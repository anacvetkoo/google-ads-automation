"""Integracijski testi brez zunanjih spletnih in Groq klicev."""
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from unittest.mock import AsyncMock, patch
from urllib.request import urlopen

import grpc
from pydantic import ValidationError
from streamlit.testing.v1 import AppTest

import google_ads_pb2 as pb
import google_ads_pb2_grpc as rpc
import grpc_client as odjemalec
import grpc_server as streznik
from grpc_mapping import v_model, v_proto
from modeli import CampaignDraft, KontekstGeneriranja, NastavitveKampanje, PodatkiStrani, PredlogSkupine


def nastavitve():
    return NastavitveKampanje(ime="Testna kampanja", cilj="Prodaja", lokacija="Slovenija", jezik="Slovenščina")


def stran():
    return PodatkiStrani(
        url="https://example.com/ponudba", datum_pridobivanja="2026-11-16T12:00:00+00:00",
        title="Ponudba", meta_description="", jezik="sl", h1=["Ponudba"], h2=[], h3=[],
        besedilo="Ponudba je opisana tukaj.", notranje_povezave=[{"naslov": "Kontakt", "url": "https://example.com/kontakt"}],
    )


def kontekst():
    return KontekstGeneriranja(nastavitve=nastavitve(), strani=[stran()], ime_skupine="Skupina 1")


def generiraj(podatki):
    return PredlogSkupine.model_validate({
        "ime": podatki.ime_skupine, "tema": "Ponudba",
        "kljucne_besede": [{"besedilo": "ponudba", "ujemanje": "EXACT", "razlog": "Ustreza strani"}],
        "oglasi": [{"koncni_url": podatki.strani[0].url, "prikazna_pot1": "ponudba", "prikazna_pot2": "",
                    "naslovi": ["Prvi naslov", "Drugi naslov", "Tretji naslov"], "opisi": ["Prvi opis", "Drugi opis"]}],
    })


class TestGRPC(unittest.TestCase):
    def setUp(self):
        self.parser = patch.object(streznik, "razcleni_stran", new_callable=AsyncMock).start()
        self.parser.return_value = stran().model_dump()
        self.generator = patch.object(streznik, "generiraj_oglase", side_effect=generiraj).start()
        self.addCleanup(patch.stopall)
        self.streznik = grpc.server(ThreadPoolExecutor(max_workers=4))
        rpc.add_GoogleAdsServiceServicer_to_server(streznik.GoogleAdsService(), self.streznik)
        vrata = self.streznik.add_insecure_port("127.0.0.1:0")
        self.assertGreater(vrata, 0)
        self.naslov = f"127.0.0.1:{vrata}"
        self.streznik.start()
        self.addCleanup(lambda: self.streznik.stop(0).wait())
        self.kanal = grpc.insecure_channel(self.naslov)
        self.addCleanup(self.kanal.close)
        grpc.channel_ready_future(self.kanal).result(timeout=5)
        self.stub = rpc.GoogleAdsServiceStub(self.kanal)

    def test_pogodba(self):
        storitve = pb.DESCRIPTOR.services_by_name
        self.assertEqual(list(storitve), ["GoogleAdsService"])
        metode = storitve["GoogleAdsService"].methods
        self.assertEqual(len(metode), 4)
        self.assertEqual([m.name for m in metode if m.server_streaming], ["GenerirajSkupino"])
        self.assertEqual(len({m.input_type.full_name for m in metode}), 4)
        self.assertEqual(len({m.output_type.full_name for m in metode}), 4)

    def test_pretvorbe(self):
        for model in [nastavitve(), stran(), kontekst(), generiraj(kontekst()), CampaignDraft(nastavitve=nastavitve())]:
            with self.subTest(model=type(model).__name__):
                self.assertEqual(v_model(v_proto(model), type(model)).model_dump(), model.model_dump())

    def test_neobvezne_vrednosti(self):
        for vrednost in [None, {}, {"izraz": "ponudba", "podatki": [1, True, None, ""]}]:
            model = kontekst().model_copy(update={"serp_context": vrednost})
            prenos = v_proto(model)
            self.assertEqual(prenos.HasField("serp_context"), vrednost is not None)
            self.assertEqual(v_model(prenos, KontekstGeneriranja).serp_context, vrednost)
        privzeto = v_model(v_proto(nastavitve()), NastavitveKampanje)
        prazno = nastavitve().model_copy(update={"ton": ""})
        self.assertEqual(privzeto.ton, "Profesionalen")
        self.assertEqual(v_model(v_proto(prazno), NastavitveKampanje).ton, "")
        with self.assertRaises(ValidationError):
            v_model(pb.NastavitveKampanje(), NastavitveKampanje)

    def test_vse_metode_vec_skupin_in_json(self):
        osnutek = odjemalec.ustvari_osnutek(nastavitve(), self.naslov)
        self.assertEqual(osnutek.skupine_oglasov, [])
        podatki = odjemalec.pridobi_stran(stran().url, self.naslov)
        self.assertEqual(podatki, stran())
        for ime in ["Prva skupina", "Druga skupina"]:
            vhod = kontekst().model_copy(update={"ime_skupine": ime, "strani": [podatki]})
            stanja = []
            skupina = odjemalec.generiraj_skupino(vhod, stanja.append, self.naslov)
            self.assertEqual(len(stanja), 1)
            osnutek.skupine_oglasov.append(skupina)
        izvoz = odjemalec.izvozi_osnutek(osnutek, self.naslov)
        self.assertEqual(izvoz.json_vsebina, json.dumps(osnutek.model_dump(mode="json"), ensure_ascii=False, indent=2))
        self.assertEqual(izvoz.ime_datoteke, "google_ads_osnutek.json")
        self.assertEqual(izvoz.mime_tip, "application/json")
        self.assertEqual(izvoz.stevilo_skupin, 2)
        self.parser.assert_awaited_once_with(stran().url)

    def test_zaporedje_streaminga(self):
        tok = self.stub.GenerirajSkupino(pb.GenerirajSkupinoRequest(kontekst=v_proto(kontekst())), timeout=5)
        odgovori = list(tok)
        self.assertEqual([o.WhichOneof("vsebina") for o in odgovori], ["stanje", "skupina"])
        self.assertTrue(odgovori[0].stanje.poteka)
        self.assertEqual(v_model(odgovori[1].skupina, PredlogSkupine), generiraj(kontekst()))

    def test_neveljavni_zahtevki(self):
        primeri = [
            (self.stub.UstvariOsnutek, pb.UstvariOsnutekRequest()),
            (self.stub.GenerirajSkupino, pb.GenerirajSkupinoRequest()),
            (self.stub.IzvoziOsnutek, pb.IzvoziOsnutekRequest()),
        ]
        for metoda, zahtevek in primeri:
            with self.subTest(metoda=metoda):
                with self.assertRaises(grpc.RpcError) as napaka:
                    odgovor = metoda(zahtevek, timeout=5)
                    if hasattr(odgovor, "__next__"):
                        list(odgovor)
                self.assertEqual(napaka.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)
        self.generator.assert_not_called()

    def test_napake_parserja(self):
        for napaka, koda in [(ValueError("skrivnost"), grpc.StatusCode.INVALID_ARGUMENT),
                             (TimeoutError("skrivnost"), grpc.StatusCode.DEADLINE_EXCEEDED),
                             (RuntimeError("skrivnost"), grpc.StatusCode.UNAVAILABLE)]:
            self.parser.side_effect = napaka
            with self.assertRaises(grpc.RpcError) as rezultat:
                self.stub.PridobiStran(pb.PridobiStranRequest(url="https://example.com"), timeout=5)
            self.assertEqual(rezultat.exception.code(), koda)
            self.assertNotIn("skrivnost", rezultat.exception.details())

    def test_llm_napaka_in_ohranitev_osnutka(self):
        osnutek = CampaignDraft(nastavitve=nastavitve(), skupine_oglasov=[generiraj(kontekst())])
        prej = osnutek.model_dump_json()
        for napaka in [ValueError("skrivnost"), RuntimeError("skrivnost"), Exception("skrivnost")]:
            self.generator.side_effect = napaka
            with self.assertRaises(odjemalec.NapakaGRPC) as rezultat:
                odjemalec.generiraj_skupino(kontekst(), naslov=self.naslov)
            self.assertNotIn("skrivnost", str(rezultat.exception))
            self.assertEqual(osnutek.model_dump_json(), prej)

    def test_nedosegljiv_streznik(self):
        self.streznik.stop(0).wait()
        with self.assertRaisesRegex(odjemalec.NapakaGRPC, "dosegljiva"):
            odjemalec.ustvari_osnutek(nastavitve(), self.naslov)

    def test_casovna_omejitev(self):
        def pocasi(podatki):
            time.sleep(0.15)
            return generiraj(podatki)
        self.generator.side_effect = pocasi
        with self.assertRaisesRegex(odjemalec.NapakaGRPC, "Čas"):
            odjemalec.generiraj_skupino(kontekst(), naslov=self.naslov, timeout=0.03)
        time.sleep(0.2)

    def test_preklic_streaminga(self):
        tok = self.stub.GenerirajSkupino(pb.GenerirajSkupinoRequest(kontekst=v_proto(kontekst())), timeout=5)
        self.assertEqual(next(tok).WhichOneof("vsebina"), "stanje")
        tok.cancel()
        with self.assertRaises(grpc.RpcError) as rezultat:
            list(tok)
        self.assertEqual(rezultat.exception.code(), grpc.StatusCode.CANCELLED)

    def test_prekinjen_in_nepravilen_tok(self):
        def samo_stanje(zahtevek, kontekst_rpc):
            yield pb.GenerirajSkupinoResponse(stanje=pb.StanjeGeneriranja(poteka=True))
        def napaka_po_rezultatu(zahtevek, kontekst_rpc):
            yield from samo_stanje(zahtevek, kontekst_rpc)
            yield pb.GenerirajSkupinoResponse(skupina=v_proto(generiraj(kontekst())))
            kontekst_rpc.abort(grpc.StatusCode.INTERNAL, "skrivnost")
        def brez_stanja(zahtevek, kontekst_rpc):
            yield pb.GenerirajSkupinoResponse(skupina=v_proto(generiraj(kontekst())))
        for izvedba in [samo_stanje, napaka_po_rezultatu, brez_stanja]:
            with self.subTest(izvedba=izvedba.__name__):
                dodatni = grpc.server(ThreadPoolExecutor(max_workers=1))
                storitev = streznik.GoogleAdsService()
                storitev.GenerirajSkupino = izvedba
                rpc.add_GoogleAdsServiceServicer_to_server(storitev, dodatni)
                vrata = dodatni.add_insecure_port("127.0.0.1:0")
                dodatni.start()
                try:
                    with self.assertRaises(odjemalec.NapakaGRPC):
                        odjemalec.generiraj_skupino(kontekst(), naslov=f"127.0.0.1:{vrata}")
                finally:
                    dodatni.stop(0).wait()

    def test_ustvari_streznik(self):
        dodatni = streznik.ustvari_streznik("127.0.0.1:0")
        dodatni.start()
        dodatni.stop(0).wait()

    def test_zagon_procesov(self):
        mapa = Path(__file__).resolve().parent
        okolje = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        proces = subprocess.Popen(
            [sys.executable, "grpc_server.py"], cwd=mapa, env=okolje,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        try:
            with grpc.insecure_channel(streznik.NASLOV) as kanal:
                grpc.channel_ready_future(kanal).result(timeout=15)
                odgovor = rpc.GoogleAdsServiceStub(kanal).UstvariOsnutek(
                    pb.UstvariOsnutekRequest(nastavitve=v_proto(nastavitve())), timeout=5,
                )
                self.assertEqual(odgovor.osnutek.nastavitve.ime, nastavitve().ime)
                self.assertIsNone(proces.poll())
        finally:
            proces.terminate()
            proces.communicate(timeout=10)

        with socket.socket() as povezava:
            povezava.bind(("127.0.0.1", 0))
            vrata = povezava.getsockname()[1]
        proces = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless=true",
             "--server.address=127.0.0.1", f"--server.port={vrata}", "--browser.gatherUsageStats=false"],
            cwd=mapa, env=okolje, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        try:
            rok = time.monotonic() + 20
            while True:
                try:
                    with urlopen(f"http://127.0.0.1:{vrata}/_stcore/health", timeout=1) as odgovor:
                        self.assertEqual(odgovor.status, 200)
                        break
                except OSError:
                    if proces.poll() is not None or time.monotonic() > rok:
                        self.fail("Zagon Streamlit strežnika ni uspel.")
                    time.sleep(0.1)
        finally:
            proces.terminate()
            proces.communicate(timeout=10)

    def test_streamlit_uporabniski_potek(self):
        #pravi gRPC klici z mock parserjem in generatorjem
        for ime in ["ustvari_osnutek", "pridobi_stran", "generiraj_skupino", "izvozi_osnutek"]:
            funkcija = getattr(odjemalec, ime)
            patch.object(odjemalec, ime, partial(funkcija, naslov=self.naslov)).start()
        izvoz_klic = patch.object(odjemalec, "izvozi_osnutek", wraps=odjemalec.izvozi_osnutek).start()
        app = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=15).run()
        self.assertEqual(len(app.exception), 0)
        app.text_input[0].set_value("Moja kampanja")
        with patch.object(odjemalec, "ustvari_osnutek", side_effect=odjemalec.NapakaGRPC("Strežnik ni dosegljiv.")):
            app.button[0].click().run()
        self.assertIsNone(app.session_state.kampanja)
        self.assertTrue(app.error)
        app.button[0].click().run()
        self.assertIsNotNone(app.session_state.kampanja)

        def klik(napis):
            next(gumb for gumb in app.button if gumb.label == napis).click().run()

        def dodaj(ime):
            klik("+ Dodaj skupino oglasov")
            app.text_input[0].set_value(ime)
            app.text_input[1].set_value(stran().url)
            klik("Generiraj ključne besede in oglas")

        dodaj("Prva")
        dodaj("Druga")
        self.assertEqual(len(app.session_state.kampanja.skupine_oglasov), 2)
        izvoz_klic.assert_not_called()
        prej = app.session_state.kampanja.model_dump_json()
        with patch.object(odjemalec, "izvozi_osnutek", side_effect=odjemalec.NapakaGRPC("Izvoz ni uspel.")):
            klik("Pripravi JSON osnutek za prenos")
        self.assertIsNone(app.session_state.izvoz)
        self.assertEqual(app.session_state.kampanja.model_dump_json(), prej)
        klik("Pripravi JSON osnutek za prenos")
        self.assertEqual(izvoz_klic.call_count, 1)
        app.run()
        self.assertEqual(izvoz_klic.call_count, 1)
        self.assertEqual(json.loads(app.session_state.izvoz.json_vsebina), app.session_state.kampanja.model_dump(mode="json"))
        dodaj("prva")
        self.assertTrue(any("že obstaja" in napaka.value for napaka in app.error))
        self.assertEqual(self.generator.call_count, 2)
        prej = app.session_state.kampanja.model_dump_json()
        prejsnji_izvoz = app.session_state.izvoz.json_vsebina
        self.generator.side_effect = RuntimeError("skrivnost")
        app.text_input[0].set_value("Tretja")
        klik("Generiraj ključne besede in oglas")
        self.assertEqual(app.session_state.kampanja.model_dump_json(), prej)
        self.assertEqual(app.session_state.izvoz.json_vsebina, prejsnji_izvoz)
        self.assertTrue(app.error)
        self.assertFalse(any("skrivnost" in napaka.value for napaka in app.error))
        self.generator.side_effect = generiraj
        klik("Generiraj ključne besede in oglas")
        self.assertEqual(len(app.session_state.kampanja.skupine_oglasov), 3)
        self.assertIsNone(app.session_state.izvoz)
        self.assertEqual(len(app.exception), 0)
        klik("Začni novo kampanjo")
        self.assertIsNone(app.session_state.kampanja)


if __name__ == "__main__":
    unittest.main()

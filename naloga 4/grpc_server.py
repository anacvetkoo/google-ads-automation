"""Lokalni gRPC strežnik brez trajnega stanja kampanj."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys

import grpc
from pydantic import ValidationError

import google_ads_pb2 as pb
import google_ads_pb2_grpc as rpc
from grpc_mapping import v_model, v_proto
from modeli import CampaignDraft, KontekstGeneriranja, NastavitveKampanje, PodatkiStrani
from ai_generator import generiraj_oglase

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "naloga 2"))
from parser import razcleni_stran

NASLOV = "127.0.0.1:50051"


class GoogleAdsService(rpc.GoogleAdsServiceServicer):
    def UstvariOsnutek(self, zahtevek, kontekst):
        try:
            nastavitve = v_model(zahtevek.nastavitve, NastavitveKampanje)
            if not nastavitve.ime.strip() or not nastavitve.lokacija.strip():
                raise ValueError()
            osnutek = CampaignDraft(nastavitve=nastavitve)
            return pb.UstvariOsnutekResponse(osnutek=v_proto(osnutek))
        except (ValidationError, ValueError):
            kontekst.abort(grpc.StatusCode.INVALID_ARGUMENT, "Preveri nastavitve kampanje; ime in lokacija sta obvezna.")
        except Exception:
            kontekst.abort(grpc.StatusCode.INTERNAL, "Ustvarjanje osnutka ni uspelo.")

    def PridobiStran(self, zahtevek, kontekst):
        try:
            #pridobivanje podatkov spletne strani
            podatki = asyncio.run(asyncio.wait_for(razcleni_stran(zahtevek.url), timeout=45))
            stran = PodatkiStrani.model_validate(podatki)
            return pb.PridobiStranResponse(stran=v_proto(stran))
        except ValueError:
            kontekst.abort(grpc.StatusCode.INVALID_ARGUMENT, "Preveri URL; uporabi dostopno javno stran HTTP ali HTTPS.")
        except TimeoutError:
            kontekst.abort(grpc.StatusCode.DEADLINE_EXCEEDED, "Pridobivanje spletne strani je trajalo predolgo.")
        except Exception:
            kontekst.abort(grpc.StatusCode.UNAVAILABLE, "Vsebine strani ni mogoče pridobiti. Preveri povezavo in namestitev Chromiuma na strežniku.")

    def GenerirajSkupino(self, zahtevek, kontekst):
        try:
            podatki = v_model(zahtevek.kontekst, KontekstGeneriranja)
        except (ValidationError, ValueError):
            kontekst.abort(grpc.StatusCode.INVALID_ARGUMENT, "Podatki za generiranje niso veljavni.")
        #pošiljanje dejanskega stanja pred obstoječim klicem LLM
        yield pb.GenerirajSkupinoResponse(stanje=pb.StanjeGeneriranja(
            sporocilo="Generiranje ključnih besed in oglasa poteka ...", poteka=True,
        ))
        if not kontekst.is_active():
            return
        try:
            skupina = generiraj_oglase(podatki)
            odgovor = pb.GenerirajSkupinoResponse(skupina=v_proto(skupina))
        except (ValueError, RuntimeError):
            kontekst.abort(grpc.StatusCode.FAILED_PRECONDITION, "Generiranje ni uspelo. Preveri vhodne podatke, konfiguracijo Groq in omejitev porabe ter poskusi ponovno.")
        except Exception:
            kontekst.abort(grpc.StatusCode.INTERNAL, "Pri generiranju oglasa je prišlo do napake.")
        if kontekst.is_active():
            yield odgovor

    def IzvoziOsnutek(self, zahtevek, kontekst):
        try:
            osnutek = v_model(zahtevek.osnutek, CampaignDraft)
            return pb.IzvoziOsnutekResponse(
                json_vsebina=json.dumps(osnutek.model_dump(mode="json"), ensure_ascii=False, indent=2),
                ime_datoteke="google_ads_osnutek.json", mime_tip="application/json",
                stevilo_skupin=len(osnutek.skupine_oglasov),
            )
        except (ValidationError, ValueError):
            kontekst.abort(grpc.StatusCode.INVALID_ARGUMENT, "Osnutek za izvoz ni veljaven.")
        except Exception:
            kontekst.abort(grpc.StatusCode.INTERNAL, "Priprava JSON osnutka ni uspela.")


def ustvari_streznik(naslov=NASLOV):
    streznik = grpc.server(ThreadPoolExecutor(max_workers=4))
    rpc.add_GoogleAdsServiceServicer_to_server(GoogleAdsService(), streznik)
    if not streznik.add_insecure_port(naslov):
        raise RuntimeError("Vrata gRPC strežnika niso na voljo.")
    return streznik


def main():
    streznik = ustvari_streznik()
    streznik.start()
    print(f"gRPC strežnik posluša na {NASLOV}", flush=True)
    try:
        streznik.wait_for_termination()
    except KeyboardInterrupt:
        pass
    finally:
        #zaključek aktivnih zahtevkov pred ustavitvijo procesa
        streznik.stop(grace=100).wait()


if __name__ == "__main__":
    main()

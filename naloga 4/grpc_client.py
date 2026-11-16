"""gRPC odjemalec za uporabo znotraj Streamlita."""
import grpc

import google_ads_pb2 as pb
import google_ads_pb2_grpc as rpc
from grpc_mapping import v_model, v_proto
from modeli import CampaignDraft, PodatkiStrani, PredlogSkupine

NASLOV = "127.0.0.1:50051"


class NapakaGRPC(RuntimeError):
    pass


def _napaka(napaka):
    sporocila = {
        grpc.StatusCode.UNAVAILABLE: "Strežnik ali spletna stran ni dosegljiva. Preveri zagon gRPC strežnika, povezavo in Chromium.",
        grpc.StatusCode.DEADLINE_EXCEEDED: "Čas za odgovor je potekel. Poskusi ponovno.",
        grpc.StatusCode.INVALID_ARGUMENT: "Vhodni podatki niso veljavni. Preveri obrazec in URL.",
        grpc.StatusCode.FAILED_PRECONDITION: "Generiranje ni uspelo. Preveri podatke, strežniško konfiguracijo Groq in omejitev porabe.",
        grpc.StatusCode.CANCELLED: "Povezava je bila prekinjena. Poskusi ponovno.",
    }
    #podrobnosti iz zunanjih storitev se ne prikazujejo uporabniku
    return NapakaGRPC(sporocila.get(napaka.code(), "Pri komunikaciji s strežnikom je prišlo do napake."))


def _poklici(metoda, zahtevek, timeout, naslov):
    try:
        with grpc.insecure_channel(naslov) as kanal:
            return getattr(rpc.GoogleAdsServiceStub(kanal), metoda)(zahtevek, timeout=timeout)
    except grpc.RpcError as napaka:
        raise _napaka(napaka) from None


def ustvari_osnutek(nastavitve, naslov=NASLOV):
    odgovor = _poklici("UstvariOsnutek", pb.UstvariOsnutekRequest(nastavitve=v_proto(nastavitve)), 10, naslov)
    return v_model(odgovor.osnutek, CampaignDraft)


def pridobi_stran(url, naslov=NASLOV):
    odgovor = _poklici("PridobiStran", pb.PridobiStranRequest(url=url), 50, naslov)
    return v_model(odgovor.stran, PodatkiStrani)


def generiraj_skupino(kontekst, prikazi_stanje=None, naslov=NASLOV, timeout=110):
    skupina = None
    zacetek = False
    try:
        with grpc.insecure_channel(naslov) as kanal:
            tok = rpc.GoogleAdsServiceStub(kanal).GenerirajSkupino(
                pb.GenerirajSkupinoRequest(kontekst=v_proto(kontekst)), timeout=timeout,
            )
            try:
                for odgovor in tok:
                    vrsta = odgovor.WhichOneof("vsebina")
                    if vrsta == "stanje" and not zacetek and skupina is None and odgovor.stanje.poteka:
                        zacetek = True
                        if prikazi_stanje:
                            prikazi_stanje(odgovor.stanje.sporocilo)
                    elif vrsta == "skupina" and zacetek and skupina is None:
                        skupina = v_model(odgovor.skupina, PredlogSkupine)
                    else:
                        raise NapakaGRPC("Strežnik je vrnil nepričakovano zaporedje odgovorov.")
            finally:
                tok.cancel()
    except grpc.RpcError as napaka:
        raise _napaka(napaka) from None
    #rezultat je uporaben šele po uspešnem zaključku celotnega toka
    if skupina is None:
        raise NapakaGRPC("Generiranje je bilo prekinjeno brez končnega rezultata.")
    return skupina


def izvozi_osnutek(osnutek, naslov=NASLOV):
    return _poklici("IzvoziOsnutek", pb.IzvoziOsnutekRequest(osnutek=v_proto(osnutek)), 10, naslov)

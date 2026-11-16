"""Pretvorbe transportnih sporočil brez spreminjanja poslovnih modelov."""
from google.protobuf.json_format import MessageToDict, ParseDict

import google_ads_pb2 as pb


def v_proto(model):
    sporocilo = getattr(pb, type(model).__name__)()
    ParseDict(model.model_dump(mode="json", exclude_unset=True), sporocilo)
    return sporocilo


def _v_slovar(sporocilo):
    if sporocilo.DESCRIPTOR.full_name == "google.protobuf.Struct":
        return MessageToDict(sporocilo)
    podatki = {}
    for polje in sporocilo.DESCRIPTOR.fields:
        if polje.is_repeated:
            vrednosti = getattr(sporocilo, polje.name)
            podatki[polje.name] = (
                [_v_slovar(v) for v in vrednosti]
                if polje.message_type else list(vrednosti)
            )
        elif sporocilo.HasField(polje.name):
            vrednost = getattr(sporocilo, polje.name)
            podatki[polje.name] = _v_slovar(vrednost) if polje.message_type else vrednost
    return podatki


def v_model(sporocilo, tip_modela):
    #prazni seznami ostanejo prisotni, odsotni scalar podatki pa ne
    return tip_modela.model_validate(_v_slovar(sporocilo))

#določa strukturo podatkov, preverja njihovo veljavnost
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field


class StrogiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NastavitveKampanje(StrogiModel):
    ime: str = Field(min_length=1)
    cilj: str
    lokacija: str
    jezik: str
    ciljna_skupina: str = ""
    ton: str = "Profesionalen"
    dodatna_navodila: str = ""


class PodatkiStrani(StrogiModel):
    url: str
    datum_pridobivanja: str
    title: str
    meta_description: str
    jezik: str
    h1: list[str]
    h2: list[str]
    h3: list[str]
    besedilo: str
    notranje_povezave: list[dict]


class KontekstGeneriranja(StrogiModel):
    nastavitve: NastavitveKampanje
    strani: list[PodatkiStrani]
    ime_skupine: str
    opis_ponudbe: str = ""
    prednosti: str = ""
    navodila_skupine: str = ""
    serp_context: dict | None = None
    keyword_planner_context: dict | None = None


class PredlogKljucneBesede(StrogiModel):
    besedilo: str = Field(min_length=1, max_length=80)
    ujemanje: Literal["EXACT", "PHRASE", "BROAD"]
    razlog: str


NaslovRSA = Annotated[str, Field(min_length=1, max_length=30)]
OpisRSA = Annotated[str, Field(min_length=1, max_length=90)]


class PredlogOglasa(StrogiModel):
    koncni_url: str
    prikazna_pot1: str = Field(max_length=15)
    prikazna_pot2: str = Field(max_length=15)
    naslovi: list[NaslovRSA] = Field(min_length=3, max_length=15)
    opisi: list[OpisRSA] = Field(min_length=2, max_length=4)


class PredlogSkupine(StrogiModel):
    ime: str
    tema: str
    kljucne_besede: list[PredlogKljucneBesede]
    oglasi: list[PredlogOglasa] = Field(min_length=1, max_length=1)


class AnalizaPonudbe(StrogiModel):
    dejavnost: str
    povzetek_ponudbe: str
    opozorila: list[str]


class GeneriranaSkupina(StrogiModel):
    """Kompakten LLM odgovor: brez URL-ja, ki ga določi aplikacija."""
    tema: str
    dejavnost: str
    povzetek_ponudbe: str
    kljucne_besede: list[PredlogKljucneBesede] = Field(min_length=4, max_length=10)
    prikazna_pot1: str = Field(max_length=15)
    prikazna_pot2: str = Field(max_length=15)
    naslovi: list[NaslovRSA] = Field(min_length=5, max_length=10)
    opisi: list[OpisRSA] = Field(min_length=2, max_length=3)


class CampaignDraft(StrogiModel):
    schema_version: str = "1.0"
    nastavitve: NastavitveKampanje
    skupine_oglasov: list[PredlogSkupine] = Field(default_factory=list)

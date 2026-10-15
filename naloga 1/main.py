import xml.etree.ElementTree as ET
from pathlib import Path
import json

#pot do mape, v kateri je datoteka main.py
MAPA_PROJEKTA = Path(__file__).resolve().parent

#pot do mape s podatki
MAPA_PODATKOV = MAPA_PROJEKTA / "data"


def preberi_xml(ime_datoteke): #prejme ime datoteke, vrne njen korenski element
    pot = MAPA_PODATKOV / ime_datoteke
    drevo = ET.parse(pot)
    return drevo.getroot()

# branje xml datotek
kampanje = preberi_xml("kampanje.xml")
skupine = preberi_xml("skupine_oglasov.xml")
kljucne_besede = preberi_xml("kljucne_besede.xml")
oglasi = preberi_xml("oglasi.xml")

#deserializacija
def pretvori_kampanjo(element):
    return {
        "id": element.get("id"),
        "ime": element.findtext("ime"),
        "cilj": element.findtext("cilj"),
        "nacinDoseganjaCilja": element.findtext("nacinDoseganjaCilja"),
        "ciljnaLokacija": element.findtext("ciljnaLokacija"),
        "jezik": element.findtext("jezik"),
        "dnevniProracun": float(element.findtext("dnevniProracun")),
        "strategijaPonudb": element.findtext("strategijaPonudb"),
        "status": element.findtext("status"),
        "datumUstvarjanja": element.findtext("datumUstvarjanja"),
    }

def pretvori_skupino(element):
    return {
        "id": element.get("id"),
        "kampanjaId": element.get("kampanjaId"),
        "ime": element.findtext("ime"),
        "status": element.findtext("status"),
    }

def pretvori_kljucno_besedo(element):
    return {
        "id": element.get("id"),
        "skupinaId": element.get("skupinaId"),
        "besedilo": element.findtext("besedilo"),
        "ujemanje": element.findtext("ujemanje"),
        "povprecnaMesecnaIskanja": int(element.findtext("povprecnaMesecnaIskanja")),
        "trimesečnaSprememba": int(element.findtext("trimesečnaSprememba")),
        "letnaSprememba": int(element.findtext("letnaSprememba")),
        "konkurenca": element.findtext("konkurenca"),
        "ponudbaNizka": float(element.findtext("ponudbaNizka")),
        "ponudbaVisoka": float(element.findtext("ponudbaVisoka")),
    }

def pretvori_oglas(element):
    return {
        "id": element.get("id"),
        "skupinaId": element.get("skupinaId"),
        "koncniUrl": element.findtext("koncniUrl"),
        "prikaznaPot1": element.findtext("prikaznaPot1"),
        "prikaznaPot2": element.findtext("prikaznaPot2"),
        "naslovi": [
            naslov.text
            for naslov in element.findall("naslovi/naslov")
        ],
        "opisi": [
            opis.text
            for opis in element.findall("opisi/opis")
        ],
        "status": element.findtext("status"),
    }

seznam_kampanj = [pretvori_kampanjo(k) for k in kampanje]
seznam_skupin = [pretvori_skupino(s) for s in skupine]
seznam_kljucnih_besed = [pretvori_kljucno_besedo(b) for b in kljucne_besede]
seznam_oglasov = [pretvori_oglas(o) for o in oglasi]


#funkcija za povezovanje podatkov
def povezi_podatke(kampanje, skupine, kljucne_besede, oglasi):

    # slovar kampanj (ključ je ID kampanje)
    kampanje_po_id = {}

    for kampanja in kampanje:
        kampanje_po_id[kampanja["id"]] = {
            **kampanja, #2 zvezdici pomenita razširjanje slovarja (vse pare ključ-vrednost kopira iz slovarja kampanja v slovar kampanje_po_id)
            "skupineOglasov": []
        }

    skupine_po_id = {}

    for skupina in skupine:
        skupine_po_id[skupina["id"]] = {
            **skupina,
            "kljucneBesede": [],
            "oglasi": []
        }

    
    # Ključne besede povezem s skupinami
    for beseda in kljucne_besede:
        skupina_id = beseda["skupinaId"]
        skupine_po_id[skupina_id]["kljucneBesede"].append(beseda)

    # Oglase povezem s skupinami
    for oglas in oglasi:
        skupina_id = oglas["skupinaId"]
        skupine_po_id[skupina_id]["oglasi"].append(oglas)

    # Skupine oglasov povezem s kampanjami
    for skupina in skupine_po_id.values():
        kampanja_id = skupina["kampanjaId"]
        kampanje_po_id[kampanja_id]["skupineOglasov"].append(skupina)

    return list(kampanje_po_id.values()) 


povezane_kampanje = povezi_podatke(
    seznam_kampanj,
    seznam_skupin,
    seznam_kljucnih_besed,
    seznam_oglasov
)


#funkcije za filtriranje

def vnesi_besedilo(vprasanje):
    return input(vprasanje).strip() or None


def vnesi_stevilo(vprasanje):
    while True:
        vrednost = input(vprasanje).strip().replace(",", ".")
        if not vrednost:
            return None
        try:
            return float(vrednost)
        except ValueError:
            print("Napaka: vnesi veljavno število ali pritisni Enter.")


def vnesi_datum(vprasanje):
    from datetime import datetime

    while True:
        vrednost = input(vprasanje).strip()
        if not vrednost:
            return None
        try:
            datetime.strptime(vrednost, "%Y-%m-%d")
            return vrednost
        except ValueError:
            print("Napaka: datum mora biti v obliki YYYY-MM-DD.")


def ustreza(vrednost, iskano, delno=False):
    if iskano is None:
        return True
    vrednost = str(vrednost if vrednost is not None else "").casefold()
    iskano = str(iskano).casefold()
    return iskano in vrednost if delno else vrednost == iskano


def ustreza_stevilu(vrednost, najmanj=None, najvec=None):
    return ((najmanj is None or vrednost >= najmanj)
            and (najvec is None or vrednost <= najvec))


def ustreza_datumu(vrednost, od=None, do=None):
    return ((od is None or vrednost >= od)
            and (do is None or vrednost <= do))



def izberi_raven():
    print("\nKaj želiš poiskati?")
    print("1 - Filtriranje kampanj")
    print("2 - Filtriranje skupin oglasov")
    print("3 - Filtriranje ključnih besed")
    print("4 - Filtriranje oglasov")
    print("5 - Vse skupine oglasov določene kampanje")
    print("6 - Vse ključne besede določene skupine")
    print("7 - Vsi oglasi določene skupine")

    while True:
        izbira = input("Izbira (1-7): ").strip()
        if izbira in ("1", "2", "3", "4", "5", "6", "7"):
            return int(izbira)
        print("Izberi številko od 1 do 7.")




def pridobi_filtre(raven):
    print("\nZa preskok posameznega filtra pritisni Enter.")
    filtri = {}

    if raven == 1:
        print("\nKAMPANJE")
        filtri["minProracun"] = vnesi_stevilo("Najmanjši dnevni proračun (EUR): ")
        filtri["maxProracun"] = vnesi_stevilo("Največji dnevni proračun (EUR): ")
        filtri["statusKampanje"] = vnesi_besedilo("Status kampanje (PAUSED/ENABLED): ")
        filtri["jezik"] = vnesi_besedilo("Jezik kampanje: ")
        filtri["cilj"] = vnesi_besedilo("Cilj kampanje: ")
        filtri["datumOd"] = vnesi_datum("Datum ustvarjanja od (YYYY-MM-DD): ")
        filtri["datumDo"] = vnesi_datum("Datum ustvarjanja do (YYYY-MM-DD): ")

    elif raven == 2:
        print("\nSKUPINE OGLASOV")
        filtri["imeSkupine"] = vnesi_besedilo("Ime skupine (ali del imena): ")
        filtri["statusSkupine"] = vnesi_besedilo("Status skupine (PAUSED/ENABLED): ")

    elif raven == 3:
        print("\nKLJUČNE BESEDE")
        filtri["besedilo"] = vnesi_besedilo("Ključna beseda (ali njen del): ")
        filtri["ujemanje"] = vnesi_besedilo("Ujemanje (BROAD/PHRASE/EXACT): ")
        filtri["konkurenca"] = vnesi_besedilo("Konkurenca (LOW/MEDIUM/HIGH): ")
        filtri["minIskanja"] = vnesi_stevilo("Najmanjše število mesečnih iskanj: ")
        filtri["maxPonudba"] = vnesi_stevilo("Najvišja zgornja ponudba (EUR): ")

    elif raven == 4:
        print("\nOGLASI")
        filtri["statusOglasa"] = vnesi_besedilo("Status oglasa (PAUSED/ENABLED): ")
        filtri["koncniUrl"] = vnesi_besedilo("Končni URL oglasa (ali del URL): ")

    return filtri



def ustreza_kampanji(k, f):
    return (
        ustreza(k["status"], f["statusKampanje"])
        and ustreza(k["jezik"], f["jezik"])
        and ustreza(k["cilj"], f["cilj"])
        and ustreza_stevilu(k["dnevniProracun"], f["minProracun"], f["maxProracun"])
        and ustreza_datumu(k["datumUstvarjanja"], f["datumOd"], f["datumDo"])
    )


def ustreza_skupini(s, f):
    return (
        ustreza(s["ime"], f["imeSkupine"], True)
        and ustreza(s["status"], f["statusSkupine"])
    )


def ustreza_besedi(b, f):
    return (
        ustreza(b["besedilo"], f["besedilo"], True)
        and ustreza(b["ujemanje"], f["ujemanje"])
        and ustreza(b["konkurenca"], f["konkurenca"])
        and (f["minIskanja"] is None
             or b["povprecnaMesecnaIskanja"] >= f["minIskanja"])
        and (f["maxPonudba"] is None
             or b["ponudbaVisoka"] <= f["maxPonudba"])
    )


def ustreza_oglasu(o, f):
    return (
        ustreza(o["status"], f["statusOglasa"])
        and ustreza(o["koncniUrl"], f["koncniUrl"], True)
    )



def filtriraj_podatke(kampanje, raven, filtri):
    rezultat = []

    for kampanja in kampanje:
        if raven == 1:
            if ustreza_kampanji(kampanja, filtri):
                rezultat.append(kampanja)
            continue

        nove_skupine = []

        for skupina in kampanja["skupineOglasov"]:
            if raven == 2:
                if ustreza_skupini(skupina, filtri):
                    nove_skupine.append(skupina)

            elif raven == 3:
                ustrezne_besede = [
                    beseda for beseda in skupina["kljucneBesede"]
                    if ustreza_besedi(beseda, filtri)
                ]

                if ustrezne_besede:
                    nove_skupine.append({
                        **skupina,
                        "kljucneBesede": ustrezne_besede
                    })

            elif raven == 4:
                ustrezni_oglasi = [
                    oglas for oglas in skupina["oglasi"]
                    if ustreza_oglasu(oglas, filtri)
                ]

                if ustrezni_oglasi:
                    nove_skupine.append({
                        **skupina,
                        "oglasi": ustrezni_oglasi
                    })

        if nove_skupine:
            rezultat.append({
                **kampanja,
                "skupineOglasov": nove_skupine
            })

    return rezultat



def izpisi_rezultate(kampanje, raven):
    print("\nREZULTATI ISKANJA")

    rezultati = []

    for kampanja in kampanje:
        if raven == 1:
            rezultati.append(kampanja)
            continue

        for skupina in kampanja["skupineOglasov"]:
            if raven == 2:
                rezultati.append(skupina)
            elif raven == 3:
                rezultati.extend(skupina["kljucneBesede"])
            elif raven == 4:
                rezultati.extend(skupina["oglasi"])

    if not rezultati:
        print("Ni rezultatov, ki ustrezajo izbranim kriterijem.")
        return []

    # priprava podatkov za tabelo
    stolpci = list(rezultati[0].keys())
    vrstice = []

    for rezultat in rezultati:
        vrstica = []
        for stolpec in stolpci:
            vrednost = rezultat[stolpec]
            if isinstance(vrednost, list):
                vrednost = len(vrednost)
            vrstica.append(str(vrednost) if vrednost is not None else "-")
        vrstice.append(vrstica)

    # širina stolpcev glede na podatke
    sirine = [
        max(len(stolpec), *(len(vrstica[i]) for vrstica in vrstice))
        for i, stolpec in enumerate(stolpci)
    ]

    print()
    print(" | ".join(stolpec.ljust(sirine[i]) for i, stolpec in enumerate(stolpci)))
    print("-+-".join("-" * sirina for sirina in sirine))

    for vrstica in vrstice:
        print(" | ".join(vrednost.ljust(sirine[i]) for i, vrednost in enumerate(vrstica)))

    print(f"\nŠtevilo rezultatov: {len(rezultati)}")

    return rezultati


# shranjevanje filtriranih rezultatov v JSON

def shrani_json(podatki):
    pot = MAPA_PROJEKTA / "filtrirano.json"

    with open(pot, "w", encoding="utf-8") as datoteka: #w - ob vsakem novem shranjevanju se datoteka prepiše
        json.dump(podatki, datoteka, ensure_ascii=False, indent=4)

    print(f"Rezultati so shranjeni v datoteko {pot.name}.")


# shranjevanje filtriranih rezultatov v XML


# pretvorba podatkov v XML elemente
def dodaj_xml_podatke(element, podatki):
    for kljuc, vrednost in podatki.items():
        if isinstance(vrednost, list):
            seznam = ET.SubElement(element, kljuc)

            imena = {
                "skupineOglasov": "skupinaOglasov",
                "kljucneBesede": "kljucnaBeseda",
                "oglasi": "oglas",
                "naslovi": "naslov",
                "opisi": "opis"
            }

            ime_elementa = imena.get(kljuc, "element")

            for vrednost_seznama in vrednost:
                pod_element = ET.SubElement(seznam, ime_elementa)

                if isinstance(vrednost_seznama, dict):
                    dodaj_xml_podatke(pod_element, vrednost_seznama)
                elif vrednost_seznama is not None:
                    pod_element.text = str(vrednost_seznama)

        else:
            ET.SubElement(element, kljuc).text = (
                str(vrednost) if vrednost is not None else ""
            )


# shranjevanje filtriranih rezultatov v XML
def shrani_xml(podatki, raven):
    imena_elementov = {
        1: ("kampanje", "kampanja"),
        2: ("skupineOglasov", "skupinaOglasov"),
        3: ("kljucneBesede", "kljucnaBeseda"),
        4: ("oglasi", "oglas")
    }

    ime_korena, ime_elementa = imena_elementov[raven]
    koren = ET.Element(ime_korena)

    for podatek in podatki:
        element = ET.SubElement(koren, ime_elementa)
        dodaj_xml_podatke(element, podatek)

    drevo = ET.ElementTree(koren)
    ET.indent(drevo, space="    ")

    pot = MAPA_PROJEKTA / "filtrirano.xml"
    drevo.write(pot, encoding="utf-8", xml_declaration=True)

    print(f"Rezultati so shranjeni v datoteko {pot.name}.")




# iskanje povezanih podatkov po ID-ju

def poisci_povezane_podatke(kampanje, izbira):
    if izbira == 5:
        iskani_id = input("ID kampanje (npr. K001): ").strip().upper()
        raven = 2
    else:
        iskani_id = input("ID skupine oglasov (npr. S001): ").strip().upper()
        raven = 3 if izbira == 6 else 4

    rezultat = []

    for kampanja in kampanje:
        if izbira == 5 and kampanja["id"] != iskani_id:
            continue

        nove_skupine = []

        for skupina in kampanja["skupineOglasov"]:
            if izbira in (6, 7) and skupina["id"] != iskani_id:
                continue

            nove_skupine.append(skupina)

        if nove_skupine:
            rezultat.append({
                **kampanja,
                "skupineOglasov": nove_skupine
            })

    return rezultat, raven


# aplikacija - filtriranje

while True:
    raven = izberi_raven()

    if raven <= 4:
        filtri = pridobi_filtre(raven)
        filtrirani_podatki = filtriraj_podatke(povezane_kampanje, raven, filtri)
        rezultati = izpisi_rezultate(filtrirani_podatki, raven)

    else:
        filtrirani_podatki, raven_izpisa = poisci_povezane_podatke(
            povezane_kampanje, raven
        )
        rezultati = izpisi_rezultate(filtrirani_podatki, raven_izpisa)

    shrani_json(rezultati)
    shrani_xml(rezultati, raven if raven <= 4 else raven_izpisa)

    if input("\nNovo iskanje? (DA/NE, datoteki filtrirano.json in filtrirano.xml bosta prepisani): ").strip().upper() != "DA":
        break

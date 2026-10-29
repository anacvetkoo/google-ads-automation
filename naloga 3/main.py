import requests
from pyaxis import pyaxis
import tempfile
import os
import pandas as pd
import matplotlib.pyplot as plt

URL = "https://pxweb.stat.si/SiStat/sl/Home/DownloadPxMatrix?pxMatrixName=2977805S"


def pridobi_podatke():
    #pošiljanje http get zahtevka
    response = requests.get(URL, timeout=30)

    #preveri uspešnost zahtevka
    response.raise_for_status()

    #združevanje prenesenih podatkov
    podatki = response.content

    vsebina = podatki.decode("windows-1250")

    return vsebina

def razcleni_podatke(vsebina):
    #ustvarjanje začasne pc-axis datoteke
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".px",
        encoding="windows-1250",
        delete=False
    ) as datoteka:
        datoteka.write(vsebina)
        pot = datoteka.name

    try:
        #razčlenjevanje datoteke da lahko z njo delam v pythonu
        podatki = pyaxis.parse(pot, encoding="windows-1250")
        return podatki

    finally:
        #brisanje začasne datoteke
        os.remove(pot)


def izpisi_podatke(podatki):
    metadata = podatki["METADATA"]
    data = podatki["DATA"]

    print("\nNASLOV PODATKOVNE ZBIRKE:")
    naslov = metadata.get("TITLE", ["Naslov ni na voljo"])

    if isinstance(naslov, list):
        naslov = naslov[0] if naslov else "Naslov ni na voljo"

    print(naslov)

    print("\nSPREMENLJIVKE:")
    for spremenljivka in data.columns:
        if spremenljivka != "DATA":
          print(f"- {spremenljivka}")

    print(f"\nŠtevilo podatkovnih zapisov: {len(data)}")


def analiziraj_podatke(podatki):
    df = podatki["DATA"].copy()

    #pretvorba v numerični tip
    df["DATA"] = pd.to_numeric(df["DATA"], errors="coerce")

    #filtriranje - za celo Slo
    df = df[df["KOHEZIJSKA REGIJA"] == "SLOVENIJA"]

    kategorija_vsa = "0 Število podjetij"
    kategorija_oglasevanje = (
        "1 Podjetje plačuje za oglaševanje na internetu, "
        "npr. oglasi na internetnih iskalnikih, družbenih medijih, drugih spletnih straneh"
    )

    #filtriranje izbranih kategorij
    df = df[
        df["PLAČLJIVO OGLAŠEVANJE NA INTERNETU"].isin(
            [kategorija_vsa, kategorija_oglasevanje]
        )
    ]

    #preoblikovanje podatkov v tabelo po letih
    tabela = df.pivot(
        index="LETO",
        columns="PLAČLJIVO OGLAŠEVANJE NA INTERNETU",
        values="DATA"
    )

    #preimenovanje stolpcev
    tabela = tabela.rename(columns={
        kategorija_vsa: "Vsa podjetja",
        kategorija_oglasevanje: "Podjetja s plačljivim oglaševanjem"
    })

    #izračun deleža podjetij s plačljivim oglaševanjem
    tabela["Delež (%)"] = (
        tabela["Podjetja s plačljivim oglaševanjem"]
        / tabela["Vsa podjetja"] * 100
    ).round(2)

    print("\nANALIZA PLAČLJIVEGA SPLETNEGA OGLAŠEVANJA")
    print(tabela.to_string())

    #izračun spremembe med letoma
    if "2023" in tabela.index and "2024" in tabela.index:
        sprememba = tabela.loc["2024", "Delež (%)"] - tabela.loc["2023", "Delež (%)"]

        print(
            f"\nSprememba deleža med letoma 2023 in 2024: "
            f"{sprememba:+.2f} odstotne točke"
        )

    return tabela

def prikazi_graf_delezev(tabela):
    leta = tabela.index.astype(str)
    delezi = tabela["Delež (%)"]

    plt.figure(figsize=(8, 5))
    stolpci = plt.bar(leta, delezi, color="#4285F4", width=0.5)

    #nastavitev naslova in oznak
    plt.title("Uporaba plačljivega spletnega oglaševanja v Sloveniji")
    plt.xlabel("Leto")
    plt.ylabel("Delež podjetij (%)")

    #nastavitev območja osi y
    plt.ylim(0, 100)

    #prikaz vrednosti nad stolpci
    for stolpec in stolpci:
        vrednost = stolpec.get_height()

        plt.text(
            stolpec.get_x() + stolpec.get_width() / 2,
            vrednost + 1,
            f"{vrednost:.2f} %",
            ha="center"
        )

    plt.tight_layout()
    plt.show()


def prikazi_graf_metod(podatki):
    df = podatki["DATA"].copy()

    #pretvorba v numerični tip
    df["DATA"] = pd.to_numeric(df["DATA"], errors="coerce")

    #filtriranje - za celo Slo
    df = df[df["KOHEZIJSKA REGIJA"] == "SLOVENIJA"]

    #izbor metod ciljnega oglaševanja
    metode = {
        "1.1": "Vsebina in ključne besede",
        "1.2": "Pretekle aktivnosti uporabnikov",
        "1.3": "Geolokacija uporabnikov",
        "1.4": "Druge metode"
    }

    #pridobivanje oznak metod
    df["Metoda"] = df["PLAČLJIVO OGLAŠEVANJE NA INTERNETU"].apply(
        lambda vrednost: next(
            (naziv for oznaka, naziv in metode.items()
             if str(vrednost).startswith(oznaka)),
            None
        )
    )

    #odstranjevanje ostalih kategorij
    df = df.dropna(subset=["Metoda", "DATA"])

    #preoblikovanje podatkov v tabelo
    tabela = df.pivot(
        index="Metoda",
        columns="LETO",
        values="DATA"
    )

    #razvrščanje metod
    tabela = tabela.reindex(list(metode.values()))

    ax = tabela.plot(
        kind="bar",
        figsize=(11, 6),
        width=0.7,
        color=["#4285F4", "#34A853"]
    )

    plt.title("Metode ciljnega spletnega oglaševanja v Sloveniji")
    plt.xlabel("Metoda ciljnega oglaševanja")
    plt.ylabel("Število podjetij")

    #nastavitev oznak na osi x
    plt.xticks(rotation=15, ha="right")

    #prikaz vrednosti nad stolpci
    for stolpec in ax.patches:
        vrednost = stolpec.get_height()

        if pd.notna(vrednost) and vrednost > 0:
            ax.annotate(
                f"{vrednost:.0f}",
                (
                    stolpec.get_x() + stolpec.get_width() / 2,
                    vrednost
                ),
                ha="center",
                va="bottom",
                xytext=(0, 3),
                textcoords="offset points"
            )

    plt.legend(title="Leto")
    plt.tight_layout()
    plt.show()

def main():
    try:
        vsebina = pridobi_podatke()

        #preverjanje formata prenesenih podatkov
        if 'AXIS-VERSION=' not in vsebina:
            print("Napaka: prenesena vsebina ni PC-Axis datoteka.")
            return

        print("Datoteka PC-Axis je bila uspešno prenesena.")

        #razčlenjevanje pc-axis datoteke
        podatki = razcleni_podatke(vsebina)

        izpisi_podatke(podatki)
        tabela = analiziraj_podatke(podatki)
        prikazi_graf_delezev(tabela)
        prikazi_graf_metod(podatki)

    except requests.RequestException as e:
        print(f"Napaka pri prenosu podatkov: {e}")

    except Exception as e:
        print(f"Napaka pri obdelavi podatkov: {e}")


if __name__ == "__main__":
    main()
# streamlit aplikacija
import asyncio
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

import streamlit as st #iz python kode naredi spletni vmesnik

from modeli import NastavitveKampanje, PodatkiStrani, KontekstGeneriranja, CampaignDraft
from ai_generator import generiraj_oglase

KOREN = Path(__file__).resolve().parent.parent
MAPA_PARSERJA = KOREN / "naloga 2"
sys.path.insert(0, str(MAPA_PARSERJA))
from parser import razcleni_stran

st.set_page_config(page_title="AI generator Google Ads kampanj", page_icon="📊", layout="wide")
st.title("AI generator Google Ads kampanj")

if "kampanja" not in st.session_state:
    st.session_state.kampanja = None

if st.session_state.kampanja is None:
    st.header("1. Ustvari kampanjo")
    with st.form("kampanja_obrazec"):
        ime = st.text_input("Ime kampanje")
        a, b = st.columns(2)
        with a:
            cilj = st.selectbox("Cilj oglaševanja", ["Potencialne stranke", "Prodaja", "Promet na spletno stran"])
            lokacija = st.text_input("Ciljna lokacija", value="Slovenija")
            jezik = st.selectbox("Jezik oglasov", ["Slovenščina", "Angleščina", "Nemščina", "Hrvaščina", "Italijanščina"])
        with b:
            ciljna_skupina = st.text_input("Ciljna skupina (neobvezno)")
            ton = st.selectbox("Ton komunikacije", ["Profesionalen", "Prijazen", "Sproščen", "Prepričljiv", "Nevtralen"])
        dodatna_navodila = st.text_area("Navodila za celotno kampanjo (neobvezno)")
        oddaj = st.form_submit_button("Ustvari kampanjo", type="primary")

    if oddaj:
        if not ime.strip() or not lokacija.strip():
            st.error("Ime kampanje in ciljna lokacija sta obvezna.")
        else:
            nastavitve = NastavitveKampanje(
                ime=ime.strip(), cilj=cilj, lokacija=lokacija.strip(), jezik=jezik,
                ciljna_skupina=ciljna_skupina.strip(), ton=ton,
                dodatna_navodila=dodatna_navodila.strip(),
            )
            st.session_state.kampanja = CampaignDraft(nastavitve=nastavitve)
            st.session_state.prikazi_obrazec_skupine = False
            st.rerun()
else:
    osnutek = st.session_state.kampanja
    st.header(f"Kampanja: {osnutek.nastavitve.ime}")
    st.write(
        f"**Cilj:** {osnutek.nastavitve.cilj}  |  "
        f"**Lokacija:** {osnutek.nastavitve.lokacija}  |  "
        f"**Jezik:** {osnutek.nastavitve.jezik}"
    )
    st.write(f"**Število skupin oglasov:** {len(osnutek.skupine_oglasov)}")

    st.subheader("Skupine oglasov")
    for i, skupina in enumerate(osnutek.skupine_oglasov, start=1):
        with st.expander(f"{i}. {skupina.ime}", expanded=True):
            st.write("**Tema:**", skupina.tema)
            st.markdown("#### Ključne besede")
            st.dataframe(
                [{"Ključna beseda": k.besedilo, "Ujemanje": k.ujemanje,
                  "Razlog": k.razlog} for k in skupina.kljucne_besede],
                use_container_width=True, hide_index=True,
            )
            #poslovna logika: vsaka skupina ima 1 oglas oz. rsa
            oglas = skupina.oglasi[0]
            st.markdown("#### Responsive Search Ad")
            st.write("**Končni URL:**", oglas.koncni_url)
            st.write("**Prikazni poti:**", oglas.prikazna_pot1, "/", oglas.prikazna_pot2)
            st.markdown("**Naslovi:**")
            st.dataframe(
                [{"Naslov": n, "Znaki": len(n)} for n in oglas.naslovi],
                use_container_width=True, hide_index=True,
            )
            st.markdown("**Opisi:**")
            st.dataframe(
                [{"Opis": o, "Znaki": len(o)} for o in oglas.opisi],
                use_container_width=True, hide_index=True,
            )

    if st.button("+ Dodaj skupino oglasov", type="primary"):
        st.session_state.prikazi_obrazec_skupine = True

    if st.session_state.get("prikazi_obrazec_skupine", False):
        st.divider()
        st.subheader("Dodaj eno skupino oglasov")
        with st.form("obrazec_skupine", clear_on_submit=False):
            ime_skupine = st.text_input("Ime skupine oglasov")
            url = st.text_input("Končni URL oglasa / URL ponudbe")
            opis_ponudbe = st.text_area("Opis ponudbe (neobvezno)", help="Pomaga AI natančneje razumeti temo skupine.")
            prednosti = st.text_area("Prednosti ponudbe (neobvezno)")
            navodila_skupine = st.text_area("Dodatna navodila za skupino (neobvezno)")
            generiraj = st.form_submit_button("Generiraj ključne besede in oglas", type="primary")

        if generiraj:
            url = url.strip()
            deli = urlsplit(url)
            if not ime_skupine.strip():
                st.error("Vnesi ime skupine oglasov.")
            elif deli.scheme not in ("http", "https") or not deli.netloc:
                st.error("Vnesi veljaven URL s https:// ali http://.")
            elif any(s.ime.casefold() == ime_skupine.strip().casefold() for s in osnutek.skupine_oglasov):
                st.error("Skupina s tem imenom že obstaja.")
            else:
                try:
                    with st.spinner("Pridobivam vsebino spletne strani ..."):
                        podatki = asyncio.run(razcleni_stran(url))
                        stran = PodatkiStrani.model_validate(podatki)
                    kontekst = KontekstGeneriranja(
                        nastavitve=osnutek.nastavitve,
                        strani=[stran],
                        ime_skupine=ime_skupine.strip(),
                        opis_ponudbe=opis_ponudbe.strip(),
                        prednosti=prednosti.strip(),
                        navodila_skupine=navodila_skupine.strip(),
                    )
                    with st.spinner("Generiranje ključnih besed in oglasa ..."):
                        skupina = generiraj_oglase(kontekst)
                    osnutek.skupine_oglasov.append(skupina)
                    st.session_state.kampanja = osnutek
                    st.session_state.prikazi_obrazec_skupine = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Skupina ni bila dodana: {e}")
                    st.info("Kampanja in že uspešno ustvarjene skupine so ohranjene. Poskusi ponovno.")

    if osnutek.skupine_oglasov:
        st.divider()
        st.download_button(
            "Prenesi JSON osnutek kampanje",
            data=json.dumps(osnutek.model_dump(mode="json"), ensure_ascii=False, indent=2),
            file_name="google_ads_osnutek.json",
            mime="application/json",
        )

    st.divider()
    if st.button("Začni novo kampanjo"):
        st.session_state.kampanja = None
        st.session_state.prikazi_obrazec_skupine = False
        st.rerun()

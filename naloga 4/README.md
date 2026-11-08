# TIDS – Naloga 4: Integracija LLM

Spletna aplikacija za generiranje predlogov Google Ads kampanj z uporabo Groq API (LLM). Podatki se generirajo dinamično in obdelajo v strukturiranem JSON formatu s Pydantic.

### Delovanje aplikacije

Uporabnik najprej ustvari kampanjo z osnovnimi nastavitvami. Nato lahko dodaja posamezne skupine oglasov, za katere vnese URL spletne strani in dodatne podatke o ponudbi.

Aplikacija s pomočjo Playwrighta pridobi vsebino spletne strani in na podlagi zbranih podatkov dinamično sestavi prompt za LLM. Model generira ključne besede in en Responsive Search Ad za posamezno skupino oglasov.

Prejeti JSON se validira s Pydantic in prikaže v aplikaciji. Uporabnik lahko doda več skupin oglasov ter na koncu prenese celoten osnutek kampanje v JSON formatu.

### Vhodni podatki

- **Kampanja:** ime, cilj, lokacija, jezik, ciljna skupina, prednosti, ton in dodatna navodila.
- **Skupina oglasov:** ime, URL, opis ponudbe, prednosti in dodatna navodila.
- **Samodejno pridobljeni podatki:** naslov, meta opis, naslovi in besedilo spletne strani (Playwright).

### Izhodni podatki

- **Ključne besede:** besedilo, vrsta ujemanja (EXACT, PHRASE, BROAD) in razlog.
- **Responsive Search Ad:** končni URL, prikazni poti, naslovi (največ 30 znakov) in opisi (največ 90 znakov).
- **JSON:** strukturiran osnutek kampanje s skupinami oglasov in oglasi, validiran s Pydantic.

### Namestitev

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### Nastavitev

V mapi `naloga 4` ustvari datoteko `.env`:

```env
GROQ_API_KEY=tvoj_api_kljuc
GROQ_MODEL=openai/gpt-oss-20b
```

### Zagon

```bash
streamlit run app.py
```

**Opomba:** Aplikacija uporablja `parser.py` iz mape `naloga 2`, zato mora biti ohranjena struktura projekta.
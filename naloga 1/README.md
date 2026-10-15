# Filtriranje podatkov Google Ads kampanj

## Opis projekta

Projekt je konzolna aplikacija v Pythonu, ki omogoča branje, povezovanje in filtriranje podatkov o Google Ads kampanjah, skupinah oglasov, ključnih besedah in oglasih.

Podatki se preberejo iz štirih XML-datotek, pretvorijo v Pythonove slovarje in sezname ter povežejo glede na ID-je. Uporabnik izbere raven filtriranja in vnese želene kriterije. **Filtriranje poteka na izbrani ravni**, pri čemer se ohranijo tudi pripadajoči povezani podatki. Omogočeno je tudi iskanje skupin oglasov po ID-ju kampanje ter ključnih besed in oglasov po ID-ju skupine.

Rezultati se izpišejo v terminalu in samodejno izvozijo v datoteki `filtrirano.json` in `filtrirano.xml`. Ob novem iskanju se datoteki prepišeta.

## Zagon programa

Program zaženemo v terminalu z ukazom:

```bash
python main.py
```

Uporablja samo standardne Pythonove knjižnice, zato dodatne namestitve niso potrebne.

## Primeri uporabe

**1. Filtriranje kampanj glede na dnevni proračun**

Izberemo možnost `1` in določimo najmanjši dnevni proračun `50` ter največji `100`. Ostale filtre preskočimo. Program vrne kampanje s proračunom med 50 in 100 EUR.

**2. Filtriranje ključnih besed glede na več kriterijev**

Izberemo možnost `3` ter določimo ujemanje `EXACT`, konkurenco `HIGH` in najmanj `1000` povprečnih mesečnih iskanj. Program vrne ključne besede, ki izpolnjujejo vse tri pogoje.

**3. Iskanje povezanih podatkov po ID-ju**

Izberemo možnost `6` in vnesemo ID skupine `S001`. Program izpiše vse ključne besede, ki pripadajo tej skupini oglasov.

**4. Filtriranje kampanj glede na cilj**

Izberemo možnost `1` in pri cilju kampanje vnesemo `SALES`. Ostale filtre preskočimo. Program vrne vse kampanje s ciljem SALES, skupaj s pripadajočimi skupinami, ključnimi besedami in oglasi.

*Primer izvoženih rezultatov je priložen v datotekah `filtrirano.json` in `filtrirano.xml`.* Datoteki vsebujeta rezultate filtriranja kampanj z najmanjšim dnevnim proračunom 50 EUR in največjim 100 EUR (primer 1).


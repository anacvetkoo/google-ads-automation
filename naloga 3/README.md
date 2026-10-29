# Naloga 3 – Analiza plačljivega spletnega oglaševanja

## Opis

Program v Pythonu ob vsakem zagonu prek HTTP GET pridobi podatke Statističnega urada RS (SURS) v formatu PC-Axis (.px).

Program:
- Razčleni datoteko in izpiše naslov podatkovne zbirke ter spremenljivke.
- Filtrira podatke za Slovenijo.
- Izračuna delež podjetij, ki uporabljajo plačljivo spletno oglaševanje, in primerja leti 2023 ter 2024.
- Prikaže dva stolpčna grafa: primerjavo deležev med letoma in primerjavo metod ciljnega oglaševanja.

**Vir podatkov:** SURS, podatkovna zbirka 2977805S.

## Metodološka opomba

Podatki se nanašajo na podjetja z 10 ali več zaposlenimi in samozaposlenimi. Posamezno podjetje lahko uporablja več metod ciljnega oglaševanja, zato se kategorije med seboj prekrivajo in jih ni smiselno seštevati.

## Navodila za zagon

**1. Namestitev potrebnih knjižnic:**

```bash
py -m pip install requests pyaxis pandas matplotlib
```

**2. Zagon programa:**

```bash
py main.py
```

Program potrebuje internetno povezavo. Po zagonu izpiše rezultate analize in odpre prvi graf. Po zaprtju prvega grafa se prikaže drugi.
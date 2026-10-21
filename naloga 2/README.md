
# Naloga 3 – Razčlenjevanje spletnih strani

Razčlenjevalnik spletnih strani za projekt Avtomatizirana priprava Google Ads kampanj.

Program uporablja Python in knjižnico Playwright. Uporabnik vnese URL spletne strani, program pa samodejno pridobi naslov strani, meta opis,naslove H1 in H2 ter besedilo spletne strani.

Pridobljeni podatki se shranijo v datoteko podatki_strani.json in bodo uporabljeni pri pripravi Google Ads kampanj.

## Namestitev

python -m pip install playwright
python -m playwright install chromium

## Zagon

python parser.py

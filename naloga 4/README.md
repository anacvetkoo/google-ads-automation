# Avtomatizirana priprava Google Ads kampanj – gRPC

Streamlit aplikacija z vsebino spletne strani in Groq LLM pripravi ključne besede
ter en oglas RSA na skupino. Rezultat je JSON osnutek; kampanje ne objavi v Google Ads.

## Arhitektura in podatki

Brskalnik → Streamlit (`app.py`) → Python odjemalec (`grpc_client.py`) →
lokalni gRPC strežnik (`grpc_server.py`, `127.0.0.1:50051`).
Strežnik uporablja obstoječa `naloga 2/parser.py` in `ai_generator.py` ter iste
Pydantic modele. Kampanja ostane v `st.session_state`, strežnik nima trajnega stanja.
Pretvorbe so v `grpc_mapping.py`. Ohrani strukturo map zaradi uvoza parserja.

| Metoda v `GoogleAdsService` | Tip | Vhod → izhod |
|---|---|---|
| `UstvariOsnutek` | Unary | Nastavitve kampanje → prazen validiran osnutek |
| `PridobiStran` | Unary | URL → strukturirani podatki strani |
| `GenerirajSkupino` | Server streaming | Kontekst → začetno stanje, nato validirana skupina |
| `IzvoziOsnutek` | Unary | Osnutek → JSON, ime datoteke, MIME tip in število skupin |

Vsaka metoda ima ločena `Request` in `Response` sporočila v `google_ads.proto`.
Strukturirana sporočila vsebujejo nastavitve (ime, cilj, lokacija, jezik, ton,
navodila), stran (URL, datum, naslov, meta opis, jezik, H1–H3, besedilo, povezave),
kontekst (nastavitve, strani, ime skupine, opis, prednosti, navodila), ključne besede
(besedilo, ujemanje, razlog), oglase (URL, poti, naslovi, opisi), skupine in osnutek.
Uporabljajo `string`, vgnezdena sporočila in `repeated`. Transportno stanje vsebuje
`bool poteka`, izvoz pa `int32 stevilo_skupin`; ti polji ne spreminjata modelov ali JSON.

`optional string` loči manjkajoče vrednosti od praznih in ohrani privzete vrednosti.
Kontekstna slovarja in slovarji notranjih povezav uporabljajo `google.protobuf.Struct`.
Odsoten kontekst ostane `None`, prisoten prazen kontekst `{}`. Števila v `Struct`
se prenašajo kot `double`. Odsoten in prazen ponavljajoči seznam sta `[]`.
Obstoječe poslovne validacije še vedno izvaja Pydantic.

## Namestitev (Windows 11, PowerShell)

Preverjeno s Python 3.13.0. Knjižnice: Pydantic 2, python-dotenv, Streamlit,
Playwright, Groq, grpcio, grpcio-tools in protobuf. Različice gRPC/Protobuf so
usklajene v `requirements.txt`. Ukaze izvajaj iz mape `naloga 4`:

```powershell
Set-Location 'C:\TIDS projekt\google-ads-automation\naloga 4'
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

Če `.venv` že obstaja, preskoči ustvarjanje okolja. Aktivacija ni potrebna.
Če `py` ne najde Pythona, uporabi dejansko pot do interpreterja, v tem okolju:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" -m venv .venv
```

Obstoječa `.env` ostane nespremenjena. Strežnik potrebuje `GROQ_API_KEY`;
`GROQ_MODEL` je neobvezen (privzeto `openai/gpt-oss-20b`). Ključ ostane na strežniku.

## Generiranje in zagon

Generirani datoteki sta priloženi. Po spremembi `.proto` ju ustvari znova;
`google_ads_pb2.py` in `google_ads_pb2_grpc.py` se ne urejata ročno:

```powershell
.\.venv\Scripts\python.exe -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. google_ads.proto
```

Prvi terminal v mapi `naloga 4`:

```powershell
.\.venv\Scripts\python.exe grpc_server.py
```

Drugi terminal v isti mapi:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Odpri `http://localhost:8501`. Procesa ustavi s Ctrl+C; gRPC strežnik omogoči
do 100 sekund za zaključek aktivnih zahtevkov.

## Streaming, izvoz in napake

Strežnik najprej pošlje stanje »Generiranje poteka«, nato pokliče obstoječi generator
in pošlje končno skupino. `oneof` loči stanje od rezultata. Streamlit prikaže prejeto
stanje med čakanjem. To ni tok tokenov LLM ali odstotkov napredka.
Rezultat se doda kampanji šele po uspešnem zaključku celotnega toka.

»Pripravi JSON osnutek za prenos« pokliče izvoz; nato se pojavi obstoječi gumb za
prenos JSON. Vsebina in oblikovanje JSON sta enaka prejšnjemu izvozu.
Izvoz je shranjen v seji in se razveljavi po uspešnem dodajanju skupine.
Ponovni izrisi sami ne sprožajo RPC klicev. Napake ohranijo kampanjo in prejšnji izvoz
ter ne prikazujejo občutljivih podrobnosti zunanjih storitev.

Odjemalec uporablja omejitve 10 s za ustvarjanje/izvoz, 50 s za stran in 110 s za
generiranje (do dva obstoječa Groq klica po 45 s). Strežnik omeji pridobivanje strani
na 45 s. Ob preklicu že začet sinhroni Groq klic lahko še teče do obstoječe omejitve;
njegov rezultat se zavrže.

## Testi in ročni preizkus

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_grpc
.\.venv\Scripts\python.exe -m pip check
```

Testi uporabljajo pravo lokalno gRPC povezavo, mock parser/generator in Streamlit
AppTest. Preverjajo metode, streaming, pretvorbe, JSON, več skupin, podvojena imena,
napake, prekinitve in ohranitev stanja. Ne kličejo dejanskega Groq API.

Ročno zaženi oba procesa in preveri:

1. »Ustvari kampanjo«: `UstvariOsnutek` vrne osnutek in aplikacija prikaže nastavitve.
2. Dodaj skupino z javnim URL-jem: `PridobiStran` pridobi vsebino, `GenerirajSkupino`
   pokaže stanje in nato ključne besede ter oglas. Poskusi še drugo in podvojeno skupino.
3. Pripravi in prenesi JSON: `IzvoziOsnutek` vrne obe skupini v `skupine_oglasov`.
4. Ustavi gRPC strežnik in poskusi dodati skupino: obstoječa kampanja ostane ohranjena.

Dejanski preizkus strani in generiranja potrebuje Chromium, internet ter veljaven
Groq ključ z razpoložljivo kvoto; avtomatski testi teh zunanjih storitev ne potrjujejo.

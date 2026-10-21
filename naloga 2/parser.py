
import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright


async def main():
    url = input("Vnesi URL spletne strani: ").strip()

    if not url.startswith(("http://", "https://")):
        print("Napaka: URL mora vsebovati https:// ali http://")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # odpre brskalnik
        try:
            page = await browser.new_page()  # nov zavihek

            await page.goto(  # odpre spletno stran
                url,
                wait_until="domcontentloaded",
                timeout=30000
            )

            # pridobivanje podatkov iz HTML elementov
            podatki = await page.evaluate("""() => {
                const besedilo = (selector) =>
                    document.querySelector(selector)?.innerText.trim() || "";

                const atribut = (selector, ime) =>
                    document.querySelector(selector)?.getAttribute(ime) || "";

                const naslovi = (selector) =>
                    Array.from(document.querySelectorAll(selector))
                        .map(el => el.innerText.trim())
                        .filter(Boolean);

                // pridobivanje notranjih povezav
                const povezave = Array.from(document.querySelectorAll("a[href]"))
                    .map(a => ({
                        naslov: a.innerText.trim(),
                        url: new URL(a.getAttribute("href"), document.baseURI).href
                    }))
                    .filter(p =>
                        p.naslov &&
                        ["http:", "https:"].includes(new URL(p.url).protocol) &&
                        new URL(p.url).hostname === window.location.hostname &&
                        p.url.split("#")[0] !== window.location.href.split("#")[0]
                    );

                // odstranjevanje podvojenih povezav
                const notranje_povezave = Array.from(
                    new Map(povezave.map(p => [p.url.split("#")[0], {
                        naslov: p.naslov,
                        url: p.url.split("#")[0]
                    }])).values()
                );

                // čiščenje glavnega besedila
                const vsebina = document.querySelector("main") || document.body;
                const kopija = vsebina.cloneNode(true);

                kopija.querySelectorAll(
                    "nav, footer, header, script, style, noscript, aside"
                ).forEach(el => el.remove());

                const glavno_besedilo = kopija.innerText ||
                    kopija.textContent || "";

                return {
                    title: document.title,
                    meta_description: atribut(
                        'meta[name="description"]', 'content'
                    ),
                    jezik: document.documentElement.lang || "",
                    h1: naslovi("h1"),
                    h2: naslovi("h2"),
                    h3: naslovi("h3"),
                    besedilo: glavno_besedilo.trim(),
                    notranje_povezave: notranje_povezave
                };
            }""")

            podatki["url"] = page.url
            podatki["datum_pridobivanja"] = datetime.now().isoformat()

            # shranjevanje v JSON
            with open("podatki_strani.json", "w", encoding="utf-8") as f:
                json.dump(podatki, f, ensure_ascii=False, indent=4)

            print("Podatki so uspešno shranjeni v podatki_strani.json")

        finally:
            await browser.close()


asyncio.run(main())

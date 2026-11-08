
import asyncio
import json
import ipaddress
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse
from playwright.async_api import async_playwright


def preveri_url(url):
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL mora uporabljati HTTP ali HTTPS.")

    if not parsed.hostname:
        raise ValueError("URL nima veljavne domene.")

    if parsed.username or parsed.password:
        raise ValueError("URL ne sme vsebovati prijavnih podatkov.")

    if parsed.port not in (None, 80, 443):
        raise ValueError("Nepodprta vrata URL-ja.")

    hostname = parsed.hostname.lower()

    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("Lokalni naslovi niso dovoljeni.")

    # Osnovna zaščita pred dostopom do zasebnega omrežja.
    naslovi = socket.getaddrinfo(hostname, None)

    for naslov in naslovi:
        ip = ipaddress.ip_address(naslov[4][0])
        if not ip.is_global:
            raise ValueError("Zasebni omrežni naslovi niso dovoljeni.")

    return url


async def razcleni_stran(url):
    preveri_url(url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        try:
            context = await browser.new_context(
                service_workers="block",
                accept_downloads=False
            )
            page = await context.new_page()

            # Preverimo tudi morebitne preusmeritve.
            async def preveri_zahtevo(route):
                request = route.request

                if request.is_navigation_request():
                    try:
                        preveri_url(request.url)
                    except Exception:
                        await route.abort()
                        return

                await route.continue_()

            await page.route("**/*", preveri_zahtevo)

            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000
            )

            preveri_url(page.url)

            if response is None or response.status >= 400:
                raise ValueError("Spletna stran ni dostopna.")

            podatki = await page.evaluate("""() => {
                const atribut = (selector, ime) =>
                    document.querySelector(selector)?.getAttribute(ime) || "";

                const naslovi = (selector) =>
                    Array.from(document.querySelectorAll(selector))
                        .map(el => el.innerText.trim())
                        .filter(Boolean);

                const povezave = Array.from(
                    document.querySelectorAll("a[href]")
                ).map(a => {
                    try {
                        return {
                            naslov: a.innerText.trim(),
                            url: new URL(a.href, document.baseURI).href
                        };
                    } catch {
                        return null;
                    }
                }).filter(p =>
                    p &&
                    p.naslov &&
                    ["http:", "https:"].includes(new URL(p.url).protocol) &&
                    new URL(p.url).hostname === window.location.hostname &&
                    p.url.split("#")[0] !== window.location.href.split("#")[0]
                );

                const notranje_povezave = Array.from(
                    new Map(povezave.map(p => [
                        p.url.split("#")[0],
                        {
                            naslov: p.naslov,
                            url: p.url.split("#")[0]
                        }
                    ])).values()
                );

                const vsebina =
                    document.querySelector("main") || document.body;

                const kopija = vsebina.cloneNode(true);

                kopija.querySelectorAll(
                    "nav, footer, header, script, style, noscript, aside"
                ).forEach(el => el.remove());

                const glavno_besedilo =
                    kopija.innerText || kopija.textContent || "";

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
            podatki["datum_pridobivanja"] = (
                datetime.now(timezone.utc).isoformat()
            )

            return podatki

        finally:
            await browser.close()


async def main():
    url = input("Vnesi URL spletne strani: ").strip()

    try:
        podatki = await razcleni_stran(url)

        with open(
            "podatki_strani.json", "w", encoding="utf-8"
        ) as f:
            json.dump(
                podatki, f, ensure_ascii=False, indent=4
            )

        print("Podatki so uspešno shranjeni.")

    except Exception as e:
        print(f"Napaka: {e}")


if __name__ == "__main__":
    asyncio.run(main())

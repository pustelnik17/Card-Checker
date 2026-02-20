from playwright.async_api import async_playwright
import json
import base64
import pandas as pd
import asyncio

sem = asyncio.Semaphore(15)

def query_hash(name: str) -> str:
    data = {
        "name": name,
        "id_expansion": "",
        "rarity": "",
        "color": [],
        "power": {"logic": "<=", "search": ""},
        "toughness": {"logic": "<=", "search": ""}
    }

    json_string = json.dumps(data, separators=(",", ":"))
    return base64.urlsafe_b64encode(json_string.encode()).decode()

def parse_card_link(text: str, href: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    name = lines[0]
    cards = None
    price = None

    for line in lines:
        if line.isdigit():
            cards = int(line)
        if "zł" in line:
            price = float(line.replace("zł", "").replace(",", "."))

    return {
        "name": name,
        "price": price,
        "cards": cards,
        "link": f"https://mtgspot.pl{href.replace(' ', '%20')}"
    }

async def fetch_offer(name: str, context) -> dict:
    print(name)
    page = await context.new_page()

    await page.goto(
        f"https://mtgspot.pl/search-results?hash={query_hash(name)}",
        wait_until="networkidle"
    )

    await page.get_by_text("Tylko na stanie").click()
    await page.locator("select#select").nth(0).select_option(value="all")

    try:
        await page.wait_for_function(
            """
            () => {
                const links = document.querySelectorAll('.pb-12 a');
                if (links.length === 0) return false;

                return Array.from(links).every(a => {
                    const text = a.innerText || '';
                    return !text.split('\\n').includes('0');
                });
            }
            """,
            timeout=15000
        ) 
    except:
        await page.close()

        print("\033[91mnot found\033[0m", name)

        return {
            "name": name,
            "price": None,
            "cards": None
        }

    container = page.locator(".pb-12")
    links = container.locator("a")

    offers = []
    for i in range(await links.count()):
        text = await links.nth(i).inner_text()
        href = await links.nth(i).get_attribute("href")
        offers.append(parse_card_link(text, href))

    await page.close()

    offers.sort(key=lambda x: x["price"])

    print("\033[92mfound\033[0m", name)

    return offers[0]

async def safe_fetch(name:str, context):
    async with sem:
        return await fetch_offer(name, context)
    
async def main():
    with open("card_names.txt") as f:
        card_names = [line.strip() for line in f]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
 
        tasks = [safe_fetch(name, context) for name in card_names]

        results = await asyncio.gather(*tasks)

        await browser.close()

    df = pd.DataFrame(results)

    print(df)
    
    df.to_excel("cards.xlsx")

asyncio.run(main())

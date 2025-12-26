from playwright.sync_api import sync_playwright
import json
import base64
import pandas as pd

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

    return {"name": name, "price": price, "cards": cards, "link": f"https://mtgspot.pl{href.replace(' ','%20')}"}

def fetch_offer(name: str) -> list[dict]:
    page.goto(f"https://mtgspot.pl/search-results?hash={query_hash(name)}")

    page.get_by_text("Tylko na stanie").click()

    page.locator("select#select").nth(0).select_option(value="all")

    try:
        page.wait_for_function(
        """
        () => {
        const links = document.querySelectorAll('.pb-12 a');
        if (links.length === 0) return false;

        return Array.from(links).every(a => {
            const text = a.innerText || '';
            return !text.split('\\n').includes('0');
        });
        }
        """, timeout=3000)
    except:
        return {"name": name, "price": None, "cards": None}
    
    else:
        container = page.locator(".pb-12")
        links = container.locator("a")

        offers = []
        for i in range(links.count()):
            text = links.nth(i).inner_text()
            href = links.nth(i).get_attribute("href")
            card = parse_card_link(text, href)
            offers.append(card)

        offers.sort(key=lambda x: x["price"])

        return offers[0]
    
with open("card_names.txt") as card_names_file:
    card_names = card_names_file.readlines()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    result = []
    for card_name in card_names:
        name = card_name[:-1]
        result.append(fetch_offer(name))

    browser.close()

    df = pd.DataFrame(result)
    print(df)
    df.to_excel('cards.xlsx')

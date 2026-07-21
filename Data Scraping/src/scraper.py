import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"

HEADERS = {"User-Agent": "Seleksi Asisten Basdat"}
BASE_URL = "https://companiesmarketcap.com/artificial-intelligence/largest-ai-companies-by-marketcap/"

def fetch_page(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()  # error is clearer if request fail
    return BeautifulSoup(resp.text, "html.parser")

def parse_table_rows(soup: BeautifulSoup) -> list[dict]:
    rows = soup.select("table tbody tr")
    raw_data = []

    for row in rows:
        link_tag = row.find("a", href=True)
        if not link_tag:
            continue

        name_tag = link_tag.select_one("div.company-name")
        code_tag = link_tag.select_one("div.company-code")
        if not name_tag or not code_tag:
            continue

        rank_span = code_tag.find("span", class_="rank")
        if rank_span:
            rank_span.decompose()
        ticker = code_tag.get_text(strip=True)

        name_cell = link_tag.find_parent("td")
        data_cells = name_cell.find_next_siblings("td")

        if len(data_cells) < 3:
            continue

        all_cells = row.find_all("td")

        raw_data.append({
            "name": name_tag.get_text(strip=True),
            "ticker": ticker,
            "detail_url": "https://companiesmarketcap.com" + link_tag["href"],
            "market_cap_raw": data_cells[0].get_text(strip=True),
            "price_raw": data_cells[1].get_text(strip=True),
            "today_change_raw": data_cells[2].get_text(strip=True),
            "country_raw": all_cells[-1].get_text(strip=True),
        })
    return raw_data

def get_next_page_url(soup: BeautifulSoup) -> str | None:
    next_link = soup.find("a", string=lambda s: s and "Next" in s)
    if next_link and next_link.get("href"):
        return "https://companiesmarketcap.com" + next_link["href"]
    return None

def scrape_all_pages(start_url: str, max_pages: int = 2) -> list[dict]:
    all_data = []
    url = start_url
    page_count = 0

    while url and page_count < max_pages:
        print(f"Scraping: {url}")
        soup = fetch_page(url)
        all_data.extend(parse_table_rows(soup))
        url = get_next_page_url(soup)
        page_count += 1
        time.sleep(1.5)

    return all_data

def scrape_company_detail(detail_url: str) -> dict:
    soup = fetch_page(detail_url)

    # Categories
    categories = []
    category_links = soup.select("div.categories-box div.line1 a.category-badge")
    for a in category_links:
        categories.append({
            "name": a.get_text(strip=True),
            "url": "https://companiesmarketcap.com" + a["href"],})

    # Historical yearly market cap
    yearly_history = []
    history_table = soup.select_one("table.table")
    if history_table:
        rows = history_table.select("tbody tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 2:
                yearly_history.append({
                    "year": int(cells[0].get_text(strip=True)),
                    "market_cap": parse_money(cells[1].get_text(strip=True)),
                    "change_pct_raw": cells[2].get_text(strip=True) if len(cells) > 2 else None,})

    return {"categories": categories, "yearly_history": yearly_history}

def parse_money(raw: str) -> float | None:
    if not raw:
        return None
    raw = raw.replace("$", "").strip()
    multiplier = {"T": 1e12, "B": 1e9, "M": 1e6}
    for suffix, mult in multiplier.items():
        if raw.endswith(suffix):
            try:
                return round(float(raw[:-1]) * mult, 2)
            except ValueError:
                return None
    try:
        return round(float(raw.replace(",", "")), 2)
    except ValueError:
        return None

def clean_emoji(raw: str) -> str:
    cleaned = re.sub(r'^[^\w]+', '', raw).strip()
    return cleaned

def preprocess(raw_items: list[dict]) -> list[dict]:
    cleaned = []
    now = datetime.now(timezone.utc).isoformat()

    for item in raw_items:
        change_raw = item["today_change_raw"].replace("%", "").strip()
        try:
            today_change_pct = float(change_raw)
        except ValueError:
            today_change_pct = None

        cleaned.append({
            "name": item["name"].strip(),
            "ticker": item["ticker"].strip().upper(),
            "detail_url": item["detail_url"],
            "country": clean_emoji(item["country_raw"]),
            "market_cap": parse_money(item["market_cap_raw"]),
            "price": parse_money(item["price_raw"]),
            "today_change_pct": today_change_pct,
            "extracted_at": now,
        })
    return cleaned

def check_duplicates(companies: list[dict]):
    tickers = [c["ticker"] for c in companies]
    seen = set()
    duplicates = set()
    for t in tickers:
        if t in seen:
            duplicates.add(t)
        seen.add(t)
    if duplicates:
        print(f"WARNING: Found duplicate ticker: {duplicates}")
    else:
        print(f"No duplicate, {len(tickers)} ticker unique.")

def save_json(data: list[dict], filepath: str):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(data)} records to {filepath}")

def main():
    raw = scrape_all_pages(BASE_URL, max_pages=2)
    cleaned = preprocess(raw)

    companies = [{"name": c["name"], "ticker": c["ticker"], "country": c["country"], "detail_url": c["detail_url"]} for c in cleaned]
    snapshots = [{"ticker": c["ticker"], "market_cap": c["market_cap"], "price": c["price"], "today_change_pct": c["today_change_pct"], "extracted_at": c["extracted_at"]} for c in cleaned]

    check_duplicates(companies)

    save_json(companies, DATA_DIR / "companies.json")
    save_json(snapshots, DATA_DIR / "market_cap_snapshots.json")

    company_industries = []
    yearly_history_all = []
    all_categories = {}
    failed_companies = []

    for i, c in enumerate(cleaned):
        print(f"[{i+1}/{len(cleaned)}] Scraping detail: {c['ticker']}")
        try:
            detail = scrape_company_detail(c["detail_url"])
        except Exception as e:
            print(f"Failed scrape {c['ticker']}: {e}")
            failed_companies.append({"ticker": c["ticker"], "error": str(e)})
            continue

        for cat in detail["categories"]:
            clean_name = clean_emoji(cat["name"])
            all_categories[clean_name] = cat["url"]
            company_industries.append({"ticker": c["ticker"], "industry_name": clean_name})

        for h in detail["yearly_history"]:
            yearly_history_all.append({"ticker": c["ticker"], **h})

        time.sleep(1.5)

    industries = [{"name": name, "url": url} for name, url in all_categories.items()]

    save_json(industries, DATA_DIR / "industries.json")
    save_json(company_industries, DATA_DIR / "company_industries.json")
    save_json(yearly_history_all, DATA_DIR / "market_cap_yearly_history.json")

    if failed_companies:
        save_json(failed_companies, DATA_DIR / "scraping_errors_log.json")
        print(f"\nWARNING: {len(failed_companies)} company failed, check scraping_errors_log.json")
    else:
        print("\nAll companies scraped successfully!")

if __name__ == "__main__":
    main()
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

PORTAL_URL = "https://e-uprava.gov.si/si/javne-evidence/prosti-termini-zemljevid.html?lang=si"
SINGLETON_URL = (
    "https://e-uprava.gov.si/si/javne-evidence/prosti-termini-zemljevid"
    "/content/singleton.html"
)

CONFIG_FILE = "config.json"
SEEN_FILE = "seen_termini.json"

MIN_INTERVAL_MINUTES = 15
NEW_SLOTS_TARGET = 5 # Brskanje po straneh rezultatov (teden za tednom) ustavimo, ko naberemo vsaj toliko novih terminov
HARD_PAGE_LIMIT = 100

USER_AGENT = "Mozilla/5.0 (compatible; glavna-voznja-scraper/1.0)"

DISCORD_WEBHOOK_RE = re.compile(
    r"^https://(?:discord|discordapp)\.com/api/webhooks/\d+/[\w-]+/?$"
)

# "Preverjanje znanja" -> vrednost filtra `type`
TYPE_MAP = {
    "vožnja": "1",
    "voznja": "1",
    "teorija": "2",
}

# Naziv kategorije -> vrednost filtra `cat` (iz spustnega seznama na e-upravi)
CATEGORY_MAP = {
    "AM": "1",
    "A1": "2",
    "A2": "3",
    "A": "4",
    "B1": "5",
    "B": "6",
    "BE": "7",
    "C1": "8",
    "C1E": "9",
    "C": "10",
    "CE": "11",
    "D1": "12",
    "D1E": "13",
    "D": "14",
    "DE": "15",
    "F": "16",
    "G": "17",
}

# Število območja (1-5) -> vrednost filtra `izpitniCenter` (17-21 na e-upravi)
AREA_CODE_OFFSET = 16

# Besedilo iz podrobnosti termina ("Preverjanje znanja vožnje"/"... teorije") normaliziramo nazaj v obliko, kot je v config.json ("voznja"/"teorija")
EXAM_TYPE_MAP = {
    "vožnje": "vožnja",
    "teorije": "teorija",
}


def log(message):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def resolve_type(value):
    if value is None or str(value).strip() == "":
        raise ValueError("'preverjanjeZnanja' je obvezen (\"voznja\" ali \"teorija\")")
    key = str(value).strip().lower()
    if key not in TYPE_MAP:
        raise ValueError(
            f"Neznana vrednost za 'preverjanjeZnanja': {value!r}. "
            f"Veljavne vrednosti: voznja, teorija"
        )
    return TYPE_MAP[key]


def resolve_categories(value):
    values = as_list(value)
    if not values:
        raise ValueError("'kategorija' je obvezna (niz ali seznam, npr. \"A2\" ali [\"A2\", \"B\"])")
    codes = []
    for v in values:
        key = str(v).strip().upper()
        if key not in CATEGORY_MAP:
            raise ValueError(
                f"Neznana kategorija: {v!r}. Veljavne kategorije: "
                f"{', '.join(sorted(CATEGORY_MAP))}"
            )
        codes.append(CATEGORY_MAP[key])
    return codes


def resolve_areas(value):
    values = as_list(value)
    if not values:
        raise ValueError("'obmocje' je obvezno (število ali seznam, npr. 1 ali [1, 2])")
    codes = []
    for v in values:
        try:
            n = int(v)
        except (TypeError, ValueError):
            raise ValueError(f"Območje mora biti število med 1 in 5, dobil: {v!r}")
        if not 1 <= n <= 5:
            raise ValueError(f"Območje mora biti med 1 in 5, dobil: {v!r}")
        codes.append(str(AREA_CODE_OFFSET + n))
    return codes


def load_config():
    with open(CONFIG_FILE, encoding="utf-8") as f:
        cfg = json.load(f)

    interval = cfg.get("scraperIntervalMinutes")
    if not isinstance(interval, (int, float)) or interval < MIN_INTERVAL_MINUTES:
        raise ValueError(
            f"'scraperIntervalMinutes' mora biti število, vsaj {MIN_INTERVAL_MINUTES} "
            f"(trenutno: {interval!r})"
        )

    return cfg


def build_filter_params(cfg):
    params = [("lang", "si"), ("type", resolve_type(cfg.get("preverjanjeZnanja")))]
    for cat in resolve_categories(cfg.get("kategorija")):
        params.append(("cat", cat))
    for area in resolve_areas(cfg.get("obmocje")):
        params.append(("izpitniCenter", area))
    params += [
        ("lokacija", "-1"),
        ("offset", "0"),
        ("sentinel_type", "ok"),
        ("sentinel_status", "ok"),
        ("is_ajax", "1"),
    ]
    return params


def fetch_page(filter_params, page):
    params = list(filter_params)
    if page > 0:
        params += [("complete", "false"), ("page", str(page))]
    headers = {"User-Agent": USER_AGENT, "X-Requested-With": "XMLHttpRequest"}
    resp = requests.get(SINGLETON_URL, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_next_count(html):
    """Stran sama javi približno število preostalih rezultatov (`data-next-count`).
    Ko pade na 0 (ali manj), naslednje strani ne vrnejo več ničesar - konec podatkov."""
    match = re.search(r'data-next-count="([^"]*)"', html)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def slot_id(slot):
    raw = "|".join([slot["date"], slot["time"], slot["location"], slot["categories"], slot["type"]])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def parse_slots(html):
    soup = BeautifulSoup(html, "html.parser")
    slots = []
    current_date = None

    for row in soup.select("tr.js_dogodekBox"):
        date_cell = row.select_one('td[data-th="Datum"]')
        if date_cell is not None:
            calendar_box = date_cell.select_one(".calendarBox")
            if calendar_box is not None and calendar_box.has_attr("title"):
                current_date = calendar_box["title"].strip()
            else:
                current_date = date_cell.get_text(strip=True)

        time_cell = row.select_one('td[data-th="Ura"]')
        loc_cell = row.select_one('td[data-th="Tip / Lokacija"]')
        cat_cell = row.select_one('td[data-th="Kategorije"]')
        spots_cell = row.select_one('td[data-th="Prosta mesta"]')

        location_el = loc_cell.select_one(".dicTitle1") if loc_cell else None
        region_el = loc_cell.select_one(".dicDisclaimer") if loc_cell else None

        detail_row = row.find_next_sibling("tr", class_="js_dicDetails")
        address = ""
        exam_type = ""
        if detail_row is not None:
            address_el = detail_row.select_one(".dicTitle2")
            address = address_el.get_text(strip=True) if address_el else ""
            detail_text = detail_row.get_text(" ", strip=True)
            match = re.search(r"Preverjanje znanja (\w+)", detail_text)
            exam_type = EXAM_TYPE_MAP.get(match.group(1).lower(), "") if match else ""

        slot = {
            "date": current_date or "",
            "time": time_cell.get_text(strip=True) if time_cell else "",
            "location": location_el.get_text(strip=True) if location_el else "",
            "address": address,
            "region": region_el.get_text(strip=True) if region_el else "",
            "categories": re.sub(r"\s+", " ", cat_cell.get_text(" ", strip=True)).strip()
            if cat_cell
            else "",
            "free_spots": spots_cell.get_text(strip=True) if spots_cell else "",
            "type": exam_type,
        }
        slot["id"] = slot_id(slot)
        slots.append(slot)

    return slots


def fetch_relevant_slots(filter_params, seen):
    """Brska po straneh rezultatov (teden za tednom), dokler ne naberemo
    vsaj `NEW_SLOTS_TARGET` še neopaženih terminov ali dokler stran ne pove,
    da rezultatov zmanjkuje (`data-next-count` <= 0)."""
    all_slots = []
    new_count = 0
    page = 0

    while True:
        html = fetch_page(filter_params, page)
        slots = parse_slots(html)
        all_slots.extend(slots)
        new_count += sum(1 for slot in slots if slot["id"] not in seen)
        next_count = parse_next_count(html)

        if new_count >= NEW_SLOTS_TARGET:
            break
        if next_count is not None and next_count <= 0:
            break
        if page >= HARD_PAGE_LIMIT:
            log(f"Opozorilo: dosežena varovalka {HARD_PAGE_LIMIT} strani, ustavljam brskanje.")
            break

        page += 1

    return all_slots


def parse_slovenian_date(date_str):
    match = re.match(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", date_str)
    if not match:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return datetime(year, month, day).date()
    except ValueError:
        return None


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return {}
    with open(SEEN_FILE, encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)


def prune_seen(seen):
    today = datetime.now().date()
    pruned = {}
    for sid, date_str in seen.items():
        slot_date = parse_slovenian_date(date_str)
        if slot_date is None or slot_date >= today:
            pruned[sid] = date_str
    return pruned


def format_slot(slot):
    lines = [f"📅 **{slot['date']} ob {slot['time']}** — {slot['location']} ({slot['region']})"]
    details = []
    if slot["free_spots"]:
        details.append(f"Prosta mesta: {slot['free_spots']}")
    if slot["categories"]:
        details.append(f"Kategorije: {slot['categories']}")
    if slot["type"]:
        details.append(slot["type"])
    if details:
        lines.append(" · ".join(details))
    if slot["address"]:
        lines.append(f"Naslov: {slot['address']}")
    return "\n".join(lines)


def chunk_messages(header, slots, limit=1900):
    chunks = []
    current = [header]
    current_len = len(header)
    for slot in slots:
        block = format_slot(slot)
        if current_len + len(block) + 2 > limit and len(current) > 1:
            chunks.append("\n\n".join(current))
            current = [block]
            current_len = len(block)
        else:
            current.append(block)
            current_len += len(block) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def send_discord_notification(webhook_url, new_slots):
    word = "termin" if len(new_slots) == 1 else "terminov"
    header = (
        f"Najdenih **{len(new_slots)}** novih prostih {word} za glavno vožnjo"
    )
    for chunk in chunk_messages(header, new_slots):
        resp = requests.post(webhook_url, json={"content": chunk}, timeout=30)
        resp.raise_for_status()


def run_once(filter_params, webhook_url):
    seen = prune_seen(load_seen())
    slots = fetch_relevant_slots(filter_params, seen)
    new_slots = [slot for slot in slots if slot["id"] not in seen]

    if new_slots:
        log(f"Najdenih {len(new_slots)} novih terminov (od {len(slots)} skupaj).")
        send_discord_notification(webhook_url, new_slots)
        for slot in new_slots:
            seen[slot["id"]] = slot["date"]
    else:
        log(f"Ni novih terminov ({len(slots)} najdenih skupaj).")

    save_seen(seen)


def main():
    load_dotenv()
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url:
        sys.exit("Napaka: DISCORD_WEBHOOK_URL ni nastavljen v .env.")
    if not DISCORD_WEBHOOK_RE.match(webhook_url):
        sys.exit(
            "Napaka: DISCORD_WEBHOOK_URL ni v pravilni obliki"
        )

    try:
        cfg = load_config()
        filter_params = build_filter_params(cfg)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        sys.exit(f"Napaka v config.json: {exc}")

    run_in_actions = os.environ.get("GITHUB_ACTIONS") == "true"

    if run_in_actions:
        log("Zaznano okolje GitHub Actions - izvedem en sam zagon.")
        run_once(filter_params, webhook_url)
        return

    interval_minutes = cfg["scraperIntervalMinutes"]
    log(f"Scraper zagnan. Preverjanje vsakih {interval_minutes} minut.")
    while True:
        try:
            run_once(filter_params, webhook_url)
        except requests.RequestException as exc:
            log(f"Napaka pri dostopu do e-uprave: {exc}")
        time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    main()

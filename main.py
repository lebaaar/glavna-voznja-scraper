import difflib
import hashlib
import json
import os
import re
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup

PORTAL_URL = "https://e-uprava.gov.si/si/javne-evidence/prosti-termini-zemljevid.html?lang=si"
SINGLETON_URL = (
    "https://e-uprava.gov.si/si/javne-evidence/prosti-termini-zemljevid"
    "/content/singleton.html"
)

CONFIG_FILE = "config.json"
SEEN_FILE = "seen.json"

NOTIFY_LIMIT = 5 # Number of chronologically closest (currently best) dates
HARD_PAGE_LIMIT = 100

USER_AGENT = "Mozilla/5.0 (compatible; glavna-voznja-scraper/1.0)"

DISCORD_WEBHOOK_RE = re.compile(
    r"^https://(?:discord|discordapp)\.com/api/webhooks/\d+/[\w-]+/?$"
)

TYPE_MAP = {
    "vožnja": "1",
    "voznja": "1",
    "teorija": "2",
}

# Category name -> value of filter `cat` (from dropdown on e-uprava)
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

# Area (1-5) -> value of filter `izpitniCenter` (17-21 on e-uprava)
AREA_CODE_OFFSET = 16

# Location name (exactly as shown in the "Lokacija" dropdown on e-uprava) -> (value of filter `lokacija`, value of parent `izpitniCenter` / area)
LOCATION_MAP = {
    "1 Za izpit s tolmačem CELJE Ljubečna Cesta v Celje 14 TESTIRNICA": ("151", "19"),
    "2 Za izpit s tolmačem TRBOVLJE Mestni trg 4 TESTIRNICA": ("167", "19"),
    "3 VELENJE Koroška cesta 62a": ("228", "19"),
    "3 VELENJE Koroška cesta 62a TESTIRNICA": ("229", "19"),
    "3 Za izpit s tolmačem VELENJE Koroška cesta 62a TESTIRNICA": ("230", "19"),
    "4 Za izpit s tolmačem SLOVENJ GRADEC Meškova 21 TESTIRNICA": ("166", "19"),
    "AJDOVŠČINA Tovarniška cesta 26": ("242", "17"),
    "AJDOVŠČINA Tovarniška cesta 26 TESTIRNICA Kurivo Gorica": ("241", "17"),
    "BREŽICE Bizeljska cesta 45": ("232", "20"),
    "BREŽICE Bizeljska cesta 45 T": ("231", "20"),
    "DOMŽALE Ljubljanska cesta 71 TESTIRNICA": ("174", "18"),
    "Domžale, Ljubljanska cesta 71": ("173", "18"),
    "IDRIJA Ulica Sv Barbare 3 TESTIRNICA": ("203", "17"),
    "Ig": ("176", "18"),
    "ILIRSKA BISTRICA Šercerjeva cesta 17": ("235", "17"),
    "ILIRSKA BISTRICA Šercerjeva cesta 17 TESTIRNICA": ("211", "17"),
    "JESENICE Cesta železarjev 6a TESTIRNICA": ("168", "18"),
    "Jesenice, Cesta železarjev 6a": ("171", "18"),
    "KOPER Bertoki vadbena površina": ("120", "17"),
    "Koper, Ljubljanska cesta 6": ("119", "17"),
    "Koper, Ljubljanska cesta 6, testirnica": ("117", "17"),
    "KOČEVJE Cesta na stadion 7": ("193", "20"),
    "KOČEVJE VADBENA POVRŠINA HERBBY Novomeška cesta": ("194", "20"),
    "KOČEVJE ŠD GAJ Trg zbora odposlancev 30": ("195", "20"),
    "KRANJ Kolodvorska cesta 5": ("223", "18"),
    "KRANJ Kolodvorska cesta 5 TESTIRNICA": ("222", "18"),
    "KRŠKO Žadovinek 36": ("205", "20"),
    "KRŠKO Žadovinek 36 T": ("204", "20"),
    "Laško, Poženelova ulica 22": ("149", "19"),
    "Ljubečna, Cesta v Celje 14": ("150", "19"),
    "Ljubečna, Cesta v Celje 14, testirnica": ("148", "19"),
    "LJUBLJANA Cesta dveh cesarjev 176": ("221", "18"),
    "LJUBLJANA Cesta dveh cesarjev 176 TESTIRNICA": ("236", "18"),
    "Ljubljana, Ježica": ("178", "18"),
    "Ločica ob Savinji, Ločica ob Savinji 49": ("153", "19"),
    "Maribor, Cesta k Tamu 11": ("212", "21"),
    "Maribor, Cesta k Tamu 11, testirnica": ("213", "21"),
    "Maribor, Zolajeva ulica 12, vadbena površina Tezno": ("147", "21"),
    "Murska Sobota, Noršinska ulica 8": ("138", "21"),
    "Murska Sobota, Noršinska ulica 8, testirnica": ("142", "21"),
    "Nova Gorica, Avtobusna postaja": ("121", "17"),
    "Nova Gorica, mejni prehod Vrtojba, vadbena površina": ("126", "17"),
    "Nova gorica, parkirišče šole vožnje": ("210", "17"),
    "Nova Gorica, Trg Edvarda Kardelja 1": ("209", "17"),
    "Nova Gorica, Trg Edvarda Kardelja 1, pritličje soba 13, testirnica": ("123", "17"),
    "NOVO MESTO BTC ČEŠČA VAS 40 samo za kat B96 BE C CE D1 D F": ("187", "20"),
    "NOVO MESTO UE Defranceschijeva 1": ("185", "20"),
    "NOVO MESTO UE Defranceschijeva 1 vhod z zadnje strani stavbe": ("186", "20"),
    "Ormož, Vrazova ulica 12, testirnica": ("143", "21"),
    "POSTOJNA Kazarje 10 EPIC": ("225", "17"),
    "POSTOJNA Kazarje 10 EPIC TESTIRNICA": ("226", "17"),
    "PTUJ Dornavska cesta 22B": ("146", "21"),
    "PTUJ Dornavska cesta 22B A KAT": ("144", "21"),
    "PTUJ Dornavska cesta 22B CCE KAT": ("145", "21"),
    "PTUJ Dornavska cesta 22B TESTIRNICA": ("141", "21"),
    "Ravne na Koroškem, Čečovje 12a, testirnica": ("162", "19"),
    "SEŽANA Ulica Mirka Pirca 4": ("219", "17"),
    "SEŽANA Ulica Mirka Pirca 4 TESTIRNICA": ("218", "17"),
    "Slovenj Gradec, Meškova ulica 21": ("160", "19"),
    "Slovenj Gradec, Meškova ulica 21, testirnica": ("158", "19"),
    "SLOVENSKA BISTRICA Partizanska 22 TESTIRNICA": ("136", "21"),
    "Slovenske Konjice, Tattenbachova ulica 2a": ("152", "19"),
    "TOLMIN Tumov drevored 4": ("234", "17"),
    "TOLMIN Tumov drevored 4 UE": ("244", "17"),
    "Tolmin, Tumov drevored 4, soba IIN23, testirnica": ("125", "17"),
    "Trbovlje, Mestni trg 4": ("157", "19"),
    "Trbovlje, Mestni trg 4, testirnica": ("156", "19"),
    "Vrhnika": ("184", "18"),
    "Za izpit s tolmačem Koper, Ljubljanska 6, testirnica": ("118", "17"),
    "Za izpit s tolmačem KRŠKO Žadovinek 36": ("208", "20"),
    "Za izpit s tolmačem LJUBLJANA Cesta dveh cesarjev 176 TESTIRNICA": ("237", "18"),
    "Za izpit s tolmačem Murska Sobota, Noršinska ulica 8, testirnica": ("139", "21"),
    "Za izpit s tolmačem Nova Gorica, Trg Edvarda Kardelja 1, testirnica": ("124", "17"),
    "Za izpit s tolmačem NOVO MESTO UE Defranceschijeva 1": ("188", "20"),
    "Za izpit s tolmačem teorija Maribor, Cesta k Tamu 11": ("214", "21"),
    "Za izpit s tolmačem, Ptuj, Dornavska cesta 22B, testirnica": ("140", "21"),
    "Za izpit z tolmačem POSTOJNA Kazarje 10 EPIC TESTIRNICA": ("227", "17"),
    "ČRNOMELJ Ulica Otona Župančiča 4": ("190", "20"),
    "ČRNOMELJ Ulica Otona Župančiča 4 T": ("191", "20"),
    "ŠENTJUR Cesta na kmetijsko šolo 9": ("154", "19"),
    "ŠMARJE PRI JELŠAH Obrtniška ulica 4": ("155", "19"),
}

# Case-insensitive lookup: normalized (uppercased) name -> canonical name from LOCATION_MAP
_LOCATION_LOOKUP = {name.upper(): name for name in LOCATION_MAP}

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


def _suggest_location(key):
    prefix = sorted((n for n in _LOCATION_LOOKUP if n.startswith(key)), key=len)
    if prefix:
        return _LOCATION_LOOKUP[prefix[0]]
    contains = sorted((n for n in _LOCATION_LOOKUP if key in n), key=len)
    if contains:
        return _LOCATION_LOOKUP[contains[0]]
    close = difflib.get_close_matches(key, _LOCATION_LOOKUP.keys(), n=1, cutoff=0.6)
    return _LOCATION_LOOKUP[close[0]] if close else None


def resolve_locations(value, area_codes):
    values = [v for v in as_list(value) if str(v).strip()]
    if not values:
        return ["-1"]
    codes = []
    for v in values:
        name = str(v).strip()
        key = name.upper()
        canonical = _LOCATION_LOOKUP.get(key)
        if canonical is None:
            suggestion = _suggest_location(key)
            if suggestion:
                raise ValueError(f"Neznana lokacija: {name!r}. Ste mislili: {suggestion!r}?")
            raise ValueError(f"Neznana lokacija: {name!r}.")
        loc_code, parent_area = LOCATION_MAP[canonical]
        if parent_area not in area_codes:
            raise ValueError(
                f"Lokacija {canonical!r} ne spada v izbrano območje "
                "('lokacija' mora ustrezati enemu od izbranih 'obmocje')"
            )
        codes.append(loc_code)
    return codes


def resolve_webhook_urls(value):
    urls = [str(v).strip() for v in as_list(value) if str(v).strip()]
    if not urls:
        raise ValueError(
            "'discordWebhookUrls' je obvezen (URL niz ali seznam URL-jev Discord webhookov)"
        )
    for url in urls:
        if not DISCORD_WEBHOOK_RE.match(url):
            raise ValueError(f"Discord webhook URL ni v pravilni obliki: {url!r}")
    return urls


def load_config():
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)


def build_filter_params(cfg):
    params = [("lang", "si"), ("type", resolve_type(cfg.get("preverjanjeZnanja")))]
    for cat in resolve_categories(cfg.get("kategorija")):
        params.append(("cat", cat))
    area_codes = resolve_areas(cfg.get("obmocje"))
    for area in area_codes:
        params.append(("izpitniCenter", area))
    for location in resolve_locations(cfg.get("lokacija"), area_codes):
        params.append(("lokacija", location))
    params += [
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


def fetch_best_slots(filter_params):
    seen_ids = set()
    slots = []
    page = 0

    while True:
        html = fetch_page(filter_params, page)
        for slot in parse_slots(html):
            if slot["id"] not in seen_ids:
                seen_ids.add(slot["id"])
                slots.append(slot)
        next_count = parse_next_count(html)

        if len(slots) >= NOTIFY_LIMIT:
            break
        if next_count is not None and next_count <= 0:
            break
        if page >= HARD_PAGE_LIMIT:
            log(f"Opozorilo: dosežena varovalka {HARD_PAGE_LIMIT} strani, ustavljam brskanje.")
            break

        page += 1

    return slots[:NOTIFY_LIMIT]


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


def send_discord_notification(webhook_urls, new_slots, total_best):
    word = "termin" if len(new_slots) == 1 else "terminov"
    header = (
        f"Najdenih **{len(new_slots)}** novih prostih {word} za glavno vožnjo "
        f"(od {total_best} trenutno najboljših)"
    )
    chunks = chunk_messages(header, new_slots)
    for webhook_url in webhook_urls:
        for chunk in chunks:
            resp = requests.post(webhook_url, json={"content": chunk}, timeout=30)
            resp.raise_for_status()


def run_once(filter_params, webhook_urls):
    seen = prune_seen(load_seen())
    best = fetch_best_slots(filter_params)
    new_slots = [slot for slot in best if slot["id"] not in seen]

    if new_slots:
        log(f"Najdenih {len(new_slots)} novih med {len(best)} trenutno najboljšimi termini.")
        send_discord_notification(webhook_urls, new_slots, len(best))
        for slot in new_slots:
            seen[slot["id"]] = slot["date"]
    else:
        log(f"Brez sprememb med {len(best)} trenutno najboljšimi termini.")

    save_seen(seen)


def main():
    try:
        cfg = load_config()
        filter_params = build_filter_params(cfg)
        webhook_urls = resolve_webhook_urls(cfg.get("discordWebhookUrls"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        sys.exit(f"Napaka v config.json: {exc}")

    try:
        run_once(filter_params, webhook_urls)
    except requests.RequestException as exc:
        sys.exit(f"Napaka pri dostopu do e-uprave: {exc}")


if __name__ == "__main__":
    main()

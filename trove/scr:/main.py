import os
import re
import csv
import json
import time
from typing import Any, Dict, List, Optional, Tuple

import requests


API_URL = "https://api.trove.nla.gov.au/v3/result"

TROVE_API_KEY = "ZviyAnc5F5jrO4OKvDeDy4Z2cqdq3kXT"

OUT_DIR = "data"
OUT_JSONL = os.path.join(OUT_DIR, "trove_genocide_au_press.jsonl")
OUT_CSV = os.path.join(OUT_DIR, "trove_genocide_au_press.csv")
STATE_PATH = os.path.join(OUT_DIR, "harvest_state.json")

CATEGORIES = ["newspaper"]

MAX_RECORDS_PER_QUERY_PER_CATEGORY = None

PAGE_SIZE = 100
SORTBY = "relevance"
SLEEP_SECONDS = 0.2

INCLUDE_NEWSPAPER = ["links"]

TOPIC = "armenian_genocide_au_press"

QUERIES = [
    '"Armenian Genocide"',
    'armenian AND (deportation OR deportations OR deported OR "death march")',
    'armenian AND (massacre OR massacres OR atrocities)',
    'armenian AND (refugees OR orphan OR relief OR "relief fund")',
]


def year_from_date(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    m = re.match(r"^(\d{4})", str(date_str))
    return int(m.group(1)) if m else None

GENOCIDE_KEYWORDS = [
    "armenian genocide",
    "genocide of the armenians",
    "armenian deportation",
    "armenian deportations",
    "death march",
    "mass extermination",
    "extermination of armenians",
    "annihilation of armenians",
    # optional broader signals:
    "deportation",
    "deportations",
    "deported",
    "massacre",
    "massacres",
    "atrocities",
]

def looks_like_genocide(row: Dict[str, Any]) -> bool:

    y = year_from_date(row.get("date_or_period"))
    if y is None or not (1915 <= y <= 1923):
        return False

    text = " ".join([
        row.get("title") or "",
        row.get("description_or_abstract") or "",
    ]).lower()

    return any(k in text for k in GENOCIDE_KEYWORDS)

def norm(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s or None

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def load_state() -> dict:
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_state(state: dict) -> None:
    ensure_dir(os.path.dirname(STATE_PATH))
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def append_jsonl(row: dict, path: str) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

def get_with_retries(url: str, params: List[Tuple[str, str]], timeout: int = 90, max_tries: int = 6) -> requests.Response:

    last_err = None
    for attempt in range(1, max_tries + 1):
        try:
            return requests.get(url, params=params, timeout=timeout)
        except (requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectTimeout,
                requests.exceptions.ConnectionError) as e:
            last_err = e
            sleep_s = min(60, 2 ** attempt)
            print(f"  [retry {attempt}/{max_tries}] timeout/network error. Sleeping {sleep_s}s")
            time.sleep(sleep_s)
    raise last_err


def find_records(payload: Any) -> List[Dict[str, Any]]:
    try:
        cats = payload.get("category", [])
        if not cats:
            return []
        recs = cats[0].get("records", {})
        articles = recs.get("article", [])
        return articles if isinstance(articles, list) else []
    except Exception:
        return []

def find_next_cursor(payload: Any) -> Optional[str]:
    try:
        cats = payload.get("category", [])
        if not cats:
            return None
        recs = cats[0].get("records", {})
        nxt = recs.get("nextStart")
        if isinstance(nxt, str) and nxt.strip():
            return nxt.strip()
        return None
    except Exception:
        return None


def extract_newspaper_article(article: Dict[str, Any], category: str, query: str) -> Dict[str, Any]:
    return {
        "topic": TOPIC,
        "query": query,
        "trove_category": category,
        "trove_record_type": "article",

        "title": norm(article.get("heading")),
        "date_or_period": norm(article.get("date")),
        "author_or_creator": norm(article.get("byline")),
        "description_or_abstract": norm(article.get("snippet")),
        "url_to_original_object": article.get("troveUrl"),

        "manuscript_id_or_shelfmark": None,
        "material": None,
        "dimensions": None,

        "trove_id": norm(str(article.get("id") or article.get("@id") or "")),
        "trove_url": article.get("troveUrl"),
    }


def harvest_query_category_stream(api_key: str, query: str, category: str, max_records: Optional[int]) -> int:
    ensure_dir(OUT_DIR)

    seen_ids = set()
    if os.path.exists(OUT_JSONL):
        with open(OUT_JSONL, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    tid = obj.get("trove_id")
                    if tid:
                        seen_ids.add(tid)
                except Exception:
                    continue

    state = load_state()
    state_key = f"{TOPIC}::{category}::{query}"
    cursor = state.get(state_key, "*")
    seen_cursors = {cursor}

    harvested = 0
    includes = INCLUDE_NEWSPAPER if category == "newspaper" else ["links"]

    while True:
        if max_records is not None and harvested >= max_records:
            break

        params: List[Tuple[str, str]] = [
            ("key", api_key),
            ("encoding", "json"),
            ("category", category),
            ("q", query),
            ("reclevel", "full"),
            ("n", str(min(PAGE_SIZE, 100))),
            ("sortby", SORTBY),
            ("s", cursor),
        ]
        for inc in includes:
            params.append(("include", inc))

        r = get_with_retries(API_URL, params=params, timeout=90, max_tries=6)
        if r.status_code != 200:
            raise RuntimeError(f"Trove API error {r.status_code}: {r.text[:800]}")

        payload = r.json()
        records = find_records(payload)

        if not records:
            state[state_key] = cursor
            save_state(state)
            break

        for rec in records:
            if max_records is not None and harvested >= max_records:
                break

            row = extract_newspaper_article(rec, category, query)

            if not looks_like_genocide(row):
                continue

            tid = row.get("trove_id")
            if tid and tid in seen_ids:
                continue
            if tid:
                seen_ids.add(tid)

            append_jsonl(row, OUT_JSONL)
            harvested += 1

        next_cursor = find_next_cursor(payload)
        if not next_cursor:
            state[state_key] = cursor
            save_state(state)
            break

        if next_cursor in seen_cursors:
            state[state_key] = next_cursor
            save_state(state)
            break

        seen_cursors.add(next_cursor)
        cursor = next_cursor

        state[state_key] = cursor
        save_state(state)

        time.sleep(SLEEP_SECONDS)

    return harvested

def jsonl_to_csv(jsonl_path: str, csv_path: str) -> None:
    columns = [
        "title",
        "date_or_period",
        "author_or_creator",
        "description_or_abstract",
        "url_to_original_object",
        "manuscript_id_or_shelfmark",
        "material",
        "dimensions",
        "trove_category",
        "trove_record_type",
        "trove_id",
        "trove_url",
    ]
    ensure_dir(os.path.dirname(csv_path))

    with open(jsonl_path, "r", encoding="utf-8") as fin, open(csv_path, "w", encoding="utf-8", newline="") as fout:
        w = csv.DictWriter(fout, fieldnames=columns)
        w.writeheader()
        for line in fin:
            obj = json.loads(line)
            w.writerow({c: obj.get(c) for c in columns})

def main() -> None:
    if not TROVE_API_KEY:
        raise SystemExit(
            "Missing TROVE_API_KEY.\n"
            "PyCharm: Run -> Edit Configurations -> Environment variables\n"
            "Add: TROVE_API_KEY=YOUR_KEY\n"
        )

    ensure_dir(OUT_DIR)

    print("Topic:", TOPIC)
    print("Categories:", ", ".join(CATEGORIES))
    print("Queries:", len(QUERIES))
    print("Max per query per category:", MAX_RECORDS_PER_QUERY_PER_CATEGORY)
    print("Output:", OUT_JSONL)
    print()

    total = 0
    for q in QUERIES:
        print(f"\n=== Query: {q}")
        for cat in CATEGORIES:
            print(f"Harvesting {cat} ...")
            try:
                got = harvest_query_category_stream(
                    api_key=TROVE_API_KEY,
                    query=q,
                    category=cat,
                    max_records=MAX_RECORDS_PER_QUERY_PER_CATEGORY,
                )
                total += got
                print(f"  -> added {got} new rows")
            except Exception as e:
                print(f"  !! Skipping due to error: {e}")
                continue

    if os.path.exists(OUT_JSONL):
        print("\nConverting JSONL -> CSV ...")
        jsonl_to_csv(OUT_JSONL, OUT_CSV)
    else:
        print("\nNo JSONL file created (0 results). Skipping CSV conversion.")

    print("\nDONE ✅")
    print("Rows added this run:", total)
    print("JSONL:", OUT_JSONL)
    print("CSV:", OUT_CSV)
    print("Resume state:", STATE_PATH)

if __name__ == "__main__":
    main()

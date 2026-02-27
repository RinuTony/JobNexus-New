import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests


def _split_env_list(value: str) -> List[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def _to_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        parts = value.replace("|", ",").split(",")
        return [p.strip() for p in parts if p.strip()]
    return [str(value).strip()]


def _pick(row: Dict, keys: List[str], default=None):
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    return default


def _normalize_course(row: Dict, source_hint: str = "") -> Optional[Dict]:
    title = _pick(row, ["title", "name", "course_title", "courseName"])
    url = _pick(row, ["url", "link", "course_url", "course_link"])
    if not title and not url:
        return None

    skills = _pick(row, ["skills", "tags", "keywords", "topics"], [])
    description = _pick(row, ["description", "summary", "snippet", "about"], "")
    provider = _pick(row, ["provider", "platform", "university", "org"], "")
    source = _pick(row, ["source", "domain"], source_hint or provider)
    level = _pick(row, ["level", "difficulty"], "")
    duration = _pick(row, ["duration", "length"], "Varies")
    price = _pick(row, ["price", "cost"], "")
    rating = _pick(row, ["rating", "stars"], None)
    instructor = _pick(row, ["instructor", "teacher"], "")
    is_free = _pick(row, ["free", "is_free"], False)

    return {
        "title": str(title or "Course").strip(),
        "url": str(url or "").strip(),
        "description": str(description or "").strip(),
        "skills": _to_list(skills),
        "provider": str(provider or "").strip(),
        "source": str(source or "").strip(),
        "level": str(level or "").strip(),
        "duration": str(duration or "Varies").strip(),
        "price": str(price or "").strip(),
        "rating": rating,
        "instructor": str(instructor or "").strip(),
        "free": bool(is_free),
    }


def _load_records_from_json(content: str) -> List[Dict]:
    payload = json.loads(content)
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("courses") or payload.get("items") or payload.get("data") or []
    else:
        rows = []
    return [r for r in rows if isinstance(r, dict)]


def _load_records_from_csv(content: str) -> List[Dict]:
    reader = csv.DictReader(content.splitlines())
    return [dict(row) for row in reader]


def _load_records_from_html(content: str, source_name: str) -> List[Dict]:
    rows: List[Dict] = []
    base_url = source_name if source_name.startswith("http") else ""
    netloc = urlparse(base_url).netloc.lower()

    # 1) Prefer structured data (JSON-LD).
    scripts = re.findall(
        r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for script_body in scripts:
        script_text = script_body.strip()
        if not script_text:
            continue
        try:
            payload = json.loads(script_text)
        except Exception:
            continue

        queue = payload if isinstance(payload, list) else [payload]
        while queue:
            item = queue.pop(0)
            if isinstance(item, list):
                queue.extend(item)
                continue
            if not isinstance(item, dict):
                continue

            item_type = str(item.get("@type", "")).lower()
            if item_type == "itemlist" and isinstance(item.get("itemListElement"), list):
                queue.extend(item.get("itemListElement", []))
                continue
            if isinstance(item.get("item"), dict):
                queue.append(item.get("item"))
                continue

            if item_type in {"course", "courseinstance", "creativework"}:
                name = item.get("name") or item.get("headline")
                link = item.get("url")
                desc = item.get("description", "")
                provider = ""
                prov = item.get("provider")
                if isinstance(prov, dict):
                    provider = str(prov.get("name", ""))
                elif prov:
                    provider = str(prov)
                if name or link:
                    rows.append(
                        {
                            "title": name,
                            "url": link,
                            "description": desc,
                            "provider": provider or netloc,
                            "source": netloc,
                        }
                    )

    # 2) Fallback: scrape anchor tags that look like course pages.
    if not rows:
        anchor_matches = re.findall(
            r"<a[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
            content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        for href, raw_title in anchor_matches:
            title = re.sub(r"<[^>]+>", " ", raw_title)
            title = re.sub(r"\s+", " ", title).strip()
            link = urljoin(base_url, href.strip()) if base_url else href.strip()
            blob = f"{href} {title}".lower()
            if not title or len(title) < 4:
                continue
            if not any(k in blob for k in ["course", "learn", "certificate", "specialization", "tutorial"]):
                continue
            rows.append(
                {
                    "title": title,
                    "url": link,
                    "description": "",
                    "provider": netloc,
                    "source": netloc,
                }
            )

    # De-duplicate rows from scraped content.
    deduped = []
    seen = set()
    for r in rows:
        key = f"{str(r.get('url','')).strip().lower()}|{str(r.get('title','')).strip().lower()}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    return deduped


def _records_from_content(content: str, mime: str, source_name: str) -> List[Dict]:
    mime = (mime or "").lower()
    source_name = source_name.lower()
    if "json" in mime or source_name.endswith(".json"):
        return _load_records_from_json(content)
    if "csv" in mime or source_name.endswith(".csv"):
        return _load_records_from_csv(content)
    if "html" in mime or source_name.endswith(".html") or "<html" in content[:4000].lower():
        return _load_records_from_html(content, source_name)

    # Fallback order: JSON -> CSV -> HTML.
    try:
        return _load_records_from_json(content)
    except Exception:
        try:
            return _load_records_from_csv(content)
        except Exception:
            return _load_records_from_html(content, source_name)


def _load_from_url(url: str, timeout: int) -> Tuple[List[Dict], str]:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    rows = _records_from_content(response.text, content_type, url)
    return rows, content_type


def _load_from_file(path: Path) -> Tuple[List[Dict], str]:
    text = path.read_text(encoding="utf-8")
    rows = _records_from_content(text, "", str(path))
    return rows, "file"


def sync_catalog(
    output_path: Path,
    source_urls: Optional[Iterable[str]] = None,
    source_files: Optional[Iterable[str]] = None,
    timeout: int = 25,
) -> Dict:
    """
    Sync catalog from configured URLs/files and write normalized JSON.
    """
    if source_urls is None:
        source_urls = _split_env_list(os.getenv("COURSE_SOURCE_URLS", ""))
    scrape_urls = _split_env_list(os.getenv("COURSE_SCRAPE_URLS", ""))
    if scrape_urls:
        source_urls = list(source_urls) + scrape_urls
    if source_files is None:
        source_files = _split_env_list(os.getenv("COURSE_SOURCE_FILES", ""))

    all_courses: List[Dict] = []
    source_stats: List[Dict] = []

    for url in source_urls:
        try:
            rows, content_type = _load_from_url(url, timeout=timeout)
            normalized = []
            for row in rows:
                course = _normalize_course(row, source_hint=url)
                if course:
                    normalized.append(course)
            all_courses.extend(normalized)
            source_stats.append(
                {
                    "source": url,
                    "kind": "url",
                    "rows": len(rows),
                    "courses": len(normalized),
                    "content_type": content_type,
                    "status": "ok",
                }
            )
        except Exception as exc:
            source_stats.append(
                {
                    "source": url,
                    "kind": "url",
                    "status": "error",
                    "error": str(exc),
                }
            )

    for file_path in source_files:
        p = Path(file_path).expanduser()
        try:
            rows, content_type = _load_from_file(p)
            normalized = []
            for row in rows:
                course = _normalize_course(row, source_hint=str(p))
                if course:
                    normalized.append(course)
            all_courses.extend(normalized)
            source_stats.append(
                {
                    "source": str(p),
                    "kind": "file",
                    "rows": len(rows),
                    "courses": len(normalized),
                    "content_type": content_type,
                    "status": "ok",
                }
            )
        except Exception as exc:
            source_stats.append(
                {
                    "source": str(p),
                    "kind": "file",
                    "status": "error",
                    "error": str(exc),
                }
            )

    # Deduplicate by URL first, then title/provider fallback.
    deduped = []
    seen = set()
    for c in all_courses:
        key = (c.get("url") or "").strip().lower()
        if not key:
            key = f"{(c.get('title') or '').strip().lower()}|{(c.get('provider') or '').strip().lower()}"
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(c)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "course_count": len(deduped),
        "courses": deduped,
        "sources": source_stats,
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return payload

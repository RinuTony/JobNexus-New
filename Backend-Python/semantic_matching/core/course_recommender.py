import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus
from urllib.parse import urlparse

import faiss
import requests

from .course_catalog_sync import sync_catalog
from .embeddings import Embedder


class CourseRecommender:
    """
    Local vector-search recommender over a synced course catalog.
    No runtime dependency on third-party recommendation APIs.
    """

    def __init__(self):
        base_dir = Path(__file__).resolve().parent.parent
        data_dir = base_dir / "data"

        self.catalog_path = Path(
            os.getenv("COURSE_CATALOG_PATH", str(data_dir / "course_catalog.json"))
        )
        self.index_path = Path(
            os.getenv("COURSE_INDEX_PATH", str(data_dir / "course_index.faiss"))
        )
        self.meta_path = Path(
            os.getenv("COURSE_INDEX_META_PATH", str(data_dir / "course_index_meta.json"))
        )

        self.auto_sync = os.getenv("COURSE_AUTO_SYNC", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.sync_interval_hours = int(os.getenv("COURSE_SYNC_INTERVAL_HOURS", "24"))
        self.default_top_k = int(os.getenv("COURSE_TOP_K", "18"))
        self.embeddings_enabled = os.getenv("COURSE_ENABLE_EMBEDDINGS", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.live_search_enabled = os.getenv("COURSE_LIVE_SEARCH", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.live_timeout = int(os.getenv("COURSE_LIVE_TIMEOUT", "8"))
        self.live_sources = [
            s.strip().lower()
            for s in os.getenv("COURSE_LIVE_SOURCES", "classcentral").split(",")
            if s.strip()
        ]

        self.embedder = None
        self._embedder_init_attempted = False
        self.catalog_data: List[Dict] = []
        self.index = None
        self._last_sync_check = 0.0

        self.refresh_from_disk(force_rebuild=False)

    def _get_embedder(self):
        if not self.embeddings_enabled:
            return None
        if self.embedder is not None:
            return self.embedder
        if self._embedder_init_attempted:
            return None
        self._embedder_init_attempted = True
        try:
            self.embedder = Embedder()
            return self.embedder
        except Exception:
            self.embedder = None
            return None

    def refresh_from_disk(self, force_rebuild: bool = False) -> None:
        self.catalog_data = self._load_catalog()
        if not self.catalog_data:
            self.index = None
            return
        self.index = self._load_or_build_index(force_rebuild=force_rebuild)

    def _load_catalog(self) -> List[Dict]:
        if not self.catalog_path.exists():
            return []

        try:
            payload = json.loads(self.catalog_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                courses = payload.get("courses", [])
            else:
                courses = payload
            if isinstance(courses, list):
                return [c for c in courses if isinstance(c, dict)]
        except Exception:
            return []
        return []

    def _catalog_signature(self, courses: List[Dict]) -> str:
        rows = []
        for c in courses:
            rows.append(
                f"{c.get('url','')}|{c.get('title','')}|{c.get('provider','')}|{c.get('source','')}"
            )
        joined = "\n".join(sorted(rows))
        return hashlib.sha1(joined.encode("utf-8")).hexdigest()

    def _course_text(self, c: Dict) -> str:
        skills = c.get("skills", [])
        if isinstance(skills, list):
            skills_text = " ".join(str(s) for s in skills if s)
        else:
            skills_text = str(skills or "")

        parts = [
            str(c.get("title") or ""),
            str(c.get("description") or ""),
            str(c.get("provider") or ""),
            str(c.get("level") or ""),
            skills_text,
        ]
        return " ".join(p for p in parts if p).strip()

    def _load_or_build_index(self, force_rebuild: bool = False):
        signature = self._catalog_signature(self.catalog_data)

        if not force_rebuild and self.index_path.exists() and self.meta_path.exists():
            try:
                meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
                if meta.get("catalog_signature") == signature:
                    return faiss.read_index(str(self.index_path))
            except Exception:
                pass

        texts = [self._course_text(c) for c in self.catalog_data]
        if not texts:
            return None

        embedder = self._get_embedder()
        if embedder is None:
            return None

        embeddings = embedder.encode_batch(texts).astype("float32")
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        dim = int(embeddings.shape[1])
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(self.index_path))
        self.meta_path.write_text(
            json.dumps(
                {
                    "catalog_signature": signature,
                    "course_count": len(self.catalog_data),
                    "dimension": dim,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return index

    def _normalize_source(self, value: str) -> str:
        v = (value or "").lower().strip()
        if not v:
            return "unknown"
        if "youtube" in v or "youtu.be" in v:
            return "youtube"
        if "coursera" in v:
            return "coursera"
        if "edx" in v:
            return "edx"
        if "udemy" in v:
            return "udemy"
        if "classcentral" in v:
            return "classcentral"
        return v.replace("www.", "").split("/")[0]

    def _live_search_templates(self) -> Dict[str, str]:
        return {
            "classcentral": "https://www.classcentral.com/search?q={q}",
            "coursera": "https://www.coursera.org/search?query={q}",
            "edx": "https://www.edx.org/search?q={q}",
            "udemy": "https://www.udemy.com/courses/search/?q={q}",
        }

    def _extract_classcentral_via_jina(self, skill: str, limit: int = 8) -> List[Dict]:
        proxy_url = f"https://r.jina.ai/http://www.classcentral.com/search?q={quote_plus(skill)}"
        try:
            response = requests.get(
                proxy_url,
                timeout=max(self.live_timeout, 12),
                headers={"User-Agent": "Mozilla/5.0 JobNexusBot/1.0"},
            )
            if response.status_code >= 400:
                return []
            text = response.text or ""

            matches = re.findall(
                r"\[([^\]]+)\]\((https?://www\.classcentral\.com/course/[^\)\s]+)\)",
                text,
                flags=re.IGNORECASE,
            )
            results = []
            seen = set()
            for raw_title, url in matches:
                title = re.sub(r"\s+", " ", raw_title).strip(" -\n\t")
                low = title.lower()
                if not title or len(title) < 4:
                    continue
                if any(x in low for x in ["review", "rating", "ratings at", "reviews at"]):
                    continue
                if re.fullmatch(r"\d+\s*(reviews?|ratings?)", low):
                    continue
                key = (url or title).strip().lower()
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    {
                        "title": title[:140],
                        "url": url.replace("http://", "https://"),
                        "snippet": f"Class Central result for {skill}",
                        "source": "classcentral",
                        "provider": "Class Central",
                        "duration": "Varies",
                        "free": False,
                    }
                )
                if len(results) >= limit:
                    break
            return results
        except Exception:
            return []

    def _extract_site_results_via_jina(self, site: str, skill: str, limit: int = 8) -> List[Dict]:
        if site == "coursera":
            source_url = f"http://www.coursera.org/search?query={quote_plus(skill)}"
            url_pattern = r"https?://www\.coursera\.org/(learn|specializations|professional-certificates)/[^\)\s]+"
            provider = "Coursera"
        elif site == "edx":
            source_url = f"http://www.edx.org/search?q={quote_plus(skill)}"
            url_pattern = r"https?://www\.edx\.org/(learn|course|certificate|program)/[^\)\s]+"
            provider = "edX"
        else:
            return []

        proxy_url = f"https://r.jina.ai/{source_url}"
        try:
            response = requests.get(
                proxy_url,
                timeout=max(self.live_timeout, 12),
                headers={"User-Agent": "Mozilla/5.0 JobNexusBot/1.0"},
            )
            if response.status_code >= 400:
                return []
            text = response.text or ""

            pairs = re.findall(r"\[([^\]]+)\]\((https?://[^\)\s]+)\)", text, flags=re.IGNORECASE)
            results = []
            seen = set()
            tokens = [t for t in (skill or "").lower().split() if len(t) > 2]

            for raw_title, url in pairs:
                if not re.match(url_pattern, url, flags=re.IGNORECASE):
                    continue
                title = re.sub(r"\s+", " ", raw_title).strip(" -\n\t")
                low = title.lower()
                if not title or len(title) < 4:
                    continue
                if any(x in low for x in ["review", "rating", "ratings", "reviews", "image "]):
                    continue
                if re.fullmatch(r"\d+\s*(reviews?|ratings?)", low):
                    continue
                if tokens and not any(t in (low + " " + url.lower()) for t in tokens):
                    continue

                key = (url or title).strip().lower()
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    {
                        "title": title[:140],
                        "url": url.replace("http://", "https://"),
                        "snippet": f"{provider} result for {skill}",
                        "source": site,
                        "provider": provider,
                        "duration": "Varies",
                        "free": False,
                    }
                )
                if len(results) >= limit:
                    break
            return results
        except Exception:
            return []

    def _extract_links_from_html(self, html: str, skill: str, source: str) -> List[Dict]:
        # Lightweight parser for anchor tags without extra dependencies.
        links = re.findall(
            r"<a[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
            html or "",
            flags=re.IGNORECASE | re.DOTALL,
        )
        out = []
        seen = set()
        tokens = [t for t in (skill or "").lower().split() if len(t) > 2]

        for href, raw_title in links:
            title = re.sub(r"<[^>]+>", " ", raw_title)
            title = re.sub(r"\s+", " ", title).strip()
            if not href or not title or len(title) < 3:
                continue

            # Normalize URL.
            if href.startswith("/"):
                if source == "classcentral":
                    url = "https://www.classcentral.com" + href
                elif source == "coursera":
                    url = "https://www.coursera.org" + href
                elif source == "edx":
                    url = "https://www.edx.org" + href
                elif source == "udemy":
                    url = "https://www.udemy.com" + href
                else:
                    url = href
            else:
                url = href

            blob = f"{title} {url}".lower()
            if source == "classcentral" and "/course/" not in blob and "classcentral.com" not in blob:
                continue

            # Keep links that look relevant to the requested skill.
            if tokens and not any(t in blob for t in tokens):
                continue

            key = (url or title).strip().lower()
            if key in seen:
                continue
            seen.add(key)

            out.append(
                {
                    "title": title[:140],
                    "url": url,
                    "snippet": f"Search result for {skill}",
                    "source": source,
                    "provider": source,
                    "duration": "Varies",
                    "free": False,
                }
            )
            if len(out) >= 8:
                break
        return out

    def _live_site_search(self, skill: str, sources: Optional[List[str]], per_source: int) -> List[Dict]:
        if not self.live_search_enabled:
            return []

        templates = self._live_search_templates()
        requested = self._normalize_requested_sources(sources)
        candidates = [s for s in self.live_sources if s in templates]
        if requested:
            candidates = [s for s in candidates if s in requested]
        if not candidates:
            return []

        all_results: List[Dict] = []
        for src in candidates:
            url = templates[src].format(q=quote_plus(skill))
            try:
                response = requests.get(
                    url,
                    timeout=self.live_timeout,
                    headers={"User-Agent": "Mozilla/5.0 JobNexusBot/1.0"},
                )
                parsed = []
                if src == "classcentral":
                    parsed = self._extract_classcentral_via_jina(skill=skill, limit=max(2, per_source))
                elif src in {"coursera", "edx"}:
                    parsed = self._extract_site_results_via_jina(site=src, skill=skill, limit=max(2, per_source))
                if response.status_code < 400 and not parsed:
                    parsed = self._extract_links_from_html(response.text, skill=skill, source=src)
                if not parsed:
                    # Fallback to providing the source search page even when blocked.
                    parsed = [
                        {
                            "title": f"{src.title()} results for {skill}",
                            "url": url,
                            "snippet": f"Open {src.title()} search for {skill}",
                            "source": src,
                            "provider": src.title(),
                            "duration": "Varies",
                            "free": False,
                        }
                    ]
                all_results.extend(parsed[: max(2, per_source)])
            except Exception:
                all_results.append(
                    {
                        "title": f"{src.title()} results for {skill}",
                        "url": url,
                        "snippet": f"Open {src.title()} search for {skill}",
                        "source": src,
                        "provider": src.title(),
                        "duration": "Varies",
                        "free": False,
                    }
                )

        # de-dup
        dedup = []
        seen = set()
        for r in all_results:
            key = (r.get("url") or r.get("title") or "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            dedup.append(r)
        return dedup

    def _course_source(self, course: Dict) -> str:
        src = self._normalize_source(str(course.get("source", "")))
        if src != "unknown":
            return src
        url = str(course.get("url", ""))
        if url:
            return self._normalize_source(urlparse(url).netloc)
        return "unknown"

    def _normalize_requested_sources(self, sources: Optional[List[str]]) -> Optional[set]:
        if not sources:
            return None
        normalized = set()
        for s in sources:
            if not s:
                continue
            s = s.strip().lower()
            if "." in s:
                s = s.split(".")[-2] if len(s.split(".")) > 1 else s
            normalized.add(self._normalize_source(s))
        return normalized or None

    def _score_by_keyword_overlap(self, skill: str, course: Dict) -> float:
        text = self._course_text(course).lower()
        tokens = [t for t in skill.lower().split() if len(t) > 2]
        if not tokens:
            return 0.0
        overlap = sum(1 for t in tokens if t in text)
        return overlap / max(1, len(tokens))

    def _relevance_score(self, skill: str, course: Dict, base_score: float = 0.0) -> float:
        phrase = (skill or "").strip().lower()
        tokens = [t for t in phrase.split() if len(t) > 2]
        if not tokens:
            return base_score

        title = str(course.get("title", "")).lower()
        desc = str(course.get("description", "")).lower()
        skills = course.get("skills", [])
        if isinstance(skills, list):
            skills_text = " ".join(str(s).lower() for s in skills)
        else:
            skills_text = str(skills or "").lower()

        token_hits = 0.0
        for t in tokens:
            if t in title:
                token_hits += 3.0
            if t in skills_text:
                token_hits += 4.0
            if t in desc:
                token_hits += 1.5

        phrase_bonus = 4.0 if phrase and (phrase in title or phrase in skills_text or phrase in desc) else 0.0
        source = self._course_source(course)
        source_bonus = 0.4 if source != "youtube" else 0.0
        return float(base_score) + token_hits + phrase_bonus + source_bonus

    def _search(
        self, skill: str, top_k: int, sources: Optional[set]
    ) -> List[Tuple[float, Dict]]:
        if not self.catalog_data:
            return []

        if self.index is None:
            scored = []
            for c in self.catalog_data:
                src = self._course_source(c)
                if sources and src not in sources:
                    continue
                score = self._score_by_keyword_overlap(skill, c)
                scored.append((score, c))
            scored.sort(key=lambda x: x[0], reverse=True)
            return scored[:top_k]

        embedder = self._get_embedder()
        if embedder is None:
            scored = []
            for c in self.catalog_data:
                src = self._course_source(c)
                if sources and src not in sources:
                    continue
                score = self._score_by_keyword_overlap(skill, c)
                scored.append((score, c))
            scored.sort(key=lambda x: x[0], reverse=True)
            return scored[:top_k]

        query = embedder.encode(f"{skill} course tutorial").astype("float32")
        if query.ndim == 1:
            query = query.reshape(1, -1)

        distances, indices = self.index.search(query, top_k * 3)
        results: List[Tuple[float, Dict]] = []

        for score, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.catalog_data):
                continue
            course = self.catalog_data[int(idx)]
            src = self._course_source(course)
            if sources and src not in sources:
                continue
            results.append((float(score), course))
            if len(results) >= top_k:
                break
        return results

    def _maybe_sync_catalog(self) -> None:
        if not self.auto_sync:
            return

        now = float(time.time())
        if now - self._last_sync_check < 60:
            return
        self._last_sync_check = now

        age_seconds = 10**12
        if self.catalog_path.exists():
            age_seconds = max(0.0, now - self.catalog_path.stat().st_mtime)
        is_stale = age_seconds >= self.sync_interval_hours * 3600

        has_sources = bool(os.getenv("COURSE_SOURCE_URLS") or os.getenv("COURSE_SOURCE_FILES"))
        if not is_stale or not has_sources:
            return

        try:
            sync_catalog(output_path=self.catalog_path)
            self.refresh_from_disk(force_rebuild=True)
        except Exception:
            # Never break matching flow if sync fails.
            pass

    def _to_payload(self, course: Dict) -> Dict:
        source = self._course_source(course)
        price = course.get("price")
        return {
            "title": course.get("title", "Course"),
            "url": course.get("url", ""),
            "snippet": course.get("description", "")[:220],
            "source": source,
            "provider": course.get("provider") or source,
            "instructor": course.get("instructor"),
            "duration": course.get("duration", "Varies"),
            "level": course.get("level"),
            "price": price,
            "rating": course.get("rating"),
            "free": bool(course.get("free", False) or str(price).strip().lower() in {"free", "0", "0.0"}),
        }

    def get_course_recommendations(
        self,
        skill: str,
        sources: Optional[List[str]] = None,
        per_source: int = 3,
    ) -> Dict[str, List[Dict]]:
        self._maybe_sync_catalog()

        normalized_sources = self._normalize_requested_sources(sources)
        top_k = max(8, per_source * (len(normalized_sources) if normalized_sources else 4) * 2)
        top_k = max(top_k, self.default_top_k)

        ranked = self._search(skill=skill, top_k=top_k, sources=normalized_sources)
        live_results = self._live_site_search(skill=skill, sources=sources, per_source=per_source)

        youtube_videos: List[Dict] = []
        online_courses: List[Dict] = []
        seen_keys = set()
        scored = []
        for base, course in ranked:
            lexical = self._relevance_score(skill, course, base_score=0.0)
            combined = self._relevance_score(skill, course, base_score=base)
            scored.append((combined, lexical, course))
        scored.sort(key=lambda x: x[0], reverse=True)

        # First pass: keep only skill-relevant courses.
        relevant = [(score, lexical, c) for score, lexical, c in scored if lexical >= 1.0]
        fallback = scored if relevant else scored

        def collect(items, strict_youtube: bool = True):
            for score, lexical, course in items:
                payload = self._to_payload(course)
                key = (payload.get("url") or payload.get("title") or "").strip().lower()
                if not key or key in seen_keys:
                    continue
                seen_keys.add(key)

                if payload["source"] == "youtube":
                    if strict_youtube and lexical < 1.0:
                        continue
                    if len(youtube_videos) < max(2, per_source):
                        youtube_videos.append(payload)
                else:
                    if len(online_courses) < max(6, per_source * 3):
                        online_courses.append(payload)

                if len(youtube_videos) >= max(2, per_source) and len(online_courses) >= max(6, per_source * 3):
                    break

        # Prioritize live site search results (e.g., Class Central skill search).
        for item in live_results:
            key = (item.get("url") or item.get("title") or "").strip().lower()
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            if item.get("source") == "youtube":
                if len(youtube_videos) < max(2, per_source):
                    youtube_videos.append(item)
            else:
                if len(online_courses) < max(6, per_source * 3):
                    online_courses.append(item)

        collect(relevant, strict_youtube=True)

        # Second pass: top up online courses first.
        if len(online_courses) < 2:
            collect(fallback, strict_youtube=True)

        # Last resort: allow broader YouTube only when no online courses are available.
        if len(youtube_videos) < 1 and len(online_courses) == 0:
            collect(fallback, strict_youtube=False)

        return {
            "youtube_videos": youtube_videos,
            "online_courses": online_courses,
        }

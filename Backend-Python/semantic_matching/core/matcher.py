# core/matcher.py
import numpy as np
import re
from typing import List, Dict, Tuple
from .embeddings import Embedder
from .extractor import extract_skills

class ResumeMatcher:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.embedder = Embedder(model_name)
        self.semantic_weight = 0.45
        self.section_weight = 0.35
        self.skill_weight = 0.20
        self.max_resume_head = 4000
        self.max_resume_tail = 1500
        self.low_req_skill_cap = 4
        self.low_req_jd_len = 350
        self.very_short_jd_len = 220
        self.semantic_skill_match_threshold = 0.72
        self.missing_skill_penalty_weight = 0.14
        self.required_skill_presence_boost = 0.12
        self.short_jd_boost_cap = 0.10
    
    def calculate_similarity(
        self,
        resume_text: str,
        jd_text: str,
        use_focus: bool = True,
        skills: List[str] = None,
        required_skills: List[str] = None
    ) -> float:
        """Calculate similarity between resume and job description.
        Combines document semantics, section-level similarity, and skill overlap.
        """
        if not resume_text or not jd_text:
            return 0.0

        jd_vec = self.embedder.encode(jd_text)

        # Base semantic similarity on a larger chunk to reduce truncation bias.
        head = resume_text[: self.max_resume_head]
        tail = resume_text[-self.max_resume_tail :] if len(resume_text) > self.max_resume_tail else resume_text
        base_text = head
        resume_vec = self.embedder.encode(base_text)
        semantic_sim = float(np.dot(resume_vec, jd_vec))

        # Section-level similarity: best match among head, tail, and skills text.
        section_texts = [head, tail]
        skills_text = ""
        if skills:
            skills_text = " ".join(skills[:40])
            section_texts.append(skills_text)
        section_sims = []
        for text in section_texts:
            if not text:
                continue
            vec = self.embedder.encode(text)
            section_sims.append(float(np.dot(vec, jd_vec)))
        section_sim = max(section_sims) if section_sims else semantic_sim

        # Skill overlap similarity.
        resume_skills = skills or extract_skills(resume_text)
        jd_skills = required_skills or extract_skills(jd_text)
        skill_sim = 0.0
        if resume_skills and jd_skills:
            resume_skill_text = " ".join(resume_skills[:60])
            jd_skill_text = " ".join(jd_skills[:60])
            resume_skill_vec = self.embedder.encode(resume_skill_text)
            jd_skill_vec = self.embedder.encode(jd_skill_text)
            semantic_skill_sim = float(np.dot(resume_skill_vec, jd_skill_vec))

            resume_set = {s.lower().strip() for s in resume_skills}
            jd_set = {s.lower().strip() for s in jd_skills}
            if resume_set and jd_set:
                jaccard = len(resume_set & jd_set) / max(len(resume_set | jd_set), 1)
            else:
                jaccard = 0.0

            skill_sim = 0.7 * semantic_skill_sim + 0.3 * jaccard

        final = (
            self.semantic_weight * semantic_sim
            + self.section_weight * section_sim
            + self.skill_weight * skill_sim
        )
        final = float(max(0.0, min(1.0, final)))

        # If JD has very low requirements, avoid unfairly low scores for strong resumes.
        jd_skill_count = len(jd_skills)
        if jd_skill_count <= self.low_req_skill_cap and len(jd_text) <= self.low_req_jd_len:
            resume_strength = self._resume_strength(resume_text, resume_skills)
            final = max(final, resume_strength)

        # Calibrate score distribution so strong matches are not overly compressed.
        skill_coverage = self._skill_coverage(resume_skills, jd_skills)
        final = self._calibrate_similarity(final, skill_coverage)

        # Apply explicit missing-skill penalty (semantic-aware).
        semantic_coverage = self._semantic_skill_coverage(resume_text, resume_skills, jd_skills)
        missing_ratio = max(0.0, 1.0 - semantic_coverage)
        req_count = max(1, len(jd_skills))
        # Damp penalty when recruiter entered very long required-skill lists.
        count_factor = min(1.0, (8.0 / float(req_count)) ** 0.35)
        penalty = self.missing_skill_penalty_weight * count_factor * (missing_ratio ** 1.15)
        final = final - penalty

        # Strong positive signal when recruiter-required skills are present.
        if required_skills:
            req_boost = self.required_skill_presence_boost * (semantic_coverage ** 1.2)
            final = final + req_boost

        # Small reward for very high required-skill coverage to avoid under-scoring near-perfect resumes.
        if semantic_coverage >= 0.85:
            bonus = 0.05 * ((semantic_coverage - 0.85) / 0.15)
            final = final + max(0.0, min(0.05, bonus))

        # Extra heuristic for short JDs: rely more on skill coverage and resume strength.
        jd_len = len(jd_text or "")
        if jd_len <= self.low_req_jd_len:
            resume_strength = self._resume_strength(resume_text, resume_skills)
            shortness = (
                (self.low_req_jd_len - jd_len) / max(1.0, (self.low_req_jd_len - self.very_short_jd_len))
                if jd_len > self.very_short_jd_len else 1.0
            )
            shortness = max(0.0, min(1.0, float(shortness)))
            short_boost = self.short_jd_boost_cap * shortness * (0.65 * semantic_coverage + 0.35 * resume_strength)
            final = final + short_boost

        # Quality floor: strong semantic/section alignment should not collapse to very low scores.
        quality_signal = 0.55 * section_sim + 0.45 * semantic_sim
        if quality_signal >= 0.55:
            if required_skills:
                floor = 0.35 + 0.35 * quality_signal + 0.30 * semantic_coverage
            else:
                floor = 0.30 + 0.45 * quality_signal + 0.25 * skill_coverage
            final = max(final, floor)

        return float(max(0.0, min(1.0, final)))

    def _resume_strength(self, resume_text: str, resume_skills: List[str]) -> float:
        """Estimate resume strength for low-requirement JDs."""
        skill_count = min(len(resume_skills), 30)
        length = len(resume_text)
        # Normalize to a 0..1 range with diminishing returns.
        skill_score = min(skill_count / 20.0, 1.0)
        length_score = min(length / 4000.0, 1.0)
        return 0.35 + 0.45 * skill_score + 0.20 * length_score

    def _skill_coverage(self, resume_skills: List[str], jd_skills: List[str]) -> float:
        if not jd_skills:
            return 0.0
        resume_set = {s.lower().strip() for s in resume_skills if s}
        jd_set = {s.lower().strip() for s in jd_skills if s}
        if not jd_set:
            return 0.0
        covered = len(resume_set & jd_set)
        return covered / max(len(jd_set), 1)

    def _lexical_similarity(self, a: str, b: str) -> float:
        x = (a or "").lower().strip()
        y = (b or "").lower().strip()
        if not x or not y:
            return 0.0
        if x == y:
            return 1.0
        if x in y or y in x:
            return 0.9
        xs = set(x.split())
        ys = set(y.split())
        if not xs or not ys:
            return 0.0
        inter = len(xs & ys)
        if inter == 0:
            return 0.0
        return inter / max(len(xs | ys), 1)

    def _raw_text_contains_skill(self, resume_text: str, skill: str) -> bool:
        s = (skill or "").lower().strip()
        if not s:
            return False

        resume_lower = (resume_text or "").lower()
        spaced = re.sub(r"[^a-z0-9+#./-]+", " ", resume_lower)
        spaced = re.sub(r"\s+", " ", spaced).strip()
        if s in spaced:
            return True

        parts = [p for p in s.split() if p]
        if len(parts) > 1 and all(p in spaced for p in parts):
            return True

        compact_resume = re.sub(r"[^a-z0-9+#]+", "", resume_lower)
        compact_skill = re.sub(r"[^a-z0-9+#]+", "", s)
        if len(compact_skill) > 2 and compact_skill in compact_resume:
            return True
        return False

    def _semantic_skill_coverage(self, resume_text: str, resume_skills: List[str], jd_skills: List[str]) -> float:
        """
        Coverage ratio of JD skills found in resume using exact + lexical + semantic match.
        """
        if not jd_skills:
            return 0.0
        if not resume_skills:
            return 0.0

        resume_list = [s.lower().strip() for s in resume_skills if s]
        jd_list = [s.lower().strip() for s in jd_skills if s]
        if not jd_list or not resume_list:
            return 0.0

        resume_set = set(resume_list)
        covered = 0

        # Compute embeddings once for semantic fallback.
        resume_emb = self.embedder.encode_batch(resume_list)
        jd_emb = self.embedder.encode_batch(jd_list)

        for j_idx, jd_skill in enumerate(jd_list):
            # Robust direct text check first (handles extraction tokenization misses).
            if self._raw_text_contains_skill(resume_text, jd_skill):
                covered += 1
                continue

            if jd_skill in resume_set:
                covered += 1
                continue

            # Lexical fallback first.
            lex_best = 0.0
            for r_skill in resume_list:
                sim = self._lexical_similarity(jd_skill, r_skill)
                if sim > lex_best:
                    lex_best = sim
            if lex_best >= 0.8:
                covered += 1
                continue

            # Semantic fallback.
            jv = jd_emb[j_idx]
            best_sem = 0.0
            for r_idx in range(len(resume_list)):
                rv = resume_emb[r_idx]
                sem = float(np.dot(jv, rv))
                if sem > best_sem:
                    best_sem = sem
            if best_sem >= self.semantic_skill_match_threshold:
                covered += 1

        return covered / max(len(jd_list), 1)

    def _calibrate_similarity(self, raw_score: float, skill_coverage: float) -> float:
        """
        Monotonic calibration:
        - Decompresses medium/high ranges (common embedding-score compression issue).
        - Uses JD skill coverage as a secondary stabilizer.
        """
        x = float(max(0.0, min(1.0, raw_score)))
        coverage = float(max(0.0, min(1.0, skill_coverage)))

        # Logistic stretch centered around typical mid-score region.
        # raw 0.40 -> ~0.40, raw 0.50 -> ~0.60, raw 0.60 -> ~0.77
        stretched = 1.0 / (1.0 + np.exp(-8.0 * (x - 0.45)))

        # Blend with skill coverage while preserving monotonicity.
        calibrated = 0.85 * stretched + 0.15 * coverage

        # Never reduce the original score.
        return max(x, float(calibrated))
    
    def rank_resumes(self, resumes: List[Dict], jd_text: str) -> List[Dict]:
        """Rank multiple resumes against job description"""
        results = []
        for resume in resumes:
            similarity = self.calculate_similarity(
                resume_text=resume.get("text", ""),
                jd_text=jd_text,
                skills=resume.get("skills")
            )
            results.append({
                **resume,
                "similarity_score": similarity
            })
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results

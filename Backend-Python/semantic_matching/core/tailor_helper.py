# core/tailor_helper.py
import re
from copy import deepcopy
from typing import Any, Dict, List, Optional

from .extractor import extract_skills


class TailorHelper:
    """
    Local resume tailoring helper with deterministic rules.
    Keeps structure intact and does not depend on external LLM APIs.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key  # kept for compatibility

    def tailor_resume(self, resume_data: Dict[str, Any], job_description: str) -> Dict[str, Any]:
        try:
            jd_skills = extract_skills(job_description, similarity_threshold=0.35)
            jd_skill_set = {self._norm(s) for s in jd_skills if s}

            tailored = deepcopy(resume_data or {})
            changes: List[str] = []

            self._tailor_summary(tailored, jd_skills, changes)
            self._tailor_skills(tailored, jd_skill_set, changes)
            self._tailor_experience_bullets(tailored, jd_skill_set, changes)

            return {
                "success": True,
                "resume_data": tailored,
                "changes_summary": "\n".join(changes[:4]) if changes else "Adjusted emphasis to better align with job requirements.",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def tailor_resume_text(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        try:
            jd_skills = extract_skills(job_description, similarity_threshold=0.35)[:12]
            lines = [ln.rstrip() for ln in (resume_text or "").splitlines()]
            text = "\n".join(lines).strip()
            if not text:
                return {"success": False, "error": "Resume text is empty."}

            if jd_skills:
                headline = "Targeted Focus: " + ", ".join(jd_skills[:6])
                if headline.lower() not in text.lower():
                    text = headline + "\n\n" + text

            return {"success": True, "tailored_text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tailor_summary(self, resume_data: Dict[str, Any], jd_skills: List[str], changes: List[str]) -> None:
        summary_keys = ["summary", "professionalSummary", "professional_summary", "objective"]
        summary_key = next((k for k in summary_keys if isinstance(resume_data.get(k), str)), None)
        if not summary_key:
            return

        summary = resume_data.get(summary_key, "").strip()
        if not summary:
            return

        emphasized = [s for s in jd_skills if self._norm(s) in self._norm(summary)]
        missing = [s for s in jd_skills if self._norm(s) not in self._norm(summary)]
        add = missing[:3]
        if add:
            addition = " Key strengths aligned to this role include " + ", ".join(add) + "."
            if addition.lower() not in summary.lower():
                resume_data[summary_key] = (summary + addition).strip()
                changes.append("- Updated summary to emphasize role-relevant skills.")
        elif emphasized:
            changes.append("- Summary already aligns with core job skills.")

    def _tailor_skills(self, resume_data: Dict[str, Any], jd_skill_set: set, changes: List[str]) -> None:
        skills = resume_data.get("skills")
        if not skills:
            return

        if isinstance(skills, str):
            skill_items = [s.strip() for s in re.split(r",|\n|\|", skills) if s.strip()]
            as_string = True
        elif isinstance(skills, list):
            skill_items = [str(s).strip() for s in skills if str(s).strip()]
            as_string = False
        else:
            return

        prioritized = sorted(
            skill_items,
            key=lambda s: (self._norm(s) not in jd_skill_set, s.lower()),
        )
        if prioritized != skill_items:
            resume_data["skills"] = ", ".join(prioritized) if as_string else prioritized
            changes.append("- Reordered skills to prioritize job-matching technologies.")

    def _tailor_experience_bullets(self, resume_data: Dict[str, Any], jd_skill_set: set, changes: List[str]) -> None:
        experience = resume_data.get("experience")
        if not isinstance(experience, list):
            return

        changed_any = False
        for item in experience:
            if not isinstance(item, dict):
                continue
            for key in ("description", "responsibilities", "highlights", "bullets"):
                value = item.get(key)
                if isinstance(value, list):
                    new_list = self._prioritize_lines(value, jd_skill_set)
                    if new_list != value:
                        item[key] = new_list
                        changed_any = True
                elif isinstance(value, str):
                    lines = [ln.strip("- ").strip() for ln in value.split("\n") if ln.strip()]
                    new_lines = self._prioritize_lines(lines, jd_skill_set)
                    if new_lines and new_lines != lines:
                        item[key] = "\n".join(f"- {ln}" for ln in new_lines)
                        changed_any = True

        if changed_any:
            changes.append("- Reordered experience bullets to surface job-relevant impact first.")

    def _prioritize_lines(self, lines: List[str], jd_skill_set: set) -> List[str]:
        scored = []
        for ln in lines:
            n = self._norm(ln)
            overlap = sum(1 for sk in jd_skill_set if sk and sk in n)
            scored.append((overlap, len(ln), ln))
        scored.sort(key=lambda t: (-t[0], t[1]))
        return [ln for _, _, ln in scored]

    def _norm(self, s: str) -> str:
        x = (s or "").lower()
        x = re.sub(r"[^\w\s+#./-]", " ", x)
        return re.sub(r"\s+", " ", x).strip()

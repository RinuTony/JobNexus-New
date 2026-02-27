import re
from typing import Any, Dict, List


class ReasoningHelper:
    """
    Local deterministic reasoning helper.
    Produces stable JSON reasoning without external LLM APIs.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key  # kept for backward compatibility

    def generate_match_reasoning(
        self,
        resume_text: str,
        job_description: str,
        similarity_score: float,
        detected_skills: List[str],
    ) -> Dict[str, Any]:
        try:
            resume_tokens = self._tokenize(resume_text)
            jd_tokens = self._tokenize(job_description)
            overlap = sorted(list(resume_tokens & jd_tokens))

            top_overlap = overlap[:8]
            jd_skill_like = self._skill_like_terms(jd_tokens)
            resume_skill_like = self._skill_like_terms(resume_tokens)
            missing = [t for t in jd_skill_like if t not in resume_skill_like][:8]

            strengths = self._build_strengths(detected_skills, top_overlap)
            gaps = self._build_gaps(missing, similarity_score)
            suggestions = self._build_suggestions(missing, similarity_score)

            reasoning = {
                "score_explanation": self._score_explanation(
                    similarity_score=similarity_score,
                    overlap_count=len(overlap),
                    detected_count=len(detected_skills or []),
                ),
                "strengths": strengths,
                "gaps": gaps,
                "suggestions": suggestions,
                "overall_assessment": self._overall_assessment(similarity_score, missing),
                "score_interpretation": self._interpret_score(similarity_score),
                "score": similarity_score,
                "source": "Local Analysis",
            }
            return {"success": True, "reasoning": reasoning}
        except Exception as e:
            return {"success": False, "error": str(e), "reasoning": {}}

    def _tokenize(self, text: str) -> set:
        parts = re.findall(r"[a-zA-Z][a-zA-Z0-9+#./-]{1,}", (text or "").lower())
        stop = {
            "with", "from", "that", "this", "have", "your", "role", "team", "work",
            "years", "year", "experience", "ability", "knowledge", "using", "and",
            "for", "the", "are", "you", "our", "will", "must", "required", "preferred",
        }
        return {p for p in parts if p not in stop and len(p) > 2}

    def _skill_like_terms(self, tokens: set) -> List[str]:
        anchors = {
            "python", "java", "javascript", "typescript", "react", "node", "sql", "mysql",
            "postgresql", "docker", "kubernetes", "aws", "gcp", "azure", "git", "rest",
            "api", "pandas", "numpy", "tensorflow", "pytorch", "tableau", "power", "bi",
            "linux", "flask", "fastapi", "django", "ml", "ai", "etl",
        }
        matched = [t for t in sorted(tokens) if t in anchors]
        if matched:
            return matched
        return [t for t in sorted(tokens) if any(ch.isdigit() for ch in t) or "+" in t or "#" in t][:20]

    def _build_strengths(self, detected_skills: List[str], overlap_terms: List[str]) -> List[str]:
        strengths = []
        if detected_skills:
            strengths.append(f"Detected {len(detected_skills)} relevant skills from the resume.")
        if overlap_terms:
            strengths.append("Strong keyword overlap on: " + ", ".join(overlap_terms[:5]) + ".")
        strengths.append("Resume includes role-relevant technical terminology.")
        return strengths[:3]

    def _build_gaps(self, missing_terms: List[str], similarity_score: float) -> List[str]:
        gaps = []
        if missing_terms:
            gaps.append("Missing or weakly represented requirements: " + ", ".join(missing_terms[:5]) + ".")
        if similarity_score < 0.7:
            gaps.append("Experience alignment appears partial for core job requirements.")
        gaps.append("Some skills may be present but not explicitly highlighted in resume bullets.")
        return gaps[:3]

    def _build_suggestions(self, missing_terms: List[str], similarity_score: float) -> List[str]:
        suggestions = []
        if missing_terms:
            suggestions.append("Prioritize upskilling in: " + ", ".join(missing_terms[:4]) + ".")
            suggestions.append("Add quantified project bullets that demonstrate these skills.")
        else:
            suggestions.append("Emphasize high-impact achievements relevant to the job stack.")
        if similarity_score < 0.8:
            suggestions.append("Tailor summary and skills section to mirror job language.")
        return suggestions[:3]

    def _score_explanation(self, similarity_score: float, overlap_count: int, detected_count: int) -> str:
        band = self._interpret_score(similarity_score)
        return (
            f"Score {similarity_score:.2f} indicates {band.lower()}. "
            f"Local analysis found {detected_count} detected skills and {overlap_count} overlapping terms "
            f"between resume and job description."
        )

    def _overall_assessment(self, similarity_score: float, missing_terms: List[str]) -> str:
        if similarity_score >= 0.8:
            return "Profile aligns strongly with the role; focus on clearer impact statements."
        if similarity_score >= 0.6:
            return "Profile is moderately aligned; targeted skill and wording improvements can raise fit."
        if missing_terms:
            return "Profile has clear gaps for this role and needs focused upskilling before applying."
        return "Profile needs better evidence alignment to this specific job description."

    def _interpret_score(self, score: float) -> str:
        if score >= 0.8:
            return "Excellent Match - Highly qualified candidate"
        if score >= 0.7:
            return "Strong Match - Well-qualified candidate"
        if score >= 0.6:
            return "Good Match - Qualified with some gaps"
        if score >= 0.5:
            return "Moderate Match - Some relevant experience"
        if score >= 0.3:
            return "Weak Match - Limited relevant experience"
        return "Poor Match - Significant experience gaps"

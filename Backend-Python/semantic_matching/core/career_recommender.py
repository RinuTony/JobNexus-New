import os
import pickle
import re
import csv
from typing import Dict, List, Any, Optional

import numpy as np
import spacy


class CareerRecommender:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(__file__))
        self.model_path = os.path.join(self.base_dir, "models", "career_recommendation", "model.pkl")
        self.vectorizer_path = os.path.join(self.base_dir, "models", "career_recommendation", "vectorizer.pkl")
        self.data_path = os.path.join(self.base_dir, "models", "career_recommendation", "career_data.csv")

        self.nlp = spacy.load("en_core_web_sm")
        self.model = self._load_pickle(self.model_path)
        self.vectorizer = self._load_pickle(self.vectorizer_path)
        self._apply_model_compatibility_fixes()

        self.role_skills = self._load_role_skills_from_csv()
        self.all_skills = sorted({skill for skills in self.role_skills.values() for skill in skills})

    @staticmethod
    def _load_pickle(path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing file: {path}")
        with open(path, "rb") as f:
            return pickle.load(f)

    def _apply_model_compatibility_fixes(self) -> None:
        """
        Some pickled sklearn LogisticRegression models created in different
        sklearn versions can miss attributes expected at inference time.
        """
        model_name = self.model.__class__.__name__.lower()
        if model_name == "logisticregression":
            if not hasattr(self.model, "multi_class"):
                self.model.multi_class = "auto"

    @staticmethod
    def _tokenize_skill_text(skills_text: str) -> List[str]:
        normalized = (skills_text or "").lower().strip()
        if not normalized:
            return []
        normalized = re.sub(r"[,\n;|]+", " ", normalized)
        tokens = re.findall(r"[a-z0-9+#./-]+", normalized)
        cleaned = []
        seen = set()
        for token in tokens:
            token = token.strip("-.")
            if not token:
                continue
            if token in seen:
                continue
            seen.add(token)
            cleaned.append(token)
        return cleaned

    def _load_role_skills_from_csv(self) -> Dict[str, List[str]]:
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Missing file: {self.data_path}")

        role_skills: Dict[str, List[str]] = {}
        with open(self.data_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                role = (row.get("job_title") or "").strip()
                raw_skills = row.get("required_skills") or ""
                if not role:
                    continue
                parsed_skills = self._tokenize_skill_text(raw_skills)
                if parsed_skills:
                    role_skills[role] = parsed_skills

        if not role_skills:
            raise ValueError("No role/skill data found in career_data.csv")
        return role_skills

    @staticmethod
    def _normalize_for_skill_matching(text: str) -> str:
        normalized = (text or "").lower()
        normalized = re.sub(r"[^a-z0-9+#./\s-]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return f" {normalized} "

    def preprocess_text(self, text: str) -> str:
        normalized = (text or "").lower()
        normalized = re.sub(r"[^a-zA-Z\s]", " ", normalized)
        doc = self.nlp(normalized)
        tokens = [token.lemma_ for token in doc if not token.is_stop]
        return " ".join(tokens)

    def extract_skills(self, text: str) -> List[str]:
        processed = self._normalize_for_skill_matching(text)
        extracted = []
        for skill in self.all_skills:
            normalized_skill = self._normalize_for_skill_matching(skill).strip()
            if not normalized_skill:
                continue
            if f" {normalized_skill} " in processed:
                extracted.append(skill)
        return extracted

    def recommend_from_resume_text(self, resume_text: str) -> Dict[str, Any]:
        if not resume_text or not resume_text.strip():
            raise ValueError("Resume text is empty")

        cleaned_text = self.preprocess_text(resume_text)
        resume_skills = self.extract_skills(resume_text)

        vector = self.vectorizer.transform([cleaned_text])
        prediction = self.model.predict(vector)[0]

        probabilities = self.model.predict_proba(vector)[0]
        top_indices = np.argsort(probabilities)[-3:][::-1]

        top_matches = [
            {
                "career": str(self.model.classes_[index]),
                "score_percentage": round(float(probabilities[index]) * 100, 2)
            }
            for index in top_indices
        ]

        required = self.role_skills.get(str(prediction), [])
        missing = [skill for skill in required if skill not in resume_skills]

        return {
            "recommended_career": str(prediction),
            "top_matches": top_matches,
            "resume_skills": sorted(set(resume_skills)),
            "missing_skills": missing,
        }

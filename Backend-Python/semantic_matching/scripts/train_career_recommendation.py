import os
import pickle
import re
import csv
from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


def normalize_skill_text(text: str) -> str:
    value = (text or "").lower().strip()
    value = re.sub(r"\s+", " ", value)
    return value


def load_training_data(csv_path: str) -> tuple[List[str], List[str]]:
    X: List[str] = []
    y: List[str] = []

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            job_title = (row.get("job_title") or "").strip()
            required_skills = normalize_skill_text(row.get("required_skills") or "")
            if not job_title or not required_skills:
                continue
            X.append(required_skills)
            y.append(job_title)

    if not X or not y:
        raise ValueError("No usable rows found in career_data.csv")
    return X, y


def main() -> None:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    model_dir = os.path.join(base_dir, "models", "career_recommendation")
    csv_path = os.path.join(model_dir, "career_data.csv")
    model_path = os.path.join(model_dir, "model.pkl")
    vectorizer_path = os.path.join(model_dir, "vectorizer.pkl")

    X_text, y = load_training_data(csv_path)

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    X = vectorizer.fit_transform(X_text)

    model = LogisticRegression(max_iter=3000, solver="lbfgs", multi_class="multinomial")
    model.fit(X, y)

    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    with open(vectorizer_path, "wb") as f:
        pickle.dump(vectorizer, f)

    print(f"Trained classes: {len(model.classes_)}")
    print("Saved:", model_path)
    print("Saved:", vectorizer_path)


if __name__ == "__main__":
    main()

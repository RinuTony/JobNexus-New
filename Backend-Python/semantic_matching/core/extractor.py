# core/extractor.py
import pdfplumber
import re
import spacy
from typing import Tuple, List, Dict, Set
import os
import nltk
from sentence_transformers import SentenceTransformer, util

# Ensure NLTK resources
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

from nltk.tokenize import sent_tokenize

# Load models once
nlp = spacy.load("en_core_web_sm")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# Regex patterns
EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"(?<!19)(?<!20)\+?\d[\d\s\-]{7,15}\d")
LINKEDIN_RE = re.compile(r"(https?://(www\.)?linkedin\.com/[A-Za-z0-9_\-/]+|www\.linkedin\.com/[A-Za-z0-9_\-/]+)")
GITHUB_RE = re.compile(r"(https?://(www\.)?github\.com/[A-Za-z0-9_\-./]+)")

# Filtering to reduce false-positive "skills" from generic role/context phrases.
LEADING_NON_SKILL_TOKENS = {
    "this", "that", "these", "those", "our", "your", "their", "the", "a", "an"
}

GENERIC_ROLE_TOKENS = {
    "intern", "internship", "engineer", "engineers", "developer", "developers",
    "team", "candidate", "candidates", "company", "organization", "role", "position",
    "project", "projects", "experience", "experiences", "department", "manager",
    "managers", "employee", "employees", "job", "jobs", "work", "working"
}

GENERIC_NON_SKILL_PHRASES = {
    "this internship", "our engineering team", "experienced engineers", "live projects",
    "engineering team", "software team", "the team", "job role"
}

TECH_HINT_TOKENS = {
    "python", "java", "javascript", "typescript", "react", "node", "nodejs", "sql", "mysql",
    "postgres", "postgresql", "mongodb", "docker", "kubernetes", "aws", "azure", "gcp",
    "linux", "git", "github", "rest", "api", "fastapi", "flask", "django", "spring",
    "tensorflow", "pytorch", "numpy", "pandas", "tableau", "power", "bi", "excel",
    "devops", "ci", "cd", "jenkins", "agile", "scrum", "html", "css", "sass", "webpack",
    "c", "c++", "c#", "go", "rust", "php", "laravel", "express", "redis"
}

NON_TECH_META_PHRASES = {
    "software development", "software engineering", "engineering", "student",
    "final year student", "undergraduate student", "experienced engineers",
    "this internship", "internship", "intern", "our engineering team"
}

TECH_MULTIWORD_TERMS = {
    "machine learning", "deep learning", "natural language processing", "computer vision",
    "data science", "data analysis", "data engineering", "data structures", "algorithms",
    "object oriented programming", "test driven development", "continuous integration",
    "continuous deployment", "rest api", "microservices", "distributed systems",
    "system design", "cloud computing", "aws lambda", "amazon web services",
    "google cloud platform", "azure devops", "neural networks", "prompt engineering",
    "power bi", "tableau", "docker compose", "kubernetes", "react js", "node js",
    "next js", "express js", "spring boot", "entity framework", "computer networks",
    "operating systems", "database design", "sql queries", "unit testing", "integration testing"
}

# Text extraction
def extract_text(path: str) -> Tuple[str, str]:
    """Extract text from PDF or TXT files"""
    ext = os.path.splitext(path)[1].lower()
    
    if ext == ".pdf":
        text = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
        return "\n".join(text), "pdf"
    
    elif ext == ".txt":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(), "txt"
    
    else:
        raise ValueError(f"Unsupported file type: {ext}")

# Skill extraction
def extract_skills(text: str, similarity_threshold: float = 0.35) -> List[str]:
    """Extract skill-like phrases from text using linguistic + embedding signals."""
    cleaned_text = re.sub(r"\s+", " ", text.lower()).strip()
    if not cleaned_text:
        return []

    doc = nlp(cleaned_text)

    def normalize_phrase(phrase: str) -> str:
        p = phrase.lower().strip()
        p = re.sub(r"[^\w\s+#./-]", " ", p)
        p = re.sub(r"\s+", " ", p).strip()
        return p

    def valid_phrase(phrase: str) -> bool:
        if not phrase:
            return False
        phrase = normalize_phrase(phrase)
        tokens = phrase.split()
        if len(tokens) == 0 or len(tokens) > 5:
            return False
        if phrase.isdigit():
            return False
        alpha_count = sum(1 for ch in phrase if ch.isalpha())
        if alpha_count < 2:
            return False
        if phrase in GENERIC_NON_SKILL_PHRASES:
            return False
        if tokens[0] in LEADING_NON_SKILL_TOKENS:
            return False
        if len(tokens) == 1 and tokens[0] in GENERIC_ROLE_TOKENS:
            return False
        if all(t in GENERIC_ROLE_TOKENS for t in tokens):
            return False
        # Reject generic context phrases unless they contain explicit tech hints.
        if any(t in GENERIC_ROLE_TOKENS for t in tokens) and not any(
            t in TECH_HINT_TOKENS for t in tokens
        ):
            return False
        if phrase in NON_TECH_META_PHRASES:
            return False
        # Keep only technical-looking phrases.
        has_tech_hint = any(t in TECH_HINT_TOKENS for t in tokens)
        has_symbolic_tech_hint = any(sym in phrase for sym in ["c++", "c#", ".net"])
        is_known_multiword = phrase in TECH_MULTIWORD_TERMS
        if not (has_tech_hint or has_symbolic_tech_hint or is_known_multiword):
            return False
        return True

    candidate_phrases: Set[str] = set()

    # 0) Dictionary-first technical phrase detection (highest precision).
    padded = f" {cleaned_text} "
    for skill in TECH_MULTIWORD_TERMS:
        if f" {skill} " in padded and valid_phrase(skill):
            candidate_phrases.add(skill)
    for token in TECH_HINT_TOKENS:
        if len(token) <= 2 and token not in {"c#", "c++"}:
            continue
        if f" {token} " in padded and valid_phrase(token):
            candidate_phrases.add(token)

    # 1) Noun chunks capture multi-word skill phrases.
    for chunk in doc.noun_chunks:
        phrase = normalize_phrase(chunk.text)
        if valid_phrase(phrase):
            candidate_phrases.add(phrase)

    # 2) Named entities add tool/technology names often missed by chunks.
    for ent in doc.ents:
        phrase = normalize_phrase(ent.text)
        if valid_phrase(phrase):
            candidate_phrases.add(phrase)

    # 3) Token fallback captures standalone skills in bullet lists (e.g., "python", "sql").
    for token in doc:
        if token.is_stop or token.is_punct or token.like_num:
            continue
        if token.pos_ not in {"NOUN", "PROPN", "ADJ"}:
            continue
        phrase = normalize_phrase(token.text)
        if valid_phrase(phrase):
            candidate_phrases.add(phrase)

    if not candidate_phrases:
        return []

    phrases = list(candidate_phrases)
    text_embedding = embed_model.encode(cleaned_text, convert_to_tensor=True)
    phrase_embeddings = embed_model.encode(phrases, convert_to_tensor=True)
    sims = util.cos_sim(phrase_embeddings, text_embedding).squeeze(-1)

    # Add a small frequency prior so repeated skills survive thresholding.
    skills_with_scores = []
    for idx, phrase in enumerate(phrases):
        semantic_score = float(sims[idx].item())
        frequency = cleaned_text.count(phrase)
        freq_boost = min(frequency, 5) * 0.02
        final_score = semantic_score + freq_boost
        if final_score >= similarity_threshold:
            skills_with_scores.append((phrase, final_score))

    # Return unique phrases sorted by confidence.
    skills_with_scores.sort(key=lambda x: x[1], reverse=True)
    results = [phrase for phrase, _ in skills_with_scores]

    # Final cleanup of known non-technical meta terms and near-duplicates.
    filtered = []
    seen = set()
    for s in results:
        n = normalize_phrase(s)
        if not n or n in NON_TECH_META_PHRASES:
            continue
        if n in seen:
            continue
        seen.add(n)
        filtered.append(n)
    return filtered

# Contact info extraction
def extract_contact_info(text: str) -> Dict[str, List[str]]:
    """Extract contact information from resume text"""
    # Extract emails
    emails = EMAIL_RE.findall(text)
    
    # Extract phones
    phones = [re.sub(r"[^\d+]", "", p) for p in PHONE_RE.findall(text)]
    
    # Extract URLs
    linkedin = [m[0] for m in LINKEDIN_RE.findall(text)]
    github = [m[0] for m in GITHUB_RE.findall(text)]
    
    # Extract name (simple approach - first line)
    first_line = text.strip().split("\n")[0].strip()
    names = [first_line] if 2 <= len(first_line.split()) <= 5 else []
    
    # Deduplicate
    def uniq(lst):
        return list(dict.fromkeys(lst))
    
    return {
        "names": uniq(names)[:3],
        "emails": uniq(emails)[:3],
        "phones": uniq(phones)[:3],
        "linkedin": uniq(linkedin)[:2],
        "github": uniq(github)[:2]
    }

# Sentence segmentation
def segment_to_sentences(text: str) -> List[str]:
    """Split text into clean sentences"""
    text = re.sub(r"\r\n", "\n", text)
    sentences = []
    
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        
        for sentence in sent_tokenize(paragraph):
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:
                sentences.append(sentence)
    
    return sentences

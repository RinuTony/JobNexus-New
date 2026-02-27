# core/skill_gap_analyzer.py
import numpy as np
import re
from typing import List, Dict, Tuple, Optional, Any
from core.matcher import ResumeMatcher
from core.extractor import segment_to_sentences, extract_skills

class SkillGapAnalyzer:
    def __init__(self):
        # Keep the skill-gap pipeline aligned with match-score embeddings.
        self.matcher = ResumeMatcher("all-MiniLM-L6-v2")
        self.embedder = self.matcher.embedder
        self.skill_extract_threshold = 0.35
        self.skill_match_threshold = 0.70
        self.max_skill_words = 5
        self.max_skill_count = 80

        # Priority keywords for classification
        self.required_keywords = [
            'must have', 'required', 'mandatory', 'essential',
            'necessary', 'need to have', 'critical'
        ]
        
        self.preferred_keywords = [
            'preferred', 'desired', 'nice to have', 'would be great',
            'advantage', 'plus', 'beneficial', 'ideal'
        ]

    def extract_semantic_skills(
        self,
        text: str,
        threshold: float = 0.5,
        return_metadata: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Extract skills from text using dynamic noun-phrase extraction.
        
        Args:
            text: Resume or job description text
            threshold: Minimum similarity score to consider a match
        
        Returns:
            List of matched skills with scores and categories
        """
        extracted = extract_skills(text, similarity_threshold=self.skill_extract_threshold)
        candidate_skills = list(dict.fromkeys(extracted))
        if not candidate_skills:
            if return_metadata:
                return [], {
                    "extractor": "local",
                    "final_count": 0,
                }
            return []

        detected_skills = []
        seen = set()
        for phrase in candidate_skills:
            if not self._is_valid_skill_phrase(phrase):
                continue
            normalized = self._normalize_skill(phrase)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            detected_skills.append({
                'skill': normalized,
                'original_phrase': phrase,
                'similarity_score': 1.0,
                'category': 'general'
            })

        if return_metadata:
            return detected_skills, {
                "extractor": "local",
                "final_count": len(detected_skills),
            }
        return detected_skills

    def _normalize_skill(self, phrase: str) -> str:
        text = phrase.lower().strip()
        # Generic cleanup only (no skill-specific mapping)
        text = re.sub(r"[^\w\s+#./-]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _is_valid_skill_phrase(self, phrase: str) -> bool:
        if not phrase:
            return False
        normalized = self._normalize_skill(phrase)
        if not normalized:
            return False
        words = normalized.split()
        if len(words) == 0 or len(words) > self.max_skill_words:
            return False
        if normalized.isdigit():
            return False
        # Skip mostly numeric/token-like phrases that are not skills.
        alpha_chars = sum(1 for ch in normalized if ch.isalpha())
        if alpha_chars < 2:
            return False
        return True

    def _lexical_similarity(self, skill_a: str, skill_b: str) -> float:
        a = self._normalize_skill(skill_a)
        b = self._normalize_skill(skill_b)
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0
        # Handles cases like "python" vs "python development"
        if a in b or b in a:
            return 0.9

        a_tokens = set(a.split())
        b_tokens = set(b.split())
        if not a_tokens or not b_tokens:
            return 0.0
        inter = len(a_tokens & b_tokens)
        if inter == 0:
            return 0.0
        union = len(a_tokens | b_tokens)
        return inter / union

    def _raw_text_contains_skill(self, resume_text: str, skill: str) -> bool:
        """
        Robust text-presence check used before semantic matching.
        Helps when PDF extraction glues words (e.g., 'pythonwas').
        """
        s = self._normalize_skill(skill)
        if not s:
            return False

        resume_lower = (resume_text or "").lower()
        # Normalize punctuation/noise to spaces for phrase checks.
        resume_spaced = re.sub(r"[^a-z0-9+#./-]+", " ", resume_lower)
        resume_spaced = re.sub(r"\s+", " ", resume_spaced).strip()

        # Exact phrase in normalized text.
        if s in resume_spaced:
            return True

        # Token-wise fallback for multi-word skills.
        parts = [p for p in s.split() if p]
        if len(parts) > 1 and all(p in resume_spaced for p in parts):
            return True

        # Compact fallback for glued words in extracted text.
        compact_resume = re.sub(r"[^a-z0-9+#]+", "", resume_lower)
        compact_skill = re.sub(r"[^a-z0-9+#]+", "", s)
        if not compact_skill:
            return False
        if len(compact_skill) <= 2:
            return False
        if compact_skill in compact_resume:
            return True
        return False
    
    def classify_skill_priority(self, skill: str, jd_text: str) -> Tuple[str, float]:
        """
        Classify skill priority using semantic context analysis
        
        Args:
            skill: The skill to classify
            jd_text: Job description text
        
        Returns:
            Tuple of (priority, confidence_score)
        """
        jd_lower = jd_text.lower()
        sentences = segment_to_sentences(jd_text)
        
        # Find sentences mentioning this skill
        skill_lower = skill.lower()
        relevant_sentences = []
        
        for sentence in sentences:
            # Use semantic similarity to find relevant sentences
            sentence_lower = sentence.lower()
            
            # Direct mention check
            if any(word in sentence_lower for word in skill_lower.split()):
                relevant_sentences.append(sentence_lower)
            else:
                # Semantic check
                skill_emb = self.embedder.encode(skill)
                sent_emb = self.embedder.encode(sentence)
                similarity = float(np.dot(skill_emb, sent_emb))
                
                if similarity > 0.4:  # Threshold for relevance
                    relevant_sentences.append(sentence_lower)
        
        if not relevant_sentences:
            return "nice-to-have", 0.5
        
        # Analyze context with embeddings
        context_text = " ".join(relevant_sentences)
        
        # Check for required indicators
        required_score = 0.0
        for keyword in self.required_keywords:
            if keyword in context_text:
                required_score += 1.0
            else:
                # Semantic check
                keyword_emb = self.embedder.encode(keyword)
                context_emb = self.embedder.encode(context_text)
                sim = float(np.dot(keyword_emb, context_emb))
                required_score += sim * 0.5
        
        # Check for preferred indicators
        preferred_score = 0.0
        for keyword in self.preferred_keywords:
            if keyword in context_text:
                preferred_score += 1.0
            else:
                keyword_emb = self.embedder.encode(keyword)
                context_emb = self.embedder.encode(context_text)
                sim = float(np.dot(keyword_emb, context_emb))
                preferred_score += sim * 0.5
        
        # Classify based on scores
        if required_score > preferred_score and required_score > 1.0:
            priority = "required"
            confidence = min(required_score / len(self.required_keywords), 1.0)
        elif preferred_score > 0.5:
            priority = "preferred"
            confidence = min(preferred_score / len(self.preferred_keywords), 1.0)
        else:
            priority = "nice-to-have"
            confidence = 0.5
        
        return priority, float(confidence)
    
    def analyze_skill_gap(
        self, 
        resume_text: str, 
        jd_text: str,
        required_skills: Optional[List[str]] = None,
        resume_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete skill gap analysis using semantic matching
        
        Args:
            resume_text: Resume content
            jd_text: Job description content
            resume_path: Optional path to resume file
        
        Returns:
            Comprehensive analysis with matched/missing skills
        """
        # Extract skills from resume and derive target skills from recruiter-provided list when available.
        resume_skills_data, resume_extract_meta = self.extract_semantic_skills(
            resume_text, threshold=0.5, return_metadata=True
        )
        if required_skills:
            normalized_required = []
            seen_required = set()
            for rs in required_skills:
                n = self._normalize_skill(str(rs or ""))
                if not n or n in seen_required or not self._is_valid_skill_phrase(n):
                    continue
                seen_required.add(n)
                normalized_required.append(n)

            jd_skills_data = [
                {
                    "skill": s,
                    "original_phrase": s,
                    "similarity_score": 1.0,
                    "category": "general",
                }
                for s in normalized_required
            ]
            jd_extract_meta = {
                "extractor": "recruiter_required_skills",
                "final_count": len(jd_skills_data),
            }
        else:
            jd_skills_data, jd_extract_meta = self.extract_semantic_skills(
                jd_text, threshold=0.5, return_metadata=True
            )
        
        # Get skill names only
        resume_skills = {s['skill'] for s in resume_skills_data}
        jd_skills = {s['skill'] for s in jd_skills_data}
        
        # Find semantic matches (not just exact matches)
        matched_skills = []
        missing_skills = []
        
        resume_skill_list = [s['skill'] for s in resume_skills_data]
        jd_skill_list = [s['skill'] for s in jd_skills_data]

        resume_embeddings = self.embedder.encode_batch(resume_skill_list) if resume_skill_list else []
        jd_embeddings = self.embedder.encode_batch(jd_skill_list) if jd_skill_list else []

        for idx, jd_skill_data in enumerate(jd_skills_data):
            jd_skill = jd_skill_data['skill']

            if jd_skill in resume_skills:
                matched_skills.append(jd_skill_data)
                continue

            # Strong safeguard: if required skill is explicitly present in raw resume text,
            # treat it as matched even when extractor tokenization is imperfect.
            if self._raw_text_contains_skill(resume_text, jd_skill):
                matched_skills.append({
                    **jd_skill_data,
                    'matched_with': jd_skill,
                    'match_type': 'text_presence',
                    'match_score': 1.0
                })
                continue

            best_match_score = 0.0
            best_match_skill = None
            best_lexical_score = 0.0
            best_lexical_skill = None

            for resume_skill in resume_skill_list:
                lex_score = self._lexical_similarity(jd_skill, resume_skill)
                if lex_score > best_lexical_score:
                    best_lexical_score = lex_score
                    best_lexical_skill = resume_skill

            if best_lexical_score >= 0.8:
                matched_skills.append({
                    **jd_skill_data,
                    'matched_with': best_lexical_skill,
                    'match_type': 'lexical',
                    'match_score': best_lexical_score
                })
                continue

            if len(resume_skill_list) > 0 and len(jd_skill_list) > 0:
                jd_vec = jd_embeddings[idx]
                for r_idx, resume_skill in enumerate(resume_skill_list):
                    resume_vec = resume_embeddings[r_idx]
                    similarity = float(np.dot(jd_vec, resume_vec))
                    if similarity > best_match_score:
                        best_match_score = similarity
                        best_match_skill = resume_skill

            if best_match_score >= self.skill_match_threshold:
                matched_skills.append({
                    **jd_skill_data,
                    'matched_with': best_match_skill,
                    'match_type': 'semantic',
                    'match_score': best_match_score
                })
            else:
                priority, confidence = self.classify_skill_priority(jd_skill, jd_text)
                missing_skills.append({
                    **jd_skill_data,
                    'priority': priority,
                    'priority_confidence': confidence
                })
        
        # Categorize missing skills
        categorized_missing = {'general': missing_skills}
        categorized_matched = {'general': matched_skills}
        
        # Calculate overall match percentage
        total_jd_skills = len(jd_skills)
        total_matched = len(matched_skills)
        
        if total_jd_skills > 0:
            match_percentage = round((total_matched / total_jd_skills) * 100, 1)
        else:
            match_percentage = 0.0
        
        # Generate recommendation using semantic analysis
        recommendation = self._generate_recommendation(
            match_percentage, 
            missing_skills,
            matched_skills
        )
        
        return {
            'match_percentage': match_percentage,
            'total_required_skills': total_jd_skills,
            'total_matched_skills': total_matched,
            'total_missing_skills': len(missing_skills),
            'matched_skills': matched_skills,
            'missing_skills': missing_skills,
            'categorized_matched': categorized_matched,
            'categorized_missing': categorized_missing,
            'recommendation': recommendation,
            'ai_analysis_enabled': False,
            'ai_analysis_used': False,
            'extraction_details': {
                'resume': resume_extract_meta,
                'jd': jd_extract_meta,
            }
        }
    
    def _generate_recommendation(
        self, 
        match_percentage: float,
        missing_skills: List[Dict],
        matched_skills: List[Dict]
    ) -> str:
        """Generate personalized recommendation based on analysis"""
        
        # Count skills by priority
        required_missing = sum(1 for s in missing_skills if s.get('priority') == 'required')
        preferred_missing = sum(1 for s in missing_skills if s.get('priority') == 'preferred')
        
        if match_percentage >= 80:
            return (
                f"Excellent match! You have {match_percentage}% of the required skills. "
                f"Focus on the remaining {len(missing_skills)} skills to become an ideal candidate."
            )
        elif match_percentage >= 60:
            if required_missing > 0:
                return (
                    f"Good match at {match_percentage}%. However, you're missing {required_missing} "
                    f"critical skill(s). Prioritize learning these required skills first."
                )
            else:
                return (
                    f"Good match at {match_percentage}%. Focus on the {preferred_missing} "
                    f"preferred skills to strengthen your application."
                )
        elif match_percentage >= 40:
            return (
                f"Moderate match at {match_percentage}%. You have a foundation but need to develop "
                f"{required_missing} required and {preferred_missing} preferred skills. "
                f"Consider a structured learning plan."
            )
        else:
            return (
                f"Low match at {match_percentage}%. This role requires significant upskilling. "
                f"Focus on {required_missing} critical skills first. Consider similar roles that "
                f"better match your current skill set."
            )
    
    def get_learning_path(self, missing_skills: List[Dict]) -> Dict[str, Any]:
        """
        Generate structured learning path based on skill priorities and dependencies
        
        Args:
            missing_skills: List of missing skill data with priorities
        
        Returns:
            Structured learning path with phases and time estimates
        """
        # Sort by priority
        required_skills = [s for s in missing_skills if s.get('priority') == 'required']
        preferred_skills = [s for s in missing_skills if s.get('priority') == 'preferred']
        nice_to_have = [s for s in missing_skills if s.get('priority') == 'nice-to-have']
        
        # Estimate learning time (in weeks)
        time_estimates = {
            'general': 4
        }
        
        def estimate_time(skill_data):
            category = skill_data.get('category', 'tools')
            base_time = time_estimates.get(category, 4)
            priority = skill_data.get('priority', 'nice-to-have')
            
            # Adjust based on priority
            if priority == 'required':
                return f"{base_time}-{base_time+2} weeks (High Priority)"
            elif priority == 'preferred':
                return f"{base_time}-{base_time+2} weeks (Medium Priority)"
            else:
                return f"{base_time//2}-{base_time} weeks (Low Priority)"
        
        # Identify quick wins (easier skills)
        quick_win_categories = ['general']
        quick_wins = [
            s['skill'] for s in missing_skills 
            if s.get('category') in quick_win_categories
        ][:3]
        
        # Calculate total estimated time
        total_weeks = sum(
            time_estimates.get(s.get('category', 'tools'), 4) 
            for s in required_skills
        )
        
        return {
            'phases': [
                {
                    'phase': 'Phase 1 - Critical Skills (Required)',
                    'skills': [
                        {
                            'name': s['skill'],
                            'category': s['category'],
                            'estimated_time': estimate_time(s),
                            'original_phrase': s.get('original_phrase', s['skill'])
                        }
                        for s in required_skills
                    ]
                },
                {
                    'phase': 'Phase 2 - Preferred Skills',
                    'skills': [
                        {
                            'name': s['skill'],
                            'category': s['category'],
                            'estimated_time': estimate_time(s),
                            'original_phrase': s.get('original_phrase', s['skill'])
                        }
                        for s in preferred_skills
                    ]
                },
                {
                    'phase': 'Phase 3 - Additional Skills',
                    'skills': [
                        {
                            'name': s['skill'],
                            'category': s['category'],
                            'estimated_time': estimate_time(s),
                            'original_phrase': s.get('original_phrase', s['skill'])
                        }
                        for s in nice_to_have
                    ]
                }
            ],
            'quick_wins': quick_wins,
            'estimated_total_time': f"{total_weeks}-{total_weeks + 8} weeks",
            'total_skills': len(missing_skills)
        }

# core/interview_helper.py
import requests
import tempfile
import os
from typing import List, Dict, Any, Optional
from core.database_helper import DatabaseHelper

class InterviewHelper:
    def __init__(self):
        self.db_helper = DatabaseHelper()
        self.interview_api_url = "http://localhost:5000"  # Your Flask interview API
    
    def start_interview_prep(self, job_id: str, candidate_id: str) -> Dict[str, Any]:
        """Start interview preparation for a specific job"""
        try:
            # Get job details
            job_details = self.db_helper.get_job_details(job_id)
            if not job_details:
                return {"success": False, "message": "Job not found"}
            
            # Get candidate's latest resume
            resume_filename = self.db_helper.get_candidate_resume(candidate_id)
            if not resume_filename:
                return {
                    "success": False,
                    "message": "No resume found for candidate",
                    "details": {"candidate_id": candidate_id},
                }
            
            # Prepare files for Flask API
            uploads_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Backend-PHP", "uploads")
            resume_path = os.path.join(uploads_dir, resume_filename)
            
            if not os.path.exists(resume_path):
                return {
                    "success": False,
                    "message": "Resume file not found",
                    "details": {
                        "candidate_id": candidate_id,
                        "resume_filename": resume_filename,
                        "resume_path": resume_path,
                    },
                }
            
            # Create temporary JD file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as jd_file:
                jd_file.write(f"Job Title: {job_details['title']}\n\n")
                jd_file.write(job_details['description'])
                jd_temp_path = jd_file.name
            
            try:
                # Call Flask interview API
                with open(resume_path, 'rb') as resume_file, open(jd_temp_path, 'rb') as jd_file:
                    files = {
                        'resume': (resume_filename, resume_file, 'application/pdf'),
                        'job_description': ('jd.txt', jd_file, 'text/plain')
                    }
                    
                    response = requests.post(
                        f"{self.interview_api_url}/start-interview",
                        files=files
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            "success": True,
                            "questions": data.get("questions", []),
                            "job_title": job_details['title'],
                            "job_description": job_details['description']
                        }
                    else:
                        return {
                            "success": False,
                            "message": f"Interview API error: {response.status_code}",
                            "details": response.text
                        }
            finally:
                if os.path.exists(jd_temp_path):
                    os.remove(jd_temp_path)
                    
        except Exception as e:
            return {"success": False, "message": str(e)}

    def generate_question_bank(
        self,
        resume_text: str,
        jd_text: str,
        num_questions: int = 20,
        include_audio: bool = True,
    ) -> Dict[str, Any]:
        """Generate a bank of interview questions using the AI service."""
        try:
            payload = {
                "resume_text": resume_text,
                "jd_text": jd_text,
                "num_questions": num_questions,
                "include_audio": include_audio,
            }
            response = requests.post(
                f"{self.interview_api_url}/generate-questions",
                json=payload,
                timeout=120,
            )
            if response.status_code == 200:
                return response.json()
            return {
                "success": False,
                "message": f"Interview API error: {response.status_code}",
                "details": response.text,
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    def evaluate_answer(
        self,
        resume_text: str,
        jd_text: str,
        question: str,
        answer_text: Optional[str] = None,
        answer_audio_base64: Optional[str] = None,
        audio_format: Optional[str] = None,
        sample_rate_hz: Optional[int] = None,
        include_audio: bool = True,
    ) -> Dict[str, Any]:
        """Evaluate an interview answer with optional audio input/output."""
        try:
            payload = {
                "resume_text": resume_text,
                "jd_text": jd_text,
                "question": question,
                "answer_text": answer_text,
                "answer_audio_base64": answer_audio_base64,
                "audio_format": audio_format,
                "sample_rate_hz": sample_rate_hz,
                "include_audio": include_audio,
            }
            response = requests.post(
                f"{self.interview_api_url}/evaluate-answer-advanced",
                json=payload,
                timeout=120,
            )
            if response.status_code == 200:
                return response.json()
            return {
                "success": False,
                "message": f"Interview API error: {response.status_code}",
                "details": response.text,
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

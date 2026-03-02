# api.py - Updated with reasoning feature
# run this to run every python file

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
import tempfile
import os
import re
import base64
import io
import wave
import time
import numpy as np
import requests
from core.extractor import extract_text, extract_skills, extract_contact_info
from core.matcher import ResumeMatcher
from core.utils import save_temp_file, cleanup_temp_file
from core.database_helper import DatabaseHelper
from core.interview_helper import InterviewHelper  
import json
from core.skill_gap_analyzer import SkillGapAnalyzer
from core.course_recommender import CourseRecommender
from core.course_catalog_sync import sync_catalog
import os
from core.reasoning_helper import ReasoningHelper
from core.tailor_helper import TailorHelper
from core.career_recommender import CareerRecommender
from dotenv import load_dotenv
try:
    from google.cloud import speech
    from google.oauth2 import service_account
except Exception:
    speech = None
    service_account = None

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

ASSEMBLYAI_BASE_URL = os.getenv("ASSEMBLYAI_BASE_URL", "https://api.assemblyai.com/v2").rstrip("/")
ASSEMBLYAI_API_KEY = (os.getenv("ASSEMBLYAI_API_KEY") or "").strip()
ASSEMBLYAI_POLL_INTERVAL_SECONDS = float(os.getenv("ASSEMBLYAI_POLL_INTERVAL_SECONDS", "0.8"))
ASSEMBLYAI_TRANSCRIBE_TIMEOUT_SECONDS = int(os.getenv("ASSEMBLYAI_TRANSCRIBE_TIMEOUT_SECONDS", "45"))
ASSEMBLYAI_LANGUAGE_CODE = (os.getenv("ASSEMBLYAI_LANGUAGE_CODE", "en") or "en").strip()
ASSEMBLYAI_SPEECH_MODELS = [
    model.strip()
    for model in (os.getenv("ASSEMBLYAI_SPEECH_MODELS", "universal-2") or "").split(",")
    if model.strip()
]
if not ASSEMBLYAI_SPEECH_MODELS:
    ASSEMBLYAI_SPEECH_MODELS = ["universal-2"]

app = FastAPI()
matcher = ResumeMatcher()
db_helper = DatabaseHelper()
interview_helper = InterviewHelper()
skill_gap_analyzer = SkillGapAnalyzer()
course_recommender = CourseRecommender()

def _build_speech_client():
    if speech is None:
        return None

    # 1) Prefer explicit credentials path in .env
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path:
        try:
            creds = service_account.Credentials.from_service_account_file(credentials_path)
            return speech.SpeechClient(credentials=creds)
        except Exception as e:
            print(f"Warning: failed to load Google credentials from file path: {e}")

    # 2) Fallback: inline service-account JSON in .env
    credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if credentials_json:
        try:
            info = json.loads(credentials_json)
            creds = service_account.Credentials.from_service_account_info(info)
            return speech.SpeechClient(credentials=creds)
        except Exception as e:
            print(f"Warning: failed to load Google credentials from JSON: {e}")

    # 3) Final fallback: default environment credentials (if set externally)
    try:
        return speech.SpeechClient()
    except Exception as e:
        print(f"Warning: default Google Speech client initialization failed: {e}")
        return None


speech_client = _build_speech_client()
_free_stt_pipeline = None


def _get_free_stt_pipeline():
    global _free_stt_pipeline
    if _free_stt_pipeline is not None:
        return _free_stt_pipeline
    try:
        from transformers import pipeline
        model_name = os.getenv("FREE_STT_MODEL", "openai/whisper-tiny.en")
        _free_stt_pipeline = pipeline(
            task="automatic-speech-recognition",
            model=model_name,
            device=-1,
        )
        print(f"Free STT initialized with model: {model_name}")
        return _free_stt_pipeline
    except Exception as e:
        print(f"Warning: free STT initialization failed: {e}")
        return None


def _resample_audio_linear(audio_np: np.ndarray, source_sr: int, target_sr: int = 16000) -> np.ndarray:
    """
    Lightweight numpy-only linear resampler to avoid torchaudio dependency.
    """
    if source_sr <= 0 or target_sr <= 0 or audio_np.size == 0 or source_sr == target_sr:
        return audio_np.astype(np.float32, copy=False)

    duration = audio_np.shape[0] / float(source_sr)
    target_len = max(1, int(round(duration * target_sr)))
    src_idx = np.arange(audio_np.shape[0], dtype=np.float32)
    dst_idx = np.linspace(0, audio_np.shape[0] - 1, num=target_len, dtype=np.float32)
    resampled = np.interp(dst_idx, src_idx, audio_np.astype(np.float32))
    return resampled.astype(np.float32, copy=False)


def _assemblyai_headers(content_type: Optional[str] = None) -> Dict[str, str]:
    if not ASSEMBLYAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="ASSEMBLYAI_API_KEY is not configured in Backend-Python/.env",
        )
    headers = {"authorization": ASSEMBLYAI_API_KEY}
    if content_type:
        headers["content-type"] = content_type
    return headers


def _normalize_assemblyai_language_code(language_code: Optional[str]) -> str:
    code = (language_code or ASSEMBLYAI_LANGUAGE_CODE or "en").strip().lower()
    if code.startswith("en"):
        return "en"
    return code


def _assemblyai_transcribe(audio_bytes: bytes, language_code: Optional[str] = None) -> str:
    if not audio_bytes:
        return ""

    upload_response = requests.post(
        f"{ASSEMBLYAI_BASE_URL}/upload",
        headers=_assemblyai_headers("application/octet-stream"),
        data=audio_bytes,
        timeout=30,
    )
    if upload_response.status_code >= 300:
        raise HTTPException(
            status_code=502,
            detail=f"AssemblyAI upload failed ({upload_response.status_code}): {upload_response.text}",
        )
    upload_url = (upload_response.json() or {}).get("upload_url")
    if not upload_url:
        raise HTTPException(status_code=502, detail="AssemblyAI upload did not return upload_url.")

    transcript_payload: Dict[str, Any] = {
        "audio_url": upload_url,
        "speech_models": ASSEMBLYAI_SPEECH_MODELS,
        "language_code": _normalize_assemblyai_language_code(language_code),
    }

    transcript_response = requests.post(
        f"{ASSEMBLYAI_BASE_URL}/transcript",
        headers=_assemblyai_headers("application/json"),
        json=transcript_payload,
        timeout=30,
    )
    if transcript_response.status_code >= 300:
        raise HTTPException(
            status_code=502,
            detail=f"AssemblyAI transcript request failed ({transcript_response.status_code}): {transcript_response.text}",
        )
    transcript_id = (transcript_response.json() or {}).get("id")
    if not transcript_id:
        raise HTTPException(status_code=502, detail="AssemblyAI transcript request did not return id.")

    started = time.time()
    while (time.time() - started) <= ASSEMBLYAI_TRANSCRIBE_TIMEOUT_SECONDS:
        status_response = requests.get(
            f"{ASSEMBLYAI_BASE_URL}/transcript/{transcript_id}",
            headers=_assemblyai_headers(),
            timeout=30,
        )
        if status_response.status_code >= 300:
            raise HTTPException(
                status_code=502,
                detail=f"AssemblyAI transcript polling failed ({status_response.status_code}): {status_response.text}",
            )

        payload = status_response.json() or {}
        status = str(payload.get("status") or "").lower()
        if status == "completed":
            return str(payload.get("text") or "").strip()
        if status == "error":
            error_text = str(payload.get("error") or "unknown error")
            lowered = error_text.lower()
            if (
                "no spoken audio" in lowered
                or "transcoding failed" in lowered
                or "does not appear to contain audio" in lowered
            ):
                return ""
            raise HTTPException(
                status_code=502,
                detail=f"AssemblyAI transcription error: {error_text}",
            )
        time.sleep(ASSEMBLYAI_POLL_INTERVAL_SECONDS)

    raise HTTPException(
        status_code=504,
        detail="AssemblyAI transcription timed out while waiting for completion.",
    )

# Initialize reasoning helper with error handling
try:
    reasoning_helper = ReasoningHelper()
    print("ReasoningHelper initialized successfully")
except Exception as e:
    print(f"Warning: ReasoningHelper initialization failed: {str(e)}")
    reasoning_helper = None

# Initialize tailor helper with error handling
try:
    tailor_helper = TailorHelper()
    print("TailorHelper initialized successfully")
except Exception as e:
    print(f"Warning: TailorHelper initialization failed: {str(e)}")
    tailor_helper = None

# Initialize career recommender with error handling
try:
    career_recommender = CareerRecommender()
    print("CareerRecommender initialized successfully")
except Exception as e:
    print(f"Warning: CareerRecommender initialization failed: {str(e)}")
    career_recommender = None

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def generate_recommendation(similarity: float) -> str:
    """Generate recommendation based on similarity score"""
    if similarity >= 0.7:
        return "Excellent match! You're a strong candidate for this role."
    elif similarity >= 0.5:
        return "Good match. Consider highlighting relevant skills in your application."
    else:
        return "Consider gaining more relevant skills or tailoring your resume to better match this role."

def generate_reasoning_response(similarity: float, skills: List[str], resume_text: str = "", job_description: str = "") -> dict:
    """Generate reasoning for the match score"""
    if similarity >= 0.8:
        return {
            "score_explanation": f"Score of {similarity:.2f} indicates excellent alignment with job requirements.",
            "strengths": ["Strong skill match", "Relevant experience", "Keyword alignment"],
            "gaps": ["Consider adding more quantifiable achievements"],
            "suggestions": ["Highlight key accomplishments", "Add specific metrics"],
            "overall_assessment": "Highly qualified candidate for this role"
        }
    elif similarity >= 0.7:
        return {
            "score_explanation": f"Score of {similarity:.2f} shows strong alignment with most requirements.",
            "strengths": ["Good skill coverage", "Relevant background", "Some keyword matches"],
            "gaps": ["Could improve specific skill highlighting", "Add more relevant keywords"],
            "suggestions": ["Tailor resume to job description", "Add missing keywords"],
            "overall_assessment": "Strong candidate with minor improvements needed"
        }
    elif similarity >= 0.5:
        return {
            "score_explanation": f"Score of {similarity:.2f} indicates moderate alignment.",
            "strengths": ["Some relevant skills", "Basic qualifications met"],
            "gaps": ["Missing key technical skills", "Experience gaps"],
            "suggestions": ["Focus on transferable skills", "Add relevant training/certifications"],
            "overall_assessment": "Consider upskilling to improve match"
        }
    else:
        return {
            "score_explanation": f"Score of {similarity:.2f} suggests significant gaps.",
            "strengths": ["Transferable skills present"],
            "gaps": ["Limited relevant experience", "Skill mismatches"],
            "suggestions": ["Consider different role types", "Focus on skill development"],
            "overall_assessment": "Significant improvements needed for this role"
        }


class TailorResumeRequest(BaseModel):
    resume_data: dict
    job_id: Optional[str] = None
    job_description: Optional[str] = None


class TailorResumeTextRequest(BaseModel):
    candidate_id: str
    job_id: str
    resume_filename: str


class InterviewStartRequest(BaseModel):
    candidate_id: str
    job_id: str
    question_count: int = 10
    include_audio: bool = True
    resume_type: str = "latest"
    resume_id: Optional[str] = None
    resume_filename: Optional[str] = None


class InterviewNextRequest(BaseModel):
    session_id: int


class InterviewAnswerRequest(BaseModel):
    session_id: int
    question_id: int
    answer_text: Optional[str] = None
    answer_audio_base64: Optional[str] = None
    audio_format: Optional[str] = None
    sample_rate_hz: Optional[int] = None
    include_audio: bool = True


class InterviewTranscribeRequest(BaseModel):
    audio_base64: str
    audio_format: Optional[str] = "webm_opus"
    sample_rate_hz: Optional[int] = None
    language_code: Optional[str] = "en-US"


class InterviewStopRequest(BaseModel):
    session_id: int


class InterviewResumeRequest(BaseModel):
    candidate_id: str
    job_id: str


class CareerRecommendationRequest(BaseModel):
    candidate_id: str
    resume_type: str = "latest"
    resume_id: Optional[str] = None
    resume_filename: Optional[str] = None


def _merge_resume_data(base: dict, updates: Optional[dict]) -> dict:
    if not updates:
        return base
    merged = dict(base)

    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_resume_data(merged[key], value)
        else:
            merged[key] = value

    return merged


def _fetch_builder_resume_text(candidate_id: str) -> str:
    resume_text = ""
    connection = db_helper.get_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT resume_data 
            FROM resumes 
            WHERE user_id = %s 
            ORDER BY updated_at DESC 
            LIMIT 1
        """
        cursor.execute(query, (candidate_id,))
        result = cursor.fetchone()
        if result and result['resume_data']:
            resume_data = json.loads(result['resume_data'])
            resume_text = convert_resume_data_to_text(resume_data)
        cursor.close()
        connection.close()
    return resume_text


def _fetch_builder_resume_text_by_id(candidate_id: str, resume_id: str) -> str:
    resume_text = ""
    connection = db_helper.get_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT resume_data 
            FROM resumes 
            WHERE user_id = %s AND id = %s
            LIMIT 1
        """
        cursor.execute(query, (candidate_id, resume_id))
        result = cursor.fetchone()
        if result and result['resume_data']:
            resume_data = json.loads(result['resume_data'])
            resume_text = convert_resume_data_to_text(resume_data)
        cursor.close()
        connection.close()
    return resume_text


def _get_uploads_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Backend-PHP", "uploads"))


def _fetch_uploaded_resume_text(candidate_id: str) -> str:
    resume_text = ""
    resume_filename = db_helper.get_candidate_resume(candidate_id)
    if resume_filename:
        uploads_dir = _get_uploads_dir()
        resume_path = os.path.join(uploads_dir, resume_filename)
        if os.path.exists(resume_path):
            resume_text, _ = extract_text(resume_path)
    return resume_text


def _fetch_uploaded_resume_text_by_filename(candidate_id: str, resume_filename: str) -> str:
    resume_text = ""
    if not resume_filename:
        return resume_text
    cleaned = "".join(resume_filename.split())
    safe_name = os.path.basename(cleaned)
    if safe_name != resume_filename:
        return resume_text
    uploads_dir = _get_uploads_dir()
    resume_path = os.path.join(uploads_dir, safe_name)
    if not os.path.exists(resume_path):
        return resume_text
    if not db_helper.candidate_has_uploaded_resume(candidate_id, safe_name):
        # If DB is out of sync, still allow local file usage
        resume_text, _ = extract_text(resume_path)
        return resume_text
    resume_text, _ = extract_text(resume_path)
    return resume_text


def _get_resume_text_for_candidate(candidate_id: str, resume_type: str = "latest") -> str:
    """Fetch resume text for a candidate using uploads with fallback to builder."""
    if resume_type == "builder":
        return _fetch_builder_resume_text(candidate_id)
    if resume_type == "uploaded":
        return _fetch_uploaded_resume_text(candidate_id)
    if resume_type == "latest":
        resume_text = _fetch_uploaded_resume_text(candidate_id)
        if resume_text:
            return resume_text
        return _fetch_builder_resume_text(candidate_id)
    if resume_type == "auto":
        resume_text = _fetch_uploaded_resume_text(candidate_id)
        return resume_text or _fetch_builder_resume_text(candidate_id)
    return ""


def _get_resume_text_for_candidate_selected(
    candidate_id: str,
    resume_type: str = "latest",
    resume_id: Optional[str] = None,
    resume_filename: Optional[str] = None
) -> str:
    if resume_type == "builder":
        if resume_id:
            return _fetch_builder_resume_text_by_id(candidate_id, resume_id)
        return _fetch_builder_resume_text(candidate_id)
    if resume_type == "uploaded":
        if resume_filename:
            return _fetch_uploaded_resume_text_by_filename(candidate_id, resume_filename)
        return _fetch_uploaded_resume_text(candidate_id)
    return _get_resume_text_for_candidate(candidate_id, resume_type)


@app.post("/api/tailor-resume")
async def tailor_resume(request: TailorResumeRequest):
    """
    Tailor resume content for a job description using Gemini.
    Accepts either job_id (from DB) or job_description (free text), or both.
    """
    if not tailor_helper:
        raise HTTPException(status_code=503, detail="Tailor helper not available")

    job_id = request.job_id.strip() if request.job_id else ""
    job_description = (request.job_description or "").strip()

    db_description = ""
    if job_id:
        db_description = db_helper.get_job_description(job_id) or ""

    if not db_description and not job_description:
        raise HTTPException(status_code=400, detail="Provide job_id or job_description")

    if db_description and job_description:
        full_description = f"{db_description}\n\nAdditional context from user:\n{job_description}"
    else:
        full_description = db_description or job_description

    try:
        result = tailor_helper.tailor_resume(request.resume_data, full_description)

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Tailoring failed"))

        tailored = _merge_resume_data(request.resume_data, result.get("resume_data"))

        return {
            "success": True,
            "resume_data": tailored,
            "changes_summary": result.get("changes_summary", ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        # Debug-friendly response to surface the underlying issue
        return {
            "success": False,
            "error": str(e),
        }


@app.post("/api/tailor-resume-text")
async def tailor_resume_text(request: TailorResumeTextRequest):
    """
    Tailor an uploaded resume (text) to a job description using Gemini.
    """
    if not tailor_helper:
        raise HTTPException(status_code=503, detail="Tailor helper not available")

    job_description = db_helper.get_job_description(request.job_id) or ""
    if not job_description:
        raise HTTPException(status_code=404, detail="Job not found")

    resume_text = _fetch_uploaded_resume_text_by_filename(request.candidate_id, request.resume_filename)
    if not resume_text:
        raise HTTPException(status_code=404, detail="Resume not found for candidate")

    try:
        result = tailor_helper.tailor_resume_text(resume_text, job_description)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Tailoring failed"))
        return {
            "success": True,
            "tailored_text": result.get("tailored_text", ""),
            "changes_summary": result.get("changes_summary", ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }

@app.post("/api/match-score/{job_id}")
async def calculate_match_score_for_job(
    job_id: str,
    resume: UploadFile = File(...),
    candidate_id: Optional[str] = Form(None),
    include_reasoning: bool = Form(False)
):
    """
    Calculate match score between user's resume and a specific job from database
    """
    try:
        # Fetch job details from database
        job_details = db_helper.get_job_details(job_id)
        if not job_details:
            raise HTTPException(status_code=404, detail="Job not found")
        job_description = f"{job_details.get('title','')}\n\n{job_details.get('description','')}".strip()
        recruiter_required_skills = parse_required_skills(job_details.get("required_skills"))
        
        # Save resume temporarily
        temp_path = None
        try:
            temp_path = save_temp_file(
                await resume.read(),
                suffix=os.path.splitext(resume.filename)[1]
            )
            
            # Extract text from resume
            resume_text, _ = extract_text(temp_path)
            skills = extract_skills(resume_text)
            detected_skills = filter_detected_skills(resume_text, job_description, top_n=10)
            
            # Calculate similarity
            similarity = matcher.calculate_similarity(
                resume_text, 
                job_description, 
                skills=skills,
                required_skills=recruiter_required_skills if recruiter_required_skills else None
            )
            
            response = {
                "success": True,
                "job_id": job_id,
                "job_title": job_details.get("title", "Unknown") if job_details else "Unknown",
                "similarity_score": round(similarity, 4),
                "match_percentage": round(similarity * 100, 1),
                "detected_skills": detected_skills,
                "required_skills": recruiter_required_skills,
                "recommendation": generate_recommendation(similarity),
                "job_description_preview": job_description[:500] + "..." if len(job_description) > 500 else job_description
            }
            
            # Add reasoning if requested
            if include_reasoning:
                if reasoning_helper:
                    try:
                        reasoning_result = reasoning_helper.generate_match_reasoning(
                            resume_text=resume_text,
                            job_description=job_description,
                            similarity_score=similarity,
                            detected_skills=skills
                        )
                        response["reasoning"] = reasoning_result.get("reasoning", {})
                        response["reasoning_success"] = reasoning_result.get("success", False)
                        if not reasoning_result.get("success", False):
                            response["reasoning_error"] = reasoning_result.get("error", "AI reasoning generation failed")
                    except Exception as e:
                        print(f"AI reasoning failed: {str(e)}")
                        response["reasoning"] = {}
                        response["reasoning_success"] = False
                        response["reasoning_error"] = str(e)
                else:
                    response["reasoning"] = {}
                    response["reasoning_success"] = False
                    response["reasoning_error"] = "AI reasoning is not configured. Set GOOGLE_API_KEY in backend env."
            
            return response
            
        finally:
            if temp_path and os.path.exists(temp_path):
                cleanup_temp_file(temp_path)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/match-score-with-existing/{job_id}")
async def calculate_match_score_existing_resume(
    job_id: str,
    candidate_id: str = Form(...),
    resume_type: str = Form("latest"),  # "latest", "builder", "uploaded"
    resume_id: Optional[str] = Form(None),
    resume_filename: Optional[str] = Form(None),
    include_reasoning: bool = Form(False)
):
    """
    Calculate match score using existing resume from database
    Options:
    - latest: Use latest uploaded resume from applications
    - builder: Use resume from resume builder (from resumes table)
    """
    try:
        # Fetch job details
        job_details = db_helper.get_job_details(job_id)
        if not job_details:
            raise HTTPException(status_code=404, detail="Job not found")
        job_description = f"{job_details.get('title','')}\n\n{job_details.get('description','')}".strip()
        recruiter_required_skills = parse_required_skills(job_details.get("required_skills"))
        
        resume_text = _get_resume_text_for_candidate_selected(
            candidate_id=candidate_id,
            resume_type=resume_type,
            resume_id=resume_id,
            resume_filename=resume_filename
        )

        if not resume_text:
            if resume_type == "builder" and resume_id:
                raise HTTPException(status_code=404, detail="Selected builder resume not found")
            if resume_type == "uploaded" and resume_filename:
                uploads_dir = _get_uploads_dir()
                resume_path = os.path.join(uploads_dir, os.path.basename(resume_filename))
                if not os.path.exists(resume_path):
                    raise HTTPException(status_code=404, detail="Uploaded resume file not found")
                raise HTTPException(status_code=422, detail="Could not extract text from the uploaded resume")
            raise HTTPException(status_code=404, detail="No resume found for candidate")
        
        # Extract skills and calculate similarity
        skills = extract_skills(resume_text)
        detected_skills = filter_detected_skills(resume_text, job_description, top_n=10)
        similarity = matcher.calculate_similarity(
            resume_text,
            job_description,
            skills=skills,
            required_skills=recruiter_required_skills if recruiter_required_skills else None
        )
        
        response = {
            "success": True,
            "job_id": job_id,
            "similarity_score": round(similarity, 4),
            "match_percentage": round(similarity * 100, 1),
            "detected_skills": detected_skills,
            "required_skills": recruiter_required_skills,
            "recommendation": generate_recommendation(similarity),
            "resume_type_used": resume_type
        }
        
        # Add reasoning if requested
        if include_reasoning:
            if reasoning_helper:
                try:
                    reasoning_result = reasoning_helper.generate_match_reasoning(
                        resume_text=resume_text,
                        job_description=job_description,
                        similarity_score=similarity,
                        detected_skills=skills
                    )
                    response["reasoning"] = reasoning_result.get("reasoning", {})
                    response["reasoning_success"] = reasoning_result.get("success", False)
                    if not reasoning_result.get("success", False):
                        response["reasoning_error"] = reasoning_result.get("error", "AI reasoning generation failed")
                except Exception as e:
                    print(f"AI reasoning failed: {str(e)}")
                    response["reasoning"] = {}
                    response["reasoning_success"] = False
                    response["reasoning_error"] = str(e)
            else:
                response["reasoning"] = {}
                response["reasoning_success"] = False
                response["reasoning_error"] = "AI reasoning is not configured. Set GOOGLE_API_KEY in backend env."
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/match-reasoning/{job_id}")
async def get_match_reasoning(
    job_id: str,
    resume: UploadFile = File(...),
    similarity_score: float = Form(...),
    candidate_id: Optional[str] = Form(None)
):
    """
    Get detailed reasoning for a match score (can be called separately)
    """
    try:
        job_description = db_helper.get_job_description(job_id)
        if not job_description:
            raise HTTPException(status_code=404, detail="Job not found")
        
        temp_path = None
        try:
            temp_path = save_temp_file(
                await resume.read(),
                suffix=os.path.splitext(resume.filename)[1]
            )
            
            resume_text, _ = extract_text(temp_path)
            skills = extract_skills(resume_text)
            
            if reasoning_helper:
                reasoning_result = reasoning_helper.generate_match_reasoning(
                    resume_text=resume_text,
                    job_description=job_description,
                    similarity_score=similarity_score,
                    detected_skills=skills
                )
                return reasoning_result
            else:
                return {
                    "success": False,
                    "error": "AI reasoning is not configured. Set GOOGLE_API_KEY in backend env.",
                    "reasoning": {}
                }
                
        finally:
            if temp_path and os.path.exists(temp_path):
                cleanup_temp_file(temp_path)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def convert_resume_data_to_text(resume_data: dict) -> str:
    """Convert resume builder JSON data to plain text"""
    text_parts = []
    
    # Basic info
    if resume_data.get('personalInfo'):
        info = resume_data['personalInfo']
        text_parts.append(f"{info.get('fullName', '')}")
        if info.get('email'):
            text_parts.append(f"Email: {info['email']}")
        if info.get('phone'):
            text_parts.append(f"Phone: {info['phone']}")
        if info.get('location'):
            text_parts.append(f"Location: {info['location']}")
    
    # Summary
    if resume_data.get('summary'):
        text_parts.append(f"\nSummary: {resume_data['summary']}")
    
    # Experience
    if resume_data.get('experience'):
        text_parts.append("\nExperience:")
        for exp in resume_data['experience']:
            text_parts.append(f"- {exp.get('position', '')} at {exp.get('company', '')}")
            if exp.get('duration'):
                text_parts.append(f"  Duration: {exp['duration']}")
            if exp.get('description'):
                text_parts.append(f"  Description: {exp['description']}")
    
    # Education
    if resume_data.get('education'):
        text_parts.append("\nEducation:")
        for edu in resume_data['education']:
            text_parts.append(f"- {edu.get('degree', '')} from {edu.get('institution', '')}")
            if edu.get('year'):
                text_parts.append(f"  Year: {edu['year']}")
    
    # Skills
    if resume_data.get('skills'):
        skills = resume_data['skills']
        if isinstance(skills, list):
            text_parts.append(f"\nSkills: {', '.join(skills)}")
        elif isinstance(skills, str):
            text_parts.append(f"\nSkills: {skills}")
    
    return "\n".join(text_parts)

def filter_detected_skills(resume_text: str, job_description: str, top_n: int = 10) -> List[str]:
    """
    Detect skills by extracting JD skills and keeping resume phrases that semantically match them.
    """
    jd_skills = extract_skills(job_description, similarity_threshold=0.35)
    resume_skills = extract_skills(resume_text, similarity_threshold=0.35)

    if not jd_skills or not resume_skills:
        return resume_skills[:top_n]

    jd_embeddings = matcher.embedder.encode_batch(jd_skills)
    resume_embeddings = matcher.embedder.encode_batch(resume_skills)

    matched = []
    for r_idx, r_skill in enumerate(resume_skills):
        r_vec = resume_embeddings[r_idx]
        best_score = 0.0
        best_jd = None
        for j_idx, j_skill in enumerate(jd_skills):
            j_vec = jd_embeddings[j_idx]
            score = float((r_vec * j_vec).sum())
            if score > best_score:
                best_score = score
                best_jd = j_skill
        if best_score >= 0.7:
            matched.append((r_skill, best_score, best_jd))

    matched.sort(key=lambda x: x[1], reverse=True)
    return [m[0] for m in matched[:top_n]]


def parse_required_skills(raw_required_skills: Any) -> List[str]:
    if raw_required_skills is None:
        return []
    if isinstance(raw_required_skills, list):
        items = raw_required_skills
    else:
        text = str(raw_required_skills).strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            items = parsed if isinstance(parsed, list) else re.split(r"[,;\n|]+", text)
        except Exception:
            items = re.split(r"[,;\n|]+", text)

    cleaned = []
    seen = set()
    for it in items:
        skill = str(it or "").strip().lower()
        skill = re.sub(r"\s+", " ", skill)
        if not skill or skill in seen:
            continue
        seen.add(skill)
        cleaned.append(skill)
    return cleaned[:80]

@app.get("/api/job/{job_id}")
async def get_job_details(job_id: str):
    """Get job details for display"""
    try:
        job_details = db_helper.get_job_details(job_id)
        if not job_details:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "success": True,
            "job": job_details
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/career-recommendation")
async def get_career_recommendation(request: CareerRecommendationRequest):
    if not career_recommender:
        raise HTTPException(status_code=503, detail="Career recommendation model is not available")

    try:
        resume_text = _get_resume_text_for_candidate_selected(
            candidate_id=request.candidate_id,
            resume_type=request.resume_type,
            resume_id=request.resume_id,
            resume_filename=request.resume_filename
        )

        if not resume_text:
            raise HTTPException(status_code=404, detail="No resume content found for candidate")

        recommendation = career_recommender.recommend_from_resume_text(resume_text)

        return {
            "success": True,
            "resume_type_used": request.resume_type,
            **recommendation
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _resolve_stt_encoding(audio_format: Optional[str]):
    if speech is None:
        return None
    normalized = str(audio_format or "").strip().lower()
    aliases = {
        "webm": "webm_opus",
        "audio/webm": "webm_opus",
        "audio/webm;codecs=opus": "webm_opus",
        "ogg": "ogg_opus",
        "audio/ogg": "ogg_opus",
        "audio/ogg;codecs=opus": "ogg_opus",
        "wav": "linear16",
        "audio/wav": "linear16",
        "audio/x-wav": "linear16",
        "mp3": "mp3",
        "audio/mp3": "mp3",
        "audio/mpeg": "mp3",
    }
    key = aliases.get(normalized, normalized)
    mapping = {
        "linear16": speech.RecognitionConfig.AudioEncoding.LINEAR16,
        "ogg_opus": speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
        "webm_opus": speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
        "mp3": speech.RecognitionConfig.AudioEncoding.MP3,
    }
    return mapping.get(key, speech.RecognitionConfig.AudioEncoding.WEBM_OPUS)


@app.post("/api/interview/transcribe")
async def interview_transcribe(request: InterviewTranscribeRequest):
    """
    Transcribe short microphone chunks via AssemblyAI.
    """
    try:
        audio_bytes = base64.b64decode(request.audio_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid audio_base64 payload.")

    if not audio_bytes:
        return {"success": True, "transcript": ""}
    transcript = _assemblyai_transcribe(audio_bytes, language_code=request.language_code)
    return {"success": True, "transcript": transcript}

@app.get("/health")
async def health_check():
    # Test database connection
    db_connected = db_helper.get_connection() is not None
    return {
        "status": "healthy",
        "model": "all-MiniLM-L6-v2",
        "database_connected": db_connected,
        "reasoning_helper_available": reasoning_helper is not None
    }

@app.post("/api/interview-prep/{job_id}")
async def start_interview_preparation(
    job_id: str,
    candidate_id: str = Form(...),
    resume_type: str = Form("latest")
):
    """
    Start AI interview preparation for a specific job
    """
    try:
        result = interview_helper.start_interview_prep(job_id, candidate_id)
        if not result.get("success"):
            # Bubble up structured details when available
            raise HTTPException(status_code=400, detail=result)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/quick-match/{job_id}")
async def quick_match_check(
    job_id: str,
    candidate_id: str = Form(...),
    include_reasoning: bool = Form(False)
):
    """
    Quick match check without file upload - uses existing resume
    """
    try:
        result = await calculate_match_score_existing_resume(
            job_id, 
            candidate_id, 
            resume_type="latest",
            include_reasoning=include_reasoning
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/interview/start")
async def interview_start(request: InterviewStartRequest):
    """
    Start a new interview session and generate a question bank.
    """
    try:
        job_description = db_helper.get_job_description(request.job_id)
        if not job_description:
            raise HTTPException(status_code=404, detail="Job not found")

        resume_text = _get_resume_text_for_candidate_selected(
            candidate_id=request.candidate_id,
            resume_type=request.resume_type,
            resume_id=request.resume_id,
            resume_filename=request.resume_filename
        )
        if not resume_text:
            raise HTTPException(status_code=404, detail="No resume found for candidate")

        session_id = db_helper.create_interview_session(
            candidate_id=request.candidate_id,
            job_id=request.job_id,
            total_questions=request.question_count,
            resume_text=resume_text,
            jd_text=job_description,
        )
        if not session_id:
            raise HTTPException(status_code=500, detail="Failed to create interview session")

        ai_result = interview_helper.generate_question_bank(
            resume_text=resume_text,
            jd_text=job_description,
            num_questions=request.question_count,
            include_audio=request.include_audio,
        )
        if not ai_result.get("success"):
            db_helper.update_interview_session_status(session_id, "stopped")
            raise HTTPException(status_code=502, detail=ai_result)

        questions = ai_result.get("questions", [])
        if not questions:
            db_helper.update_interview_session_status(session_id, "stopped")
            raise HTTPException(status_code=500, detail="No questions generated")

        if not db_helper.add_interview_questions(session_id, questions):
            db_helper.update_interview_session_status(session_id, "stopped")
            raise HTTPException(status_code=500, detail="Failed to store questions")

        next_q = db_helper.get_next_interview_question(session_id)
        if not next_q:
            raise HTTPException(status_code=500, detail="Failed to fetch next question")

        return {
            "success": True,
            "session_id": session_id,
            "total_questions": request.question_count,
            "next_question": next_q,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/interview/next")
async def interview_next(request: InterviewNextRequest):
    """
    Fetch the next interview question for a session.
    """
    try:
        session = db_helper.get_interview_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.get("status") == "completed":
            return {"success": True, "done": True, "message": "Interview completed"}

        next_q = db_helper.get_next_interview_question(request.session_id)
        if not next_q:
            db_helper.update_interview_session_status(request.session_id, "completed")
            final_score = db_helper.get_interview_average_score(request.session_id)
            return {
                "success": True,
                "done": True,
                "message": "No more questions",
                "final_score": final_score
            }

        return {"success": True, "next_question": next_q}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/interview/answer")
async def interview_answer(request: InterviewAnswerRequest):
    """
    Save an interview answer and return AI feedback (text + audio).
    """
    try:
        session = db_helper.get_interview_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        question = db_helper.get_interview_question(request.question_id)
        if not question or question.get("session_id") != request.session_id:
            raise HTTPException(status_code=404, detail="Question not found for session")

        resume_text = session.get("resume_text") or ""
        jd_text = session.get("jd_text") or ""
        if not resume_text or not jd_text:
            raise HTTPException(status_code=500, detail="Session text data missing")

        raw_format = str(request.audio_format or "").strip().lower()
        format_aliases = {
            "audio/webm": "webm",
            "audio/webm;codecs=opus": "webm",
            "webm_opus": "webm",
            "audio/ogg": "ogg",
            "audio/ogg;codecs=opus": "ogg",
            "ogg_opus": "ogg",
            "audio/wav": "wav",
            "audio/x-wav": "wav",
            "linear16": "wav",
            "audio/mp3": "mp3",
            "audio/mpeg": "mp3",
        }
        normalized_format = format_aliases.get(raw_format, raw_format or None)

        fallback_formats = [normalized_format]
        if request.answer_audio_base64 and not request.answer_text:
            for candidate in [None, "webm", "ogg", "wav", "mp3"]:
                if candidate not in fallback_formats:
                    fallback_formats.append(candidate)

        ai_result = None
        for candidate_format in fallback_formats:
            attempt = interview_helper.evaluate_answer(
                resume_text=resume_text,
                jd_text=jd_text,
                question=question.get("question_text", ""),
                answer_text=request.answer_text,
                answer_audio_base64=request.answer_audio_base64,
                audio_format=candidate_format,
                sample_rate_hz=request.sample_rate_hz,
                include_audio=request.include_audio,
            )

            if attempt.get("success") and (
                (attempt.get("answer_text") and str(attempt.get("answer_text")).strip())
                or isinstance(attempt.get("feedback"), dict)
            ):
                ai_result = attempt
                break

            # Keep last attempt for error reporting.
            ai_result = attempt

        if not ai_result or not ai_result.get("success"):
            raise HTTPException(status_code=502, detail=ai_result or {"success": False, "message": "Interview evaluation failed"})

        feedback = ai_result.get("feedback", {})
        score = feedback.get("score") if isinstance(feedback, dict) else None

        db_helper.save_interview_answer(
            session_id=request.session_id,
            question_id=request.question_id,
            answer_text=ai_result.get("answer_text", request.answer_text or ""),
            answer_audio_base64=request.answer_audio_base64,
            feedback_json=feedback if isinstance(feedback, dict) else {"raw": feedback},
            feedback_audio_base64=ai_result.get("feedback_audio_base64"),
            score=score,
        )

        return {
            "success": True,
            "feedback": feedback,
            "feedback_audio_base64": ai_result.get("feedback_audio_base64"),
            "feedback_audio_mime": ai_result.get("feedback_audio_mime"),
            "answer_text": ai_result.get("answer_text", request.answer_text or ""),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/interview/stop")
async def interview_stop(request: InterviewStopRequest):
    """
    Stop/pause an interview session.
    """
    try:
        if not db_helper.update_interview_session_status(request.session_id, "stopped"):
            raise HTTPException(status_code=500, detail="Failed to stop session")
        return {"success": True, "status": "stopped"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/interview/resume")
async def interview_resume(request: InterviewResumeRequest):
    """
    Resume the latest active/stopped interview session for a candidate and job.
    """
    try:
        session = db_helper.get_latest_active_session(request.candidate_id, request.job_id)
        if not session:
            raise HTTPException(status_code=404, detail="No active session found")

        if session.get("status") != "active":
            db_helper.update_interview_session_status(session["id"], "active")

        next_q = db_helper.get_next_interview_question(session["id"])
        if not next_q:
            db_helper.update_interview_session_status(session["id"], "completed")
            final_score = db_helper.get_interview_average_score(session["id"])
            return {
                "success": True,
                "done": True,
                "message": "No more questions",
                "final_score": final_score
            }

        return {
            "success": True,
            "session_id": session["id"],
            "next_question": next_q,
            "total_questions": session.get("total_questions")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/interview/sessions")
async def list_interview_sessions(candidate_id: str, job_id: Optional[str] = None):
    """
    List interview sessions for a candidate (optionally filtered by job).
    """
    try:
        sessions = db_helper.list_interview_sessions(candidate_id, job_id)
        enriched = []
        for session in sessions:
            session_id = session.get("id")
            final_score = db_helper.get_interview_average_score(session_id) if session_id else 0.0
            enriched.append({
                **session,
                "final_score": final_score
            })
        return {"success": True, "sessions": enriched}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/interview/session/{session_id}")
async def get_interview_session_detail(session_id: int):
    """
    Get full interview session details (questions + answers + score).
    """
    try:
        session = db_helper.get_interview_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        questions = db_helper.get_interview_questions_for_session(session_id)
        answers = db_helper.get_interview_answers_for_session(session_id)

        for answer in answers:
            raw = answer.get("feedback_json")
            if isinstance(raw, str):
                try:
                    answer["feedback_json"] = json.loads(raw)
                except Exception:
                    answer["feedback_json"] = {"raw": raw}

        final_score = db_helper.get_interview_average_score(session_id)

        return {
            "success": True,
            "session": session,
            "questions": questions,
            "answers": answers,
            "final_score": final_score
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/skill-gap-analysis/{job_id}")
async def skill_gap_analysis(
    job_id: str,
    candidate_id: str = Form(...),
    resume_type: str = Form("latest"),
    resume_id: Optional[str] = Form(None),
    resume_filename: Optional[str] = Form(None)
):
    """
    Analyze skill gap between candidate's resume and job description.
    """
    try:
        # 1. Get job details
        job_details = db_helper.get_job_details(job_id)
        if not job_details:
            raise HTTPException(status_code=404, detail="Job not found")

        # 2. Extract resume text based on selected resume
        resume_text = _get_resume_text_for_candidate_selected(
            candidate_id=candidate_id,
            resume_type=resume_type,
            resume_id=resume_id,
            resume_filename=resume_filename
        )
        if not resume_text:
            raise HTTPException(status_code=404, detail="No resume found for candidate")

        # 4. Analyze skill gap using semantic analyzer.
        recruiter_required_skills = parse_required_skills(job_details.get("required_skills"))
        analysis = skill_gap_analyzer.analyze_skill_gap(
            resume_text=resume_text,
            jd_text=job_details["description"],
            required_skills=recruiter_required_skills if recruiter_required_skills else None
        )

        missing_skills_data = analysis.get("missing_skills", [])
        matching_skills_data = analysis.get("matched_skills", [])

        missing_skill_names = [s.get("skill") for s in missing_skills_data if s.get("skill")]
        matching_skill_names = [s.get("skill") for s in matching_skills_data if s.get("skill")]

        # 5. Course recommendations per missing skill (normalized to frontend shape)
        course_recommendations = {}
        for skill_data in missing_skills_data:
            skill_name = skill_data.get("skill")
            if not skill_name:
                continue

            recs = course_recommender.get_course_recommendations(
                skill_name,
                per_source=3
            )

            course_recommendations[skill_name] = {
                "youtube_videos": recs.get("youtube_videos", []),
                "online_courses": recs.get("online_courses", [])
            }

        # 6. Learning path (optional)
        learning_path = skill_gap_analyzer.get_learning_path(missing_skills_data)

        # 7. Response
        return {
            "success": True,
            "job_id": job_id,
            "job_title": job_details["title"],
            "required_skills": recruiter_required_skills,
            "resume_skills_count": len(analysis.get("matched_skills", [])) + len(missing_skills_data),
            "jd_skills_count": analysis.get("total_required_skills", 0),
            "missing_skills": missing_skill_names,
            "missing_skills_count": len(missing_skill_names),
            "matching_skills": matching_skill_names,
            "matching_skills_count": len(matching_skill_names),
            "ai_analysis_enabled": analysis.get("ai_analysis_enabled", False),
            "ai_analysis_used": analysis.get("ai_analysis_used", False),
            "extraction_details": analysis.get("extraction_details", {}),
            "course_recommendations": course_recommendations,
            "course_count": sum(
                len(recs.get("youtube_videos", [])) + len(recs.get("online_courses", []))
                for recs in course_recommendations.values()
            ),
            "learning_path": learning_path
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/skill-gap-analysis/{job_id}")
async def skill_gap_analysis_get(
    job_id: str,
    candidate_id: str,
    resume_type: str = "latest",
    resume_id: Optional[str] = None,
    resume_filename: Optional[str] = None
):
    """
    GET-friendly wrapper for skill gap analysis.
    """
    return await skill_gap_analysis(
        job_id=job_id,
        candidate_id=candidate_id,
        resume_type=resume_type,
        resume_id=resume_id,
        resume_filename=resume_filename
    )


@app.post("/api/course-catalog/sync")
async def sync_course_catalog(
    source_urls: Optional[str] = Form(None),
    source_files: Optional[str] = Form(None),
):
    """
    Sync local course catalog (from JSON/CSV sources) and rebuild FAISS index.
    """
    try:
        urls = [u.strip() for u in (source_urls or "").split(",") if u.strip()] or None
        files = [f.strip() for f in (source_files or "").split(",") if f.strip()] or None

        payload = sync_catalog(
            output_path=course_recommender.catalog_path,
            source_urls=urls,
            source_files=files,
        )
        course_recommender.refresh_from_disk(force_rebuild=True)

        return {
            "success": True,
            "message": "Course catalog synced and vector index rebuilt.",
            "catalog_path": str(course_recommender.catalog_path),
            "course_count": payload.get("course_count", 0),
            "sources": payload.get("sources", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

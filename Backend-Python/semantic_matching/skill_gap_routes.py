# Backend-Python/semantic_matching/skill_gap_routes.py
from flask import Blueprint, request, jsonify
from core.skill_gap_analyzer import SkillGapAnalyzer
from core.database_helper import DatabaseHelper
from core.extractor import extract_text, extract_skills
import tempfile
import os

skill_gap_bp = Blueprint('skill_gap', __name__)
db_helper = DatabaseHelper()
skill_analyzer = SkillGapAnalyzer()

@skill_gap_bp.route('/api/skill-gap-analysis/<job_id>', methods=['POST'])
def analyze_skill_gap(job_id):
    """Analyze skill gap between candidate's resume and job description"""
    try:
        candidate_id = request.form.get('candidate_id')
        if not candidate_id:
            return jsonify({"success": False, "message": "Candidate ID is required"}), 400
        
        # 1. Get candidate's latest resume
        resume_filename = db_helper.get_candidate_resume(candidate_id)
        if not resume_filename:
            return jsonify({"success": False, "message": "No resume found for candidate"}), 404
        
        # 2. Get job description
        job_details = db_helper.get_job_details(job_id)
        if not job_details:
            return jsonify({"success": False, "message": "Job not found"}), 404
        
        # 3. Extract resume text
        uploads_dir = os.path.join(os.path.dirname(__file__), "..", "..", "Backend-PHP", "uploads")
        resume_path = os.path.join(uploads_dir, resume_filename)
        
        if not os.path.exists(resume_path):
            return jsonify({"success": False, "message": "Resume file not found"}), 404
        
        resume_text, _ = extract_text(resume_path)
        
        # 4. Extract skills from resume and JD
        resume_skills = skill_analyzer.extract_skills_dynamically(resume_text)
        jd_skills = skill_analyzer.extract_skills_dynamically(job_details['description'])
        
        # 5. Find missing skills
        skill_gap = skill_analyzer.find_missing_skills(resume_skills, jd_skills)
        
        # 6. Get course recommendations for missing skills
        course_recommendations = {}
        if skill_gap["missing_skills"]:
            course_recommendations = skill_analyzer.get_course_recommendations(
                skill_gap["missing_skills"],
                sources=["youtube", "google", "free"]
            )
        
        # 7. Generate learning path
        learning_path = skill_analyzer.generate_learning_path(
            skill_gap["missing_skills"],
            time_available="1 month"
        )
        
        # 8. Prepare response
        response = {
            "success": True,
            "job_id": job_id,
            "job_title": job_details['title'],
            "resume_skills_count": len(resume_skills),
            "jd_skills_count": len(jd_skills),
            "missing_skills": skill_gap["missing_skills"],
            "missing_skills_count": skill_gap["missing_count"],
            "matching_skills": skill_gap["matching_skills"],
            "matching_skills_count": skill_gap["matching_count"],
            "course_recommendations": course_recommendations,
            "course_count": sum(len(recs.get('youtube_videos', [])) + len(recs.get('online_courses', [])) 
                              for recs in course_recommendations.values()),
            "learning_path": learning_path
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Skill gap analysis error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
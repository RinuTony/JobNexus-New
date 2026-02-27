# app.py
import streamlit as st
import os
from core.extractor import extract_text, extract_skills
from core.matcher import ResumeMatcher

st.set_page_config(page_title="Resume Matcher", layout="wide")
matcher = ResumeMatcher()

st.title("📄 Resume-Job Description Matcher")

# Upload resumes
uploaded_files = st.file_uploader(
    "Upload resumes (PDF/TXT)",
    type=["pdf", "txt"],
    accept_multiple_files=True
)

# Job description
st.subheader("🎯 Job Description")
jd_text = st.text_area("Paste job description here", height=200)

if uploaded_files and jd_text:
    st.subheader("📊 Results")
    
    resumes_data = []
    
    # Process each resume
    for file in uploaded_files:
        # Save temporarily
        temp_dir = "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, file.name)
        
        with open(temp_path, "wb") as f:
            f.write(file.getbuffer())
        
        # Extract text and skills
        resume_text, _ = extract_text(temp_path)
        skills = extract_skills(resume_text)
        
        resumes_data.append({
            "id": file.name,
            "text": resume_text,
            "skills": skills
        })
        
        os.remove(temp_path)
    
    # Rank resumes
    ranked = matcher.rank_resumes(resumes_data, jd_text)
    
    # Display results
    cols = st.columns(3)
    col_titles = ["🥇 Top Matches", "🥈 Good Matches", "🥉 Others"]
    
    for i, (col, title) in enumerate(zip(cols, col_titles)):
        col.subheader(title)
        
        start_idx = i * (len(ranked) // 3)
        end_idx = start_idx + (len(ranked) // 3) if i < 2 else len(ranked)
        
        for resume in ranked[start_idx:end_idx]:
            with col.expander(f"{resume['id']} - Score: {resume['similarity_score']:.3f}"):
                st.write(f"**Top Skills:** {', '.join(resume['skills'][:5])}")
                st.write(f"**Preview:** {resume['text'][:200]}...")
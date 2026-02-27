# core/database_helper.py
import mysql.connector
from mysql.connector import Error
from typing import Optional, Dict, Any, List
import os
import json
from dotenv import load_dotenv

load_dotenv()

class DatabaseHelper:
    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        # Keep Python backend defaults aligned with local PHP/XAMPP config.
        self.database = os.getenv("DB_NAME", "job_nexus")
        self.user = os.getenv("DB_USER", "root")
        self.password = os.getenv("DB_PASSWORD", "")
        self.port = int(os.getenv("DB_PORT", 3306))
        
    def get_connection(self):
        """Create and return a database connection"""
        try:
            connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port
            )
            return connection
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return None
    
    def get_job_description(self, job_id: str) -> Optional[str]:
        """Fetch job description from database by job ID"""
        connection = self.get_connection()
        if not connection:
            return None
            
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT title, description 
                FROM jobs 
                WHERE id = %s
            """
            cursor.execute(query, (job_id,))
            result = cursor.fetchone()
            
            if result:
                # Combine title and description for better matching
                return f"{result['title']}\n\n{result['description']}"
            return None
            
        except Error as e:
            print(f"Error fetching job description: {e}")
            return None
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_candidate_resume(self, candidate_id: str) -> Optional[str]:
        """Fetch candidate's latest resume from database"""
        connection = self.get_connection()
        if not connection:
            return None
            
        try:
            cursor = connection.cursor(dictionary=True)
            # Prefer standalone uploads, fall back to applications
            query_uploads = """
                SELECT resume_filename
                FROM candidate_resumes
                WHERE candidate_id = %s
                ORDER BY uploaded_at DESC
                LIMIT 1
            """
            cursor.execute(query_uploads, (candidate_id,))
            result = cursor.fetchone()
            if result and result.get('resume_filename'):
                return result['resume_filename']

            query_apps = """
                SELECT resume_filename 
                FROM applications 
                WHERE candidate_id = %s 
                ORDER BY applied_at DESC 
                LIMIT 1
            """
            cursor.execute(query_apps, (candidate_id,))
            result = cursor.fetchone()
            if result and result.get('resume_filename'):
                return result['resume_filename']
            return None
            
        except Error as e:
            print(f"Error fetching candidate resume: {e}")
            return None
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_job_details(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get complete job details including recruiter info"""
        connection = self.get_connection()
        if not connection:
            return None
            
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT 
                    j.id,
                    j.title,
                    j.description,
                    j.required_skills,
                    j.created_at,
                    u.email AS recruiter_email
                FROM jobs j
                JOIN users u ON j.recruiter_id = u.id
                WHERE j.id = %s
            """
            cursor.execute(query, (job_id,))
            result = cursor.fetchone()
            return result
            
        except Error as e:
            print(f"Error fetching job details: {e}")
            return None
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def candidate_has_uploaded_resume(self, candidate_id: str, resume_filename: str) -> bool:
        """Verify that a resume file belongs to the candidate's applications."""
        connection = self.get_connection()
        if not connection:
            return False

        try:
            cursor = connection.cursor(dictionary=True)
            query_uploads = """
                SELECT 1
                FROM candidate_resumes
                WHERE candidate_id = %s AND resume_filename = %s
                LIMIT 1
            """
            cursor.execute(query_uploads, (candidate_id, resume_filename))
            result = cursor.fetchone()
            if result:
                return True

            query_apps = """
                SELECT 1
                FROM applications
                WHERE candidate_id = %s AND resume_filename = %s
                LIMIT 1
            """
            cursor.execute(query_apps, (candidate_id, resume_filename))
            result = cursor.fetchone()
            return bool(result)
        except Error as e:
            print(f"Error verifying candidate resume: {e}")
            return False
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def create_interview_session(
        self,
        candidate_id: str,
        job_id: str,
        total_questions: int,
        resume_text: str,
        jd_text: str,
    ) -> Optional[int]:
        """Create a new interview session and return its ID."""
        connection = self.get_connection()
        if not connection:
            return None

        try:
            cursor = connection.cursor()
            query = """
                INSERT INTO interview_sessions
                    (candidate_id, job_id, status, total_questions, asked_count, resume_text, jd_text)
                VALUES
                    (%s, %s, 'active', %s, 0, %s, %s)
            """
            cursor.execute(query, (candidate_id, job_id, total_questions, resume_text, jd_text))
            connection.commit()
            return cursor.lastrowid
        except Error as e:
            print(f"Error creating interview session: {e}")
            return None
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def add_interview_questions(
        self,
        session_id: int,
        questions: List[Dict[str, Any]],
    ) -> bool:
        """Insert interview questions for a session."""
        connection = self.get_connection()
        if not connection:
            return False

        try:
            cursor = connection.cursor()
            query = """
                INSERT INTO interview_questions
                    (session_id, question_text, question_audio_base64, question_audio_mime, order_index)
                VALUES
                    (%s, %s, %s, %s, %s)
            """
            rows = []
            for idx, q in enumerate(questions):
                rows.append(
                    (
                        session_id,
                        q.get("text", ""),
                        q.get("audio_base64"),
                        q.get("audio_mime"),
                        idx,
                    )
                )
            cursor.executemany(query, rows)
            connection.commit()
            return True
        except Error as e:
            print(f"Error inserting interview questions: {e}")
            return False
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def get_next_interview_question(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Fetch next unasked question and mark it asked."""
        connection = self.get_connection()
        if not connection:
            return None

        try:
            cursor = connection.cursor(dictionary=True)
            select_query = """
                SELECT id, question_text, question_audio_base64, question_audio_mime
                FROM interview_questions
                WHERE session_id = %s AND asked = 0
                ORDER BY order_index ASC
                LIMIT 1
            """
            cursor.execute(select_query, (session_id,))
            question = cursor.fetchone()
            if not question:
                return None

            update_query = """
                UPDATE interview_questions
                SET asked = 1, asked_at = NOW()
                WHERE id = %s
            """
            cursor.execute(update_query, (question["id"],))

            increment_query = """
                UPDATE interview_sessions
                SET asked_count = asked_count + 1, updated_at = NOW()
                WHERE id = %s
            """
            cursor.execute(increment_query, (session_id,))
            connection.commit()

            return question
        except Error as e:
            print(f"Error fetching next interview question: {e}")
            return None
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def get_interview_question(self, question_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a specific interview question."""
        connection = self.get_connection()
        if not connection:
            return None

        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT id, session_id, question_text, question_audio_base64, question_audio_mime
                FROM interview_questions
                WHERE id = %s
            """
            cursor.execute(query, (question_id,))
            return cursor.fetchone()
        except Error as e:
            print(f"Error fetching interview question: {e}")
            return None
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def save_interview_answer(
        self,
        session_id: int,
        question_id: int,
        answer_text: str,
        answer_audio_base64: Optional[str],
        feedback_json: Dict[str, Any],
        feedback_audio_base64: Optional[str],
        score: Optional[int],
    ) -> bool:
        """Save an interview answer and feedback."""
        connection = self.get_connection()
        if not connection:
            return False

        try:
            cursor = connection.cursor()
            query = """
                INSERT INTO interview_answers
                    (session_id, question_id, answer_text, answer_audio_base64, feedback_json, feedback_audio_base64, score)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(
                query,
                (
                    session_id,
                    question_id,
                    answer_text,
                    answer_audio_base64,
                    json.dumps(feedback_json),
                    feedback_audio_base64,
                    score,
                ),
            )
            connection.commit()
            return True
        except Error as e:
            print(f"Error saving interview answer: {e}")
            return False
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def update_interview_session_status(self, session_id: int, status: str) -> bool:
        """Update the status of an interview session."""
        connection = self.get_connection()
        if not connection:
            return False

        try:
            cursor = connection.cursor()
            query = """
                UPDATE interview_sessions
                SET status = %s, updated_at = NOW()
                WHERE id = %s
            """
            cursor.execute(query, (status, session_id))
            connection.commit()
            return True
        except Error as e:
            print(f"Error updating interview session status: {e}")
            return False
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def get_interview_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Fetch an interview session by ID."""
        connection = self.get_connection()
        if not connection:
            return None

        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT id, candidate_id, job_id, status, total_questions, asked_count, resume_text, jd_text
                FROM interview_sessions
                WHERE id = %s
            """
            cursor.execute(query, (session_id,))
            return cursor.fetchone()
        except Error as e:
            print(f"Error fetching interview session: {e}")
            return None
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def get_latest_active_session(self, candidate_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        """Fetch the latest active/stopped session for a candidate and job."""
        connection = self.get_connection()
        if not connection:
            return None

        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT id, candidate_id, job_id, status, total_questions, asked_count, resume_text, jd_text
                FROM interview_sessions
                WHERE candidate_id = %s AND job_id = %s AND status IN ('active', 'stopped')
                ORDER BY updated_at DESC
                LIMIT 1
            """
            cursor.execute(query, (candidate_id, job_id))
            return cursor.fetchone()
        except Error as e:
            print(f"Error fetching latest interview session: {e}")
            return None
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def get_interview_scores(self, session_id: int) -> List[int]:
        """Fetch non-null scores for a session."""
        connection = self.get_connection()
        if not connection:
            return []

        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT score
                FROM interview_answers
                WHERE session_id = %s AND score IS NOT NULL
            """
            cursor.execute(query, (session_id,))
            rows = cursor.fetchall() or []
            return [row["score"] for row in rows if row.get("score") is not None]
        except Error as e:
            print(f"Error fetching interview scores: {e}")
            return []
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def get_interview_average_score(self, session_id: int) -> float:
        """Compute average score for a session."""
        scores = self.get_interview_scores(session_id)
        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 2)

    def list_interview_sessions(self, candidate_id: str, job_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List interview sessions for a candidate (optionally filtered by job)."""
        connection = self.get_connection()
        if not connection:
            return []

        try:
            cursor = connection.cursor(dictionary=True)
            if job_id:
                query = """
                    SELECT id, candidate_id, job_id, status, total_questions, asked_count, created_at, updated_at
                    FROM interview_sessions
                    WHERE candidate_id = %s AND job_id = %s
                    ORDER BY created_at DESC
                """
                cursor.execute(query, (candidate_id, job_id))
            else:
                query = """
                    SELECT id, candidate_id, job_id, status, total_questions, asked_count, created_at, updated_at
                    FROM interview_sessions
                    WHERE candidate_id = %s
                    ORDER BY created_at DESC
                """
                cursor.execute(query, (candidate_id,))
            return cursor.fetchall() or []
        except Error as e:
            print(f"Error listing interview sessions: {e}")
            return []
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def get_interview_questions_for_session(self, session_id: int) -> List[Dict[str, Any]]:
        """Fetch all interview questions for a session."""
        connection = self.get_connection()
        if not connection:
            return []

        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT id, question_text, question_audio_base64, question_audio_mime, order_index, asked, asked_at
                FROM interview_questions
                WHERE session_id = %s
                ORDER BY order_index ASC
            """
            cursor.execute(query, (session_id,))
            return cursor.fetchall() or []
        except Error as e:
            print(f"Error fetching interview questions: {e}")
            return []
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def get_interview_answers_for_session(self, session_id: int) -> List[Dict[str, Any]]:
        """Fetch all interview answers for a session."""
        connection = self.get_connection()
        if not connection:
            return []

        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT question_id, answer_text, feedback_json, feedback_audio_base64, score, created_at
                FROM interview_answers
                WHERE session_id = %s
                ORDER BY id ASC
            """
            cursor.execute(query, (session_id,))
            return cursor.fetchall() or []
        except Error as e:
            print(f"Error fetching interview answers: {e}")
            return []
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

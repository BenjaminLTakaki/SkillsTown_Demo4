import os
import json
import re
from dotenv import load_dotenv
import sys
import traceback
import PyPDF2
import requests
from datetime import datetime  # Fixed: Use this instead of import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, current_app, Response
from flask_login import login_required, current_user, LoginManager, login_user, logout_user, UserMixin
from werkzeug.utils import secure_filename
from sqlalchemy import text
from jinja2 import ChoiceLoader, FileSystemLoader
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from local_config import NARRETEX_API_URL, check_environment, LOCAL_DATABASE_URL, DEVELOPMENT_MODE

load_dotenv()

# Production detection
is_production = os.environ.get('RENDER', False) or os.environ.get('FLASK_ENV') == 'production'

# API configurations
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent"
QUIZ_API_BASE_URL = os.environ.get('QUIZ_API_BASE_URL', 'http://localhost:8081')
QUIZ_API_ACCESS_TOKEN = os.environ.get('QUIZ_API_ACCESS_TOKEN', 'kJ9mP2vL8xQ5nR3tY7wZ6cB4dF2gH8jK9lM3nP5qR7sT2uV6wX8yZ9aB3cD5eF7gH2iJ4kL6mN8oP9qR2sT4uV6wX8yZ1aB3cD5eF7gH9iJ2kL')

def get_url_for(*args, **kwargs):
    url = url_for(*args, **kwargs)
    if is_production and not url.startswith('/skillstown'):
        url = f"/skillstown{url}"
    return url

# Import models after db is defined
from models import Company, Student, Category, ContentPage, Course, CourseContentPage, UserProfile, SkillsTownCourse, CourseDetail, CourseQuiz, CourseQuizAttempt, UserCourse, db

def get_quiz_api_headers():
    """Get headers for quiz API requests"""
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {QUIZ_API_ACCESS_TOKEN}'
    }

def generate_podcast_for_course(course_name, course_description):
    """
    Generate a podcast for a specific course using NarreteX API
    Uses the detailed course catalog for rich content
    """
    try:
        # Load the course catalog to get detailed information
        course_details = get_detailed_course_info(course_name)
        
        # Create comprehensive content from catalog data
        document_content = f"""
        COURSE: {course_name}
        
        DESCRIPTION: {course_description}
        
        DETAILED COURSE INFORMATION:
        {format_course_details(course_details)}
        
        EDUCATIONAL CONTEXT:
        This course is designed to provide comprehensive knowledge and practical skills.
        Students will gain hands-on experience through real-world projects and exercises.
        The curriculum follows industry best practices and includes the latest technologies and methodologies.
        """
        
        # Debug: Print the content being sent
        print("=" * 50)
        print("DEBUG: Course catalog content:")
        print(f"Length: {len(document_content)} characters")
        print("Content preview:")
        print(document_content[:300] + "...")
        print("=" * 50)
        
        # Call NarreteX instant podcast API
        response = requests.post(
            f"{NARRETEX_API_URL}/instant-podcast",
            json={
                "topic": course_name,
                "document": document_content
            },
            timeout=120
        )
        
        if response.status_code == 200:
            return response.content
        else:
            print(f"Podcast generation failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error generating podcast: {e}")
        return None

def get_detailed_course_info(course_name):
    """
    Get detailed course information from the course catalog
    """
    try:
        catalog_path = os.path.join(os.path.dirname(__file__), 'static', 'data', 'course_catalog.json')
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        
        # Search for the course in the catalog
        for category in catalog.get('categories', []):
            for course in category.get('courses', []):
                if course['name'].lower() == course_name.lower():
                    return course
        
        # If not found, return minimal info
        return {"name": course_name, "description": "Course information not available"}
        
    except Exception as e:
        print(f"Error loading course catalog: {e}")
        return {"name": course_name, "description": "Course information not available"}

def format_course_details(course_details):
    """
    Format course details into a comprehensive text description
    """
    if not course_details:
        return "Course details not available."
    
    formatted = f"Course: {course_details.get('name', 'Unknown')}\n\n"
    formatted += f"Description: {course_details.get('description', 'No description available')}\n\n"
    
    if 'duration' in course_details:
        formatted += f"Duration: {course_details['duration']}\n"
    
    if 'level' in course_details:
        formatted += f"Level: {course_details['level']}\n\n"
    
    if 'skills' in course_details and course_details['skills']:
        formatted += "Skills You'll Learn:\n"
        for skill in course_details['skills']:
            formatted += f"- {skill}\n"
        formatted += "\n"
    
    if 'projects' in course_details and course_details['projects']:
        formatted += "Projects You'll Build:\n"
        for project in course_details['projects']:
            formatted += f"- {project}\n"
        formatted += "\n"
    
    if 'career_paths' in course_details and course_details['career_paths']:
        formatted += "Career Opportunities:\n"
        for career in course_details['career_paths']:
            formatted += f"- {career}\n"
        formatted += "\n"
    
    return formatted

# Auth setup
def init_auth(app, get_url_for_func, get_stats_func):
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return Student.query.get(user_id)
    
    return db

# Fallback skill extraction
def extract_skills_fallback(cv_text):
    patterns = [
        r'\b(?:Python|Java|JavaScript|C\+\+|C#|PHP|Ruby|Swift|Kotlin|Go|Rust)\b',
        r'\b(?:HTML|CSS|React|Angular|Vue|Node\.js|Express|Django|Flask)\b',
        r'\b(?:SQL|MySQL|PostgreSQL|MongoDB|SQLite|Oracle|Redis)\b',
        r'\b(?:Git|Docker|Kubernetes|AWS|Azure|GCP|Jenkins|CI/CD)\b',
        r'\b(?:Machine Learning|AI|Data Science|Analytics|TensorFlow|PyTorch)\b',
        r'\b(?:Project Management|Agile|Scrum|Leadership|Communication)\b',
    ]
    skills = []
    for pat in patterns:
        for m in re.finditer(pat, cv_text, re.IGNORECASE):
            s = m.group().strip()
            if s not in skills:
                skills.append(s)
    return {
        "current_skills": skills,
        "skill_categories": {"technical": skills},
        "experience_level": "unknown",
        "learning_recommendations": ["Consider learning complementary technologies"],
        "career_paths": ["Continue developing in your current domain"]
    }

# Gemini-based analysis
def analyze_skills_with_gemini(cv_text, job_description=None):
    if not GEMINI_API_KEY:
        return extract_skills_fallback(cv_text)
    
    if job_description and job_description.strip():
        prompt = f"""
Analyze this CV and job description to extract skills and provide guidance.

CV TEXT:
{cv_text[:3000]}

JOB DESCRIPTION:
{job_description[:2000]}

Provide JSON with current_skills, job_requirements, skill_gaps, matching_skills,
learning_recommendations, career_advice, skill_categories, experience_level.
"""
    else:
        prompt = f"""
Analyze this CV to extract skills and provide recommendations.

CV TEXT:
{cv_text[:4000]}

Provide JSON with current_skills, skill_categories, experience_level,
learning_recommendations, career_paths.
"""
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}], 
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2000,
            "topP": 0.8
        }
    }
    
    try:
        res = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", 
            json=payload, 
            headers={"Content-Type": "application/json"}, 
            timeout=30
        )
        res.raise_for_status()
        cand = res.json().get('candidates', [])
        if not cand:
            return extract_skills_fallback(cv_text)
        
        txt = cand[0]['content']['parts'][0]['text'].strip()
        jm = re.search(r'```json\s*(\{.*?\})\s*```', txt, re.DOTALL) or re.search(r'\{.*\}', txt, re.DOTALL)
        js = jm.group(1) if jm else txt
        data = json.loads(js)
        return data if isinstance(data, dict) and 'current_skills' in data else extract_skills_fallback(cv_text)
    except Exception:
        return extract_skills_fallback(cv_text)

# App factory
def create_app(config_name=None):
    global is_production
    
    # Check environment in development mode
    if DEVELOPMENT_MODE:
        check_environment()
        is_production = False
    else:
        if config_name == 'production': 
            is_production = True
        elif config_name is not None: 
            is_production = False

    app = Flask(__name__)

    # Templates - Fixed path resolution
    tpl_dirs = [FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates'))]
    animewatchlist_path = os.path.join(os.path.dirname(__file__), '..', 'animewatchlist')
    if os.path.isdir(animewatchlist_path): 
        tpl_dirs.append(FileSystemLoader(os.path.join(animewatchlist_path, 'templates')))
    app.jinja_loader = ChoiceLoader(tpl_dirs)

    # Config
    app.config.update({
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev-secret'),
        'UPLOAD_FOLDER': os.path.join(os.path.dirname(__file__), 'uploads'),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'MAX_CONTENT_LENGTH': 10 * 1024 * 1024,
    })
    
    if DEVELOPMENT_MODE and not os.environ.get('DATABASE_URL'):
        app.config['SQLALCHEMY_DATABASE_URI'] = LOCAL_DATABASE_URL
    else:
        db_url = os.environ.get('DATABASE_URL')
        if db_url and db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://')
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///skillstown.db'

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)

    @app.context_processor
    def inject(): 
        return {
            'current_year': datetime.now().year,  # Fixed: Use datetime.now() instead of datetime.now()
            'get_url_for': get_url_for
        }

    @app.template_filter('from_json')
    def from_json_filter(json_str):
        try:
            return json.loads(json_str) if json_str else {}
        except:
            return {}

    @app.template_filter('urlencode')
    def urlencode_filter(s):
        from urllib.parse import quote
        return quote(str(s)) if s else ''

    # Stats function
    def get_skillstown_stats(uid):
        try:
            total = UserCourse.query.filter_by(user_id=uid).count()
            enrolled = UserCourse.query.filter_by(user_id=uid, status='enrolled').count()
            in_p = UserCourse.query.filter_by(user_id=uid, status='in_progress').count()
            comp = UserCourse.query.filter_by(user_id=uid, status='completed').count()
            pct = (comp/total*100) if total else 0
            return {'total':total,'enrolled':enrolled,'in_progress':in_p,'completed':comp,'completion_percentage':pct}
        except:
            return {'total':0,'enrolled':0,'in_progress':0,'completed':0,'completion_percentage':0}    # Initialize auth
    init_auth(app, get_url_for, get_skillstown_stats)

    with app.app_context(): 
        db.create_all()

    # Helpers
    COURSE_CATALOG_PATH = os.path.join(os.path.dirname(__file__), 'static', 'data', 'course_catalog.json')
    
    def load_course_catalog():
        try:
            with open(COURSE_CATALOG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'categories': []}
    
    def calc_score(q, t, d): 
        return sum(3 for w in q.split() if w in t.lower()) + sum(1 for w in q.split() if w in d.lower())
    
    def search_courses(query, catalog=None):
        if not catalog: 
            catalog = load_course_catalog()
        q = query.lower().strip()
        res = []
        for cat in catalog.get('categories', []):
            for c in cat.get('courses', []):
                sc = calc_score(q, c['name'], c.get('description', ''))
                if sc > 0: 
                    res.append({
                        'category': cat['name'],
                        'course': c['name'],
                        'description': c.get('description', ''),
                        'relevance_score': sc
                    })
        return sorted(res, key=lambda x: x['relevance_score'], reverse=True)
    
    def allowed_file(fn): 
        return '.' in fn and fn.rsplit('.', 1)[1].lower() == 'pdf'
    
    def extract_text_from_pdf(fp):
        txt = ''
        try:
            with open(fp, 'rb') as f:
                r = PyPDF2.PdfReader(f)
                for p in r.pages:
                    try: 
                        txt += p.extract_text() or ''
                    except: 
                        continue
        except Exception as e:
            print(f"Error reading PDF: {e}")
        return txt.strip()

    # Helper functions for quiz recommendations
    def generate_course_recommendations_from_quiz(attempt, api_attempts):
        """Generate course recommendations based on quiz performance"""
        score = attempt.score or 0
        catalog = load_course_catalog()
        
        recommendations = {
            'remedial_courses': [],
            'next_courses': [],
            'advanced_courses': [],
            'specific_advice': ''
        }
        
        # Determine recommendations based on score
        if score < 60:
            # Low score - recommend foundational courses
            recommendations['specific_advice'] = "Focus on strengthening your foundation in this subject area. The recommended courses will help you build core competencies."
            recommendations['remedial_courses'] = get_foundational_courses(catalog)
        elif score < 80:
            # Medium score - recommend intermediate courses
            recommendations['specific_advice'] = "You have a good foundation! Continue building your skills with these intermediate courses."
            recommendations['next_courses'] = get_intermediate_courses(catalog)
        else:
            # High score - recommend advanced courses
            recommendations['specific_advice'] = "Excellent work! You're ready for advanced topics that will set you apart."
            recommendations['advanced_courses'] = get_advanced_courses(catalog)
        
        return recommendations

    def generate_basic_recommendations_from_score(score):
        """Generate basic recommendations when API is unavailable"""
        catalog = load_course_catalog()
        
        recommendations = {
            'remedial_courses': [],
            'next_courses': [],
            'advanced_courses': [],
            'specific_advice': ''
        }
        
        if score < 60:
            recommendations['specific_advice'] = "Focus on foundational skills to improve your understanding."
            recommendations['remedial_courses'] = get_foundational_courses(catalog)
        elif score < 80:
            recommendations['specific_advice'] = "Great progress! Continue with intermediate level courses."
            recommendations['next_courses'] = get_intermediate_courses(catalog)
        else:
            recommendations['specific_advice'] = "Excellent! You're ready for advanced challenges."
            recommendations['advanced_courses'] = get_advanced_courses(catalog)
        
        return recommendations

    def get_foundational_courses(catalog):
        """Get beginner/foundational courses from catalog"""
        courses = []
        for category in catalog.get('categories', []):
            for course in category.get('courses', []):
                if course.get('level', '').lower() in ['beginner', 'basic', 'foundational']:
                    courses.append({
                        'name': course['name'],
                        'category': category['name'],
                        'reason': f"Strengthen foundation in {category['name'].lower()}"
                    })
                    if len(courses) >= 4:
                        break
            if len(courses) >= 4:
                break
        return courses

    def get_intermediate_courses(catalog):
        """Get intermediate courses from catalog"""
        courses = []
        for category in catalog.get('categories', []):
            for course in category.get('courses', []):
                if course.get('level', '').lower() in ['intermediate', 'medium']:
                    courses.append({
                        'name': course['name'],
                        'category': category['name'],
                        'reason': f"Build expertise in {category['name'].lower()}"
                    })
                    if len(courses) >= 4:
                        break
            if len(courses) >= 4:
                break
        return courses

    def get_advanced_courses(catalog):
        """Get advanced courses from catalog"""
        courses = []
        for category in catalog.get('categories', []):
            for course in category.get('courses', []):
                if course.get('level', '').lower() in ['advanced', 'expert', 'professional']:
                    courses.append({
                        'name': course['name'],
                        'category': category['name'],
                        'reason': f"Master advanced {category['name'].lower()} concepts"
                    })
                    if len(courses) >= 4:
                        break
            if len(courses) >= 4:
                break
        return courses

    # Routes
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            
            user = Student.query.filter_by(email=email).first()
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                return redirect(get_url_for('index'))
            else:
                flash('Invalid email or password', 'error')
        
        return render_template('auth/login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            
            if Student.query.filter_by(email=email).first():
                flash('Email already exists', 'error')
                return render_template('auth/register.html')
            
            user = Student(
                name=name,
                email=email,
                username=email,
                password_hash=generate_password_hash(password)
            )
            db.session.add(user)
            db.session.commit()
            
            login_user(user)
            flash('Registration successful!', 'success')
            return redirect(get_url_for('index'))
        
        return render_template('auth/register.html')

    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(get_url_for('index'))

    # QUIZ ROUTES - NEW INTEGRATION
    @app.route('/course/<int:course_id>/generate-quiz', methods=['POST'])
    @login_required
    def generate_quiz(course_id):
        """Generate a new quiz for a course"""
        try:
            # Get the course from UserCourse table
            course = UserCourse.query.filter_by(id=course_id, user_id=current_user.id).first()
            if not course:
                return jsonify({
                    'success': False,
                    'error': 'Course not found or you do not have access to it'
                }), 404
            
            # Get or create quiz UUID for the user
            quiz_user_uuid = current_user.get_quiz_uuid()
            
            # Get course details to send to quiz API
            course_details = CourseDetail.query.filter_by(user_course_id=course_id).first()
            description = course_details.description if course_details else f"Learn {course.course_name} with practical examples and real-world applications."
            
            # Get course info from catalog for more details
            catalog_info = get_detailed_course_info(course.course_name)
            
            # Prepare the request payload for quiz API
            quiz_payload = {
                "user_id": quiz_user_uuid,
                "course": {
                    "name": course.course_name,
                    "description": description,
                    "duration": catalog_info.get('duration', '8 weeks'),
                    "level": catalog_info.get('level', 'Intermediate'),
                    "skills": catalog_info.get('skills', []),
                    "projects": catalog_info.get('projects', []),
                    "career_paths": catalog_info.get('career_paths', [])
                }
            }
            
            print(f"[DEBUG] Sending quiz payload: {quiz_payload}")
            
            # Call the quiz API to create quiz
            response = requests.post(
                f"{QUIZ_API_BASE_URL}/quiz/create-ai-from-course",
                json=quiz_payload,
                headers=get_quiz_api_headers(),
                timeout=30
            )
            
            print(f"[DEBUG] Quiz API response: {response.status_code} - {response.text}")
            
            if response.status_code == 201:  # Note: API returns 201, not 200
                quiz_data = response.json()
                
                # Save quiz info to our database
                course_quiz = CourseQuiz(
                    user_course_id=course_id,
                    quiz_api_id=quiz_data['quizId'],
                    quiz_title=quiz_data['title'],
                    quiz_description=quiz_data['description'],
                    questions_count=quiz_data['questionsCount']
                )
                db.session.add(course_quiz)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'quiz_id': quiz_data['quizId'],
                    'title': quiz_data['title'],
                    'description': quiz_data['description'],
                    'questions_count': quiz_data['questionsCount'],
                    'message': 'Quiz generated successfully!'
                })
            else:
                print(f"Quiz API error: {response.status_code} - {response.text}")
                return jsonify({
                    'success': False,
                    'error': f'Quiz API returned status {response.status_code}: {response.text}'
                }), 500
                    
        except Exception as e:
            print(f"Error generating quiz: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Internal error: {str(e)}'
            }), 500

    @app.route('/quiz/<quiz_id>/details')
    @login_required
    def get_quiz_details(quiz_id):
        """Get quiz details for taking the quiz"""
        try:
            # Verify user owns this quiz
            course_quiz = CourseQuiz.query.filter_by(quiz_api_id=quiz_id).first()
            if not course_quiz:
                return jsonify({'error': 'Quiz not found'}), 404
                
            user_course = UserCourse.query.filter_by(
                id=course_quiz.user_course_id, 
                user_id=current_user.id
            ).first()
            if not user_course:
                return jsonify({'error': 'Access denied'}), 403
            
            # Get quiz details from API
            response = requests.get(
                f"{QUIZ_API_BASE_URL}/quiz/{quiz_id}/from-course",
                headers=get_quiz_api_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                return jsonify(response.json())
            else:
                return jsonify({'error': f'Quiz API error: {response.status_code}'}), 500
                    
        except Exception as e:
            print(f"Error getting quiz details: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/quiz/<quiz_id>/start', methods=['POST'])
    @login_required  
    def start_quiz_attempt(quiz_id):
        """Start a new quiz attempt"""
        try:
            # Verify user owns this quiz
            course_quiz = CourseQuiz.query.filter_by(quiz_api_id=quiz_id).first()
            if not course_quiz:
                return jsonify({'error': 'Quiz not found'}), 404
                
            user_course = UserCourse.query.filter_by(
                id=course_quiz.user_course_id,
                user_id=current_user.id
            ).first()
            if not user_course:
                return jsonify({'error': 'Access denied'}), 403
            
            # Start attempt via API
            response = requests.post(
                f"{QUIZ_API_BASE_URL}/quiz/{quiz_id}/attempt-from-course",
                headers=get_quiz_api_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                attempt_data = response.json()
                
                # Save attempt to our database
                quiz_attempt = CourseQuizAttempt(
                    user_id=current_user.id,
                    course_quiz_id=course_quiz.id,
                    attempt_api_id=attempt_data['attemptId']
                )
                db.session.add(quiz_attempt)
                db.session.commit()
                
                return jsonify(attempt_data)
            else:
                return jsonify({'error': f'Quiz API error: {response.status_code}'}), 500
                    
        except Exception as e:
            print(f"Error starting quiz attempt: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/quiz/attempt/<attempt_id>/complete', methods=['POST'])
    @login_required
    def complete_quiz_attempt(attempt_id):
        """Complete a quiz attempt with user answers"""
        try:
            # Get the attempt from our database
            quiz_attempt = CourseQuizAttempt.query.filter_by(
                attempt_api_id=attempt_id,
                user_id=current_user.id
            ).first()
            if not quiz_attempt:
                return jsonify({'error': 'Quiz attempt not found'}), 404
            
            # Get user answers from request
            user_answers = request.json
            
            # Submit answers to quiz API
            response = requests.post(
                f"{QUIZ_API_BASE_URL}/quiz/attempt/{attempt_id}/complete-from-course",
                json=user_answers,
                headers=get_quiz_api_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                result_data = response.json()
                
                # Update our attempt record with results
                if 'results' in result_data:
                    results = result_data['results']
                    quiz_attempt.score = results.get('score', 0)
                    quiz_attempt.total_questions = results.get('totalQuestions', 0)
                    quiz_attempt.correct_answers = results.get('correct', 0)
                    quiz_attempt.feedback_strengths = results.get('strengths', '')
                    quiz_attempt.feedback_improvements = results.get('improvements', '')
                    quiz_attempt.user_answers = json.dumps(user_answers)
                    quiz_attempt.completed_at = datetime.utcnow()
                    
                    db.session.commit()
                
                return jsonify(result_data)
            else:
                return jsonify({'error': f'Quiz API error: {response.status_code}'}), 500
                    
        except Exception as e:
            print(f"Error completing quiz attempt: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/course/<int:course_id>/quiz-attempts')
    @login_required
    def get_course_quiz_attempts(course_id):
        """Get all quiz attempts for a course"""
        try:
            # Verify user owns this course
            course = UserCourse.query.filter_by(id=course_id, user_id=current_user.id).first()
            if not course:
                return jsonify({'error': 'Course not found'}), 404
            
            # Get all quiz attempts for this course
            quiz_attempts = db.session.query(CourseQuizAttempt).join(
                CourseQuiz, CourseQuizAttempt.course_quiz_id == CourseQuiz.id
            ).filter(
                CourseQuiz.user_course_id == course_id,
                CourseQuizAttempt.user_id == current_user.id
            ).order_by(CourseQuizAttempt.completed_at.desc()).all()
            
            attempts_data = []
            for attempt in quiz_attempts:
                attempts_data.append({
                    'id': attempt.id,
                    'attempt_api_id': attempt.attempt_api_id,
                    'score': attempt.score,
                    'total_questions': attempt.total_questions,
                    'correct_answers': attempt.correct_answers,
                    'feedback_strengths': attempt.feedback_strengths,
                    'feedback_improvements': attempt.feedback_improvements,
                    'completed_at': attempt.completed_at.isoformat() if attempt.completed_at else None,
                    'quiz_title': attempt.course_quiz.quiz_title
                })
            
            return jsonify({'attempts': attempts_data})
            
        except Exception as e:
            print(f"Error getting quiz attempts: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/course/<int:course_id>/quiz-recommendations')
    @login_required
    def get_quiz_recommendations(course_id):
        """Get AI-generated course recommendations based on quiz performance"""
        try:
            # Get the latest quiz attempt for this course
            latest_attempt = db.session.query(CourseQuizAttempt).join(
                CourseQuiz, CourseQuizAttempt.course_quiz_id == CourseQuiz.id
            ).filter(
                CourseQuiz.user_course_id == course_id,
                CourseQuizAttempt.user_id == current_user.id,
                CourseQuizAttempt.score.isnot(None)
            ).order_by(CourseQuizAttempt.completed_at.desc()).first()
            
            if not latest_attempt:
                return jsonify({'error': 'No completed quiz attempts found'}), 404
            
            # Get user's quiz UUID for API calls
            quiz_user_uuid = current_user.get_quiz_uuid()
            
            # Call quiz API to get detailed results and recommendations
            try:
                response = requests.get(
                    f"{QUIZ_API_BASE_URL}/user/{quiz_user_uuid}/quiz-attempts-from-course",
                    headers=get_quiz_api_headers(),
                    timeout=30
                )
                
                if response.status_code == 200:
                    attempts_data = response.json()
                    
                    # Find the matching attempt and generate recommendations
                    recommendations = generate_course_recommendations_from_quiz(
                        latest_attempt, attempts_data.get('attempts', [])
                    )
                    
                    return jsonify({
                        'latest_attempt': {
                            'score': latest_attempt.score,
                            'feedback_strengths': latest_attempt.feedback_strengths,
                            'feedback_improvements': latest_attempt.feedback_improvements,
                            'completed_at': latest_attempt.completed_at.isoformat() if latest_attempt.completed_at else None
                        },
                        'recommendations': recommendations
                    })
                else:
                    # Fallback to basic recommendations if API fails
                    recommendations = generate_basic_recommendations_from_score(latest_attempt.score)
                    return jsonify({
                        'latest_attempt': {
                            'score': latest_attempt.score,
                            'feedback_strengths': latest_attempt.feedback_strengths,
                            'feedback_improvements': latest_attempt.feedback_improvements,
                            'completed_at': latest_attempt.completed_at.isoformat() if latest_attempt.completed_at else None
                        },
                        'recommendations': recommendations
                    })
            except requests.RequestException as e:
                print(f"Quiz API request failed: {e}")
                # Fallback to basic recommendations
                recommendations = generate_basic_recommendations_from_score(latest_attempt.score)
                return jsonify({
                    'latest_attempt': {
                        'score': latest_attempt.score,
                        'feedback_strengths': latest_attempt.feedback_strengths,
                        'feedback_improvements': latest_attempt.feedback_improvements,
                        'completed_at': latest_attempt.completed_at.isoformat() if latest_attempt.completed_at else None
                    },
                    'recommendations': recommendations
                })
                    
        except Exception as e:
            print(f"Error getting quiz recommendations: {e}")
            return jsonify({'error': str(e)}), 500

    # PODCAST ROUTES
    @app.route('/course/<int:course_id>/generate-podcast', methods=['POST'])
    @login_required
    def generate_course_podcast(course_id):
        course = UserCourse.query.filter_by(id=course_id, user_id=current_user.id).first_or_404()
        
        try:
            print(f"=== PODCAST GENERATION DEBUG ===")
            print(f"Course: {course.course_name}")
            print(f"Course ID: {course_id}")
            
            # Get course details for more context
            course_details = CourseDetail.query.filter_by(user_course_id=course_id).first()
            description = course_details.description if course_details else f"Learn {course.course_name} with practical examples and real-world applications."
            
            print(f"Description length: {len(description)} chars")
            print(f"Description preview: {description[:100]}...")
            # Generate podcast
            print("Calling generate_podcast_for_course...")
            audio_data = generate_podcast_for_course(course.course_name, description)
            
            print(f"Received audio_data: {type(audio_data)}")
            if audio_data:
                print(f"Audio data size: {len(audio_data)} bytes")
                print(f"Audio data preview: {audio_data[:20] if len(audio_data) >= 20 else audio_data}")
                
                # Check if it looks like WAV data
                if audio_data.startswith(b'RIFF') and b'WAVE' in audio_data[:12]:
                    print("✅ Audio data appears to be valid WAV format")
                else:
                    print("❌ WARNING: Audio data does not appear to be WAV format")
                    print(f"First 20 bytes: {audio_data[:20]}")
            else:
                print("❌ ERROR: audio_data is None or empty")
                
            if audio_data and len(audio_data) > 0:
                # Store the audio data in session or database for streaming
                # For now, we'll return it directly for streaming (no attachment header)
                print("Returning successful audio response for streaming")
                return Response(
                    audio_data,
                    mimetype='audio/wav',
                    headers={
                        'Content-Length': str(len(audio_data)),
                        'Accept-Ranges': 'bytes',
                        'Cache-Control': 'no-cache'
                    }
                )
            else:
                print("❌ ERROR: Empty or invalid audio data")
                flash('Failed to generate podcast - empty audio data', 'error')
                return redirect(get_url_for('course_detail', course_id=course_id))
        except Exception as e:
            print(f"❌ EXCEPTION in podcast generation: {e}")
            traceback.print_exc()
            flash(f'Error generating podcast: {str(e)}', 'error')
            return redirect(get_url_for('course_detail', course_id=course_id))

    @app.route('/test-podcast')
    @login_required
    def test_podcast():
        """Test route for podcast generation"""
        try:
            test_audio = generate_podcast_for_course(
                "Python Programming", 
                "Learn Python from basics to advanced concepts including data structures, algorithms, and web development."
            )
            
            if test_audio:
                return Response(
                    test_audio,
                    mimetype='audio/wav',
                    headers={'Content-Disposition': 'attachment; filename="test_podcast.wav"'}
                )
            else:
                return "Podcast generation failed", 500
                
        except Exception as e:
            return f"Error: {e}", 500

    # CV ANALYSIS ROUTES
    @app.route('/assessment')
    @login_required
    def assessment():
        return render_template('assessment/assessment.html')

    @app.route('/assessment', methods=['POST'])
    @login_required
    def upload_cv():
        if 'cv_file' not in request.files:
            flash('Please select a file', 'error')
            return redirect(get_url_for('assessment'))
        
        file = request.files['cv_file']
        job_description = request.form.get('job_description', '').strip()
        
        if file.filename == '':
            flash('Please select a file', 'error')
            return redirect(get_url_for('assessment'))
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                cv_text = extract_text_from_pdf(filepath)
                os.remove(filepath)  # Clean up uploaded file
                
                if not cv_text.strip():
                    flash('Could not extract text from PDF. Please ensure it\'s not an image-only PDF.', 'error')
                    return redirect(get_url_for('assessment'))
                
                # Analyze with Gemini
                analysis = analyze_skills_with_gemini(cv_text, job_description)
                skills = analysis.get('current_skills', [])
                
                # Save to database
                profile = UserProfile(
                    user_id=current_user.id,
                    cv_text=cv_text,
                    job_description=job_description if job_description else None,
                    skills=json.dumps(skills),
                    skill_analysis=json.dumps(analysis)
                )
                db.session.add(profile)
                db.session.commit()
                
                return redirect(get_url_for('results', profile_id=profile.id))
                
            except Exception as e:
                print(f"Error processing CV: {e}")
                flash('Error processing CV. Please try again.', 'error')
                return redirect(get_url_for('assessment'))
        
        flash('Invalid file format. Please upload a PDF file.', 'error')
        return redirect(get_url_for('assessment'))

    @app.route('/results/<int:profile_id>')
    @login_required
    def results(profile_id):
        profile = UserProfile.query.filter_by(id=profile_id, user_id=current_user.id).first_or_404()
        
        try:
            skills = json.loads(profile.skills) if profile.skills else []
            full_analysis = json.loads(profile.skill_analysis) if profile.skill_analysis else {}
        except:
            skills = []
            full_analysis = {}
        
        # Determine skill categories for recommendations
        has_programming_skills = any(skill.lower() in ['python', 'java', 'javascript', 'c++', 'c#'] for skill in skills)
        has_data_skills = any(skill.lower() in ['data science', 'machine learning', 'analytics', 'sql'] for skill in skills)
        has_web_skills = any(skill.lower() in ['html', 'css', 'react', 'angular', 'web development'] for skill in skills)
        has_devops_skills = any(skill.lower() in ['docker', 'kubernetes', 'aws', 'azure', 'devops'] for skill in skills)
        
        return render_template('assessment/results.html', 
                             profile=profile, 
                             skills=skills, 
                             full_analysis=full_analysis,
                             has_programming_skills=has_programming_skills,
                             has_data_skills=has_data_skills,
                             has_web_skills=has_web_skills,
                             has_devops_skills=has_devops_skills)

    # COURSE MANAGEMENT ROUTES
    @app.route('/search')
    def search():
        query = request.args.get('query', '')
        results = []
        if query:
            results = search_courses(query)
        return render_template('courses/search.html', query=query, results=results)

    @app.route('/enroll', methods=['POST'])
    @login_required
    def enroll_course():
        category = request.form.get('category')
        course = request.form.get('course')
        
        existing = UserCourse.query.filter_by(
            user_id=current_user.id, 
            course_name=course
        ).first()
        
        if existing:
            return jsonify({'success': False, 'message': 'Already enrolled in this course'})
        
        user_course = UserCourse(
            user_id=current_user.id,
            category=category,
            course_name=course,
            status='enrolled'
        )
        db.session.add(user_course)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Successfully enrolled!'})

    @app.route('/my-courses')
    @login_required
    def my_courses():
        courses = UserCourse.query.filter_by(user_id=current_user.id).order_by(UserCourse.created_at.desc()).all()
        stats = get_skillstown_stats(current_user.id)
        return render_template('courses/my_courses.html', courses=courses, stats=stats)

    @app.route('/course/<int:course_id>')
    @login_required
    def course_detail(course_id):
        course = UserCourse.query.filter_by(id=course_id, user_id=current_user.id).first_or_404()
        
        # Get or create course details
        course_details = CourseDetail.query.filter_by(user_course_id=course_id).first()
        if not course_details:
            # Create sample course details
            sample_materials = {
                "materials": [
                    {
                        "title": f"Introduction to {course.course_name}",
                        "type": "lesson",
                        "duration": "2 hours",
                        "topics": ["Fundamentals", "Getting Started", "Overview"],
                        "description": f"Learn the basics of {course.course_name} and get started with practical examples."
                    },
                    {
                        "title": f"Intermediate {course.course_name}",
                        "type": "lesson", 
                        "duration": "3 hours",
                        "topics": ["Advanced Concepts", "Best Practices", "Real-world Applications"],
                        "description": f"Dive deeper into {course.course_name} with advanced techniques and industry practices."
                    },
                    {
                        "title": f"{course.course_name} Project",
                        "type": "project",
                        "duration": "5 hours", 
                        "topics": ["Hands-on Practice", "Portfolio Building", "Implementation"],
                        "description": f"Build a complete project using {course.course_name} to demonstrate your skills."
                    }
                ]
            }
            
            course_details = CourseDetail(
                user_course_id=course_id,
                description=f"Learn {course.course_name} with hands-on projects and real-world applications. This comprehensive course covers everything from basics to advanced concepts.",
                progress_percentage=0,
                materials=json.dumps(sample_materials)
            )
            db.session.add(course_details)
            db.session.commit()
        
        # Parse materials
        try:
            materials = json.loads(course_details.materials) if course_details.materials else {"materials": []}
        except:
            materials = {"materials": []}
        
        return render_template('courses/course_detail.html', 
                             course=course, 
                             course_details=course_details,
                             materials=materials)

    @app.route('/course/<int:course_id>/update-status', methods=['POST'])
    @login_required
    def update_course_status(course_id):
        course = UserCourse.query.filter_by(id=course_id, user_id=current_user.id).first_or_404()
        new_status = request.form.get('status')
        
        if new_status in ['enrolled', 'in_progress', 'completed']:
            course.status = new_status
            if new_status == 'completed':
                # Update course details progress
                course_details = CourseDetail.query.filter_by(user_course_id=course_id).first()
                if course_details:
                    course_details.progress_percentage = 100
                    course_details.completed_at = datetime.utcnow()  # Fixed: Use datetime.utcnow()
            
            db.session.commit()
            flash(f'Course status updated to {new_status}!', 'success')
        
        return redirect(get_url_for('course_detail', course_id=course_id))

    @app.route('/profile')
    @login_required
    def skillstown_user_profile():
        stats = get_skillstown_stats(current_user.id)
        recent_courses = UserCourse.query.filter_by(user_id=current_user.id).order_by(UserCourse.created_at.desc()).limit(5).all()
        return render_template('profile.html', stats=stats, recent_courses=recent_courses)

    @app.route('/about')
    def about():
        return render_template('about.html')

    # Admin routes
    @app.route('/admin/reset-skillstown-tables', methods=['POST'])
    @login_required
    def reset_skillstown_tables():
        if current_user.email != 'bentakaki7@gmail.com':
            flash('Not authorized', 'danger')
            return redirect(get_url_for('skillstown_user_profile'))
        
        try:
            cmds = [
                "DROP TABLE IF EXISTS skillstown_user_courses CASCADE;",
                "DROP TABLE IF EXISTS skillstown_user_profiles CASCADE;",
                "DROP TABLE IF EXISTS skillstown_course_details CASCADE;",
                "DROP TABLE IF EXISTS skillstown_course_quizzes CASCADE;",
                "DROP TABLE IF EXISTS skillstown_quiz_attempts CASCADE;",
                "DROP TABLE IF EXISTS students CASCADE;",
                "DROP TABLE IF EXISTS companies CASCADE;",
                "DROP TABLE IF EXISTS category CASCADE;",
                "DROP TABLE IF EXISTS skillstown_courses CASCADE;"
            ]
            for cmd in cmds: 
                db.session.execute(text(cmd))
            db.session.commit()
            db.create_all()
            flash('Tables reset successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error resetting tables: {e}', 'danger')
        return redirect(get_url_for('skillstown_user_profile'))

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(413)
    def file_too_large_error(error):
        return render_template('errors/413.html'), 413

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
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
    pass
    

# Import models after db is defined
from models import Company, Student, Category, ContentPage, Course, CourseContentPage, UserProfile, SkillsTownCourse, CourseDetail, CourseQuiz, CourseQuizAttempt, UserCourse, db

def get_quiz_api_headers():
    pass
    

def generate_podcast_for_course(course_name, course_description):
    try:
        pass
            
    except Exception as e:
        pass
        

def get_detailed_course_info(course_name):
    """
    Get detailed course information from the course catalog
    """
    try:
        pass
        
        
    except Exception as e:
        pass
        

def format_course_details(course_details):
    """
    Format course details into a comprehensive text description
    """
    if not course_details:
        pass
    
    formatted = f"Course: {course_details.get('name', 'Unknown')}\\n\\n"
    formatted += f"Description: {course_details.get('description', 'No description available')}\n\n"
    
    if 'duration' in course_details:
        pass
    
    if 'level' in course_details:
        pass
    
    if 'skills' in course_details and course_details['skills']:
        pass
    
    if 'projects' in course_details and course_details['projects']:
        pass
    
    if 'career_paths' in course_details and course_details['career_paths']:
        pass
    
    return formatted

# Auth setup
def init_auth(app, get_url_for_func, get_stats_func):
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    @login_manager.user_loader
    def load_user(user_id): # Added placeholder function
        return Student.query.get(int(user_id)) # Assuming Student model and int ID
    
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
        pass
        
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
        pass
    
    if job_description and job_description.strip():
        pass
    else:
        pass
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}], 
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2000,
            "topP": 0.8
        }
    }
    
    try:
        pass
    except Exception:
        pass
        

# App factory
def create_app(config_name=None):
    global is_production
    
    # Check environment in development mode
    if DEVELOPMENT_MODE:
        check_environment()
        is_production = False
    else:
        if config_name == 'production': 
            pass
        elif config_name is not None: 
            pass
            

    app = Flask(__name__)

    # Templates - Fixed path resolution
    tpl_dirs = [FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates'))]
    animewatchlist_path = os.path.join(os.path.dirname(__file__), '..', 'animewatchlist')
    if os.path.isdir(animewatchlist_path): 
        tpl_dirs.append(FileSystemLoader(os.path.join(animewatchlist_path, 'templates')))
        # pass # Removed pass as it's not needed if the line above is the only content of the if
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
            pass
        except:
            pass
            

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
                pass
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
                pass
        return sorted(res, key=lambda x: x['relevance_score'], reverse=True)
    
    def allowed_file(fn): 
        return '.' in fn and fn.rsplit('.', 1)[1].lower() == 'pdf'
    
    def extract_text_from_pdf(fp):
        txt = ''
        try:
            with open(fp, 'rb') as f:
                pass
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
                    pass
            if len(courses) >= 4:
                break
        return courses

    def get_intermediate_courses(catalog):
        """Get intermediate courses from catalog"""
        courses = []
        for category in catalog.get('categories', []):
            for course in category.get('courses', []):
                if course.get('level', '').lower() in ['intermediate', 'medium']:
                    pass
            if len(courses) >= 4:
                break
        return courses

    def get_advanced_courses(catalog):
        """Get advanced courses from catalog"""
        courses = []
        for category in catalog.get('categories', []):
            for course in category.get('courses', []):
                if course.get('level', '').lower() in ['advanced', 'expert', 'professional']:
                    pass
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
                return jsonify({'error': 'Course not found or not authorized'}), 404
            
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
            
            if response.status_code == 201:
                quiz_data = response.json()
                course_quiz = CourseQuiz(
                    user_course_id=course.id,
                    quiz_api_id=quiz_data['quizId'],
                    quiz_title=quiz_data['title']
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
                    'error': f'Quiz API error: {response.status_code} - {response.text}'
                }), 500
                    
        except Exception as e:
            print(f"Error generating quiz: {e}")
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
                return jsonify({'error': 'User not authorized for this quiz'}), 403
            
            # Call the quiz API with correct endpoint
            response = requests.get(
                f"{QUIZ_API_BASE_URL}/quiz/{quiz_id}/from-course",
                headers=get_quiz_api_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                quiz_data = response.json()
                return jsonify(quiz_data)
            else:
                return jsonify({'error': f'Quiz API error: {response.status_code} - {response.text}'}), 500
                        
        except Exception as e:
            print(f"Exception in get_quiz_details: {e}")
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
                return jsonify({'error': 'User not authorized for this quiz'}), 403
            
            # Call the quiz API with correct endpoint
            response = requests.post(
                f"{QUIZ_API_BASE_URL}/quiz/{quiz_id}/attempt-from-course",
                headers=get_quiz_api_headers(),
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                attempt_data = response.json()
                
                # Save attempt to our database
                quiz_attempt = CourseQuizAttempt(
                    user_id=current_user.id,
                    course_quiz_id=course_quiz.id,
                    attempt_api_id=attempt_data.get('attemptId', attempt_data.get('id', 'unknown'))
                )
                db.session.add(quiz_attempt)
                db.session.commit()
                return jsonify(attempt_data)
            else:
                return jsonify({'error': f'Quiz API error: {response.status_code} - {response.text}'}), 500
                        
        except Exception as e:
            print(f"Exception in start_quiz_attempt: {e}")
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
                return jsonify({'error': 'Quiz attempt not found or not authorized'}), 404
            
            # Get user answers from request
            user_answers = request.json
            
            # Call the quiz API with correct endpoint
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
                return jsonify({'error': f'Quiz API error: {response.status_code} - {response.text}'}), 500
                        
        except Exception as e:
            print(f"Exception in complete_quiz_attempt: {e}")
            return jsonify({'error': str(e)}), 500

    # Add this test route to check your quiz API connectivity
    @app.route('/test-quiz-api')
    @login_required
    def test_quiz_api():
            """Test route to check quiz API connectivity"""
            try:
                # Test basic connectivity
                response = requests.get(f"{QUIZ_API_BASE_URL}/health", timeout=10)
                
                api_status = {
                    'quiz_api_base_url': QUIZ_API_BASE_URL,
                    'health_check_status': response.status_code if response else 'No response',
                    'health_check_response': response.text if response else 'No response'
                }
                
                return jsonify(api_status)
                
            except Exception as e:
                return jsonify({
                    'error': str(e),
                    'quiz_api_base_url': QUIZ_API_BASE_URL
                }), 500

    @app.route('/test-quiz-auth')
    @login_required
    def test_quiz_auth():
        """Test route to verify quiz API authentication with different methods"""
        try:
            access_token = os.environ.get('QUIZ_API_ACCESS_TOKEN', QUIZ_API_ACCESS_TOKEN)
            
            # Try different authentication methods
            auth_methods = [
                {'name': 'Bearer Token', 'headers': {'Content-Type': 'application/json', 'Authorization': f'Bearer {access_token}'}},
                {'name': 'Token Header', 'headers': {'Content-Type': 'application/json', 'Authorization': f'Token {access_token}'}},
                {'name': 'X-API-Key', 'headers': {'Content-Type': 'application/json', 'X-API-Key': access_token}},
                {'name': 'X-Access-Token', 'headers': {'Content-Type': 'application/json', 'X-Access-Token': access_token}},
                {'name': 'No Auth', 'headers': {'Content-Type': 'application/json'}},
            ]
            
            # Test endpoints
            test_endpoints = ['/health', '/status', '/']
            
            results = {}
            
            for method in auth_methods:
                pass
            
            return jsonify({
                'quiz_api_base_url': QUIZ_API_BASE_URL,
                'token_preview': f"{access_token[:20]}..." if access_token else "NO TOKEN",
                'authentication_test_results': results
            })
            
        except Exception as e:
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
            pass # Placeholder for implementation
                    
        except Exception as e:
            print(f"Error getting quiz recommendations: {e}")
            return jsonify({'error': str(e)}), 500    # PODCAST ROUTES
    @app.route('/course/<int:course_id>/generate-podcast', methods=['POST'])
    @login_required
    def generate_podcast(course_id): # Added placeholder function
        pass

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
import os
import datetime
import json
import re
import sys
import traceback
import PyPDF2
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, current_app, Response
from flask_login import login_required, current_user, LoginManager, login_user, logout_user, UserMixin
from werkzeug.utils import secure_filename
from sqlalchemy import text
from jinja2 import ChoiceLoader, FileSystemLoader
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from local_config import NARRETEX_API_URL, check_environment, LOCAL_DATABASE_URL, DEVELOPMENT_MODE
from urllib.parse import urlencode

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


# Production detection
is_production = os.environ.get('RENDER', False) or os.environ.get('FLASK_ENV') == 'production'

# Gemini API configuration
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent"
QUIZ_API_BASE_URL = os.environ.get('QUIZ_API_URL', 'http://localhost:8081')

def get_url_for(*args, **kwargs):
    url = url_for(*args, **kwargs)
    if is_production and not url.startswith('/skillstown'):
        url = f"/skillstown{url}"
    return url

# Import models after db is defined
from models import Company, Student, Category, ContentPage, Course, CourseContentPage, UserProfile, SkillsTownCourse, CourseDetail, db

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
        # Force remove any PostgreSQL connection for local development
        if 'DATABASE_URL' in os.environ:
            print("Removing DATABASE_URL for local development")
            del os.environ['DATABASE_URL']
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
    
    # Database configuration - FORCE SQLite for local development
    if DEVELOPMENT_MODE:
        print(f"Local development mode: Using SQLite database")
        app.config['SQLALCHEMY_DATABASE_URI'] = LOCAL_DATABASE_URL
    else:
        # Production: use DATABASE_URL if available
        db_url = os.environ.get('DATABASE_URL')
        if db_url and db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://')
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///skillstown.db'
    
    print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)

    @app.context_processor
    def inject(): 
        return {
            'current_year': datetime.datetime.now().year,
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
            return {'total':0,'enrolled':0,'in_progress':0,'completed':0,'completion_percentage':0}

    # Initialize auth
    init_auth(app, get_url_for, get_skillstown_stats)

    # Models - Define within app context
    class UserCourse(db.Model):
        __tablename__ = 'skillstown_user_courses'
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.String(36), db.ForeignKey('students.id'), nullable=False)
        category = db.Column(db.String(100), nullable=False)
        course_name = db.Column(db.String(255), nullable=False)
        status = db.Column(db.String(50), default='enrolled')
        created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
        __table_args__ = (db.UniqueConstraint('user_id', 'course_name', name='skillstown_user_course_unique'),)

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

    @app.route('/course/<int:course_id>/generate-quiz', methods=['POST'])
    @login_required
    def generate_course_quiz(course_id):
        """Generate a quiz based on the course content using AI"""
        course = UserCourse.query.filter_by(id=course_id, user_id=current_user.id).first_or_404()
        
        try:
            # Get course details for quiz generation
            course_details = CourseDetail.query.filter_by(user_course_id=course_id).first()
            if not course_details:
                flash('Course details not found', 'error')
                return redirect(get_url_for('course_detail', course_id=course_id))
            
            # Get detailed course info from catalog
            course_info = get_detailed_course_info(course.course_name)
            
            # Generate quiz using Gemini
            quiz_data = generate_quiz_from_course_content(course, course_details, course_info)
            
            if not quiz_data:
                flash('Failed to generate quiz', 'error')
                return redirect(get_url_for('course_detail', course_id=course_id))
            
            # Create quiz via API call to your quiz backend
            quiz_payload = {
                'title': f"{course.course_name} - Knowledge Check",
                'subject': course.category,
                'description': f"Quiz generated from {course.course_name} course content",
                'isPublic': False,  # Private quiz for this user
                'questions': quiz_data['questions']
            }
            
            # Make API call to create quiz (you'll need to handle authentication)
            quiz_response = requests.post(
                f"{QUIZ_API_BASE_URL}/quiz/create",
                json=quiz_payload,
                cookies={'as': request.cookies.get('as')},  # Pass authentication
                timeout=30
            )
            
            if quiz_response.status_code == 201:
                quiz_id = quiz_response.json().get('quizId')
                flash('Quiz generated successfully!', 'success')
                return redirect(f"{QUIZ_API_BASE_URL.replace('8080', '5001')}/quiz/{quiz_id}")
            else:
                flash('Failed to create quiz', 'error')
                return redirect(get_url_for('course_detail', course_id=course_id))
                
        except Exception as e:
            print(f"Error generating quiz: {e}")
            flash('Error generating quiz. Please try again.', 'error')
            return redirect(get_url_for('course_detail', course_id=course_id))

    def generate_quiz_from_course_content(course, course_details, course_info):
        """Generate quiz questions using Gemini AI based on course content"""
        if not GEMINI_API_KEY:
            return None
        
        # Prepare course content for quiz generation
        content = f"""
        Course: {course.course_name}
        Category: {course.category}
        Description: {course_details.description}
        
        Course Details:
        {format_course_details(course_info)}
        
        Skills covered: {', '.join(course_info.get('skills', []))}
        Projects: {', '.join(course_info.get('projects', []))}
        """
        
        prompt = f"""
        Based on the following course content, generate 5 multiple-choice questions to test student understanding.
        Each question should have 4 options with only one correct answer.
        
        Course Content:
        {content[:3000]}  # Limit content size
        
        Return a JSON object with this structure:
        {{
            "questions": [
                {{
                    "question": "Question text here?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correctAnswer": "Option A",
                    "explanation": "Brief explanation of why this is correct"
                }}
            ]
        }}
        
        Focus on practical knowledge and key concepts from the course.
        """
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2000,
                "topP": 0.8
            }
        }
        
        try:
            response = requests.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('candidates'):
                text = result['candidates'][0]['content']['parts'][0]['text']
                
                # Extract JSON from response
                import re
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
                if json_match:
                    quiz_data = json.loads(json_match.group(1))
                    return quiz_data
                else:
                    # Try to parse the entire response as JSON
                    quiz_data = json.loads(text.strip())
                    return quiz_data
                    
        except Exception as e:
            print(f"Error generating quiz with Gemini: {e}")
            return None

        @app.route('/course/<int:course_id>/quiz-completed', methods=['POST'])
        @login_required
        def handle_quiz_completion(course_id):
            """Handle quiz completion and provide personalized recommendations"""
            course = UserCourse.query.filter_by(id=course_id, user_id=current_user.id).first_or_404()
            
            try:
                quiz_data = request.get_json()
                score = quiz_data.get('score', 0)
                weak_areas = quiz_data.get('weak_areas', [])
                strong_areas = quiz_data.get('strong_areas', [])
                
                # Generate personalized recommendations based on quiz results
                recommendations = generate_personalized_recommendations(
                    course, score, weak_areas, strong_areas
                )
                
                # Store quiz results in the database
                course_details = CourseDetail.query.filter_by(user_course_id=course_id).first()
                if course_details:
                    # Update course details with quiz results
                    quiz_results = {
                        'score': score,
                        'weak_areas': weak_areas,
                        'strong_areas': strong_areas,
                        'recommendations': recommendations,
                        'completed_at': datetime.datetime.utcnow().isoformat()
                    }
                    course_details.quiz_results = json.dumps(quiz_results)
                    db.session.commit()
                
                return jsonify({
                    'success': True,
                    'recommendations': recommendations,
                    'score': score
                })
                
            except Exception as e:
                print(f"Error handling quiz completion: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500

        def generate_personalized_recommendations(course, score, weak_areas, strong_areas):
            """Generate personalized course recommendations based on quiz performance"""
            recommendations = {
                'next_courses': [],
                'remedial_courses': [],
                'advanced_courses': [],
                'specific_advice': ''
            }
            
            catalog = load_course_catalog()
            
            # Determine skill level based on score
            if score >= 80:
                skill_level = 'advanced'
                recommendations['specific_advice'] = f"Excellent work on {course.course_name}! You've mastered the core concepts."
            elif score >= 60:
                skill_level = 'intermediate'
                recommendations['specific_advice'] = f"Good progress on {course.course_name}. Focus on strengthening weak areas."
            else:
                skill_level = 'beginner'
                recommendations['specific_advice'] = f"Consider reviewing {course.course_name} fundamentals before advancing."
            
            # Find related courses based on category and performance
            for category in catalog.get('categories', []):
                for catalog_course in category.get('courses', []):
                    course_name = catalog_course['name']
                    course_level = catalog_course.get('level', 'beginner').lower()
                    
                    # Skip the current course
                    if course_name.lower() == course.course_name.lower():
                        continue
                    
                    # Check if course is related to current course category
                    if category['name'].lower() == course.category.lower():
                        if score < 60 and course_level == 'beginner':
                            # Suggest remedial courses for low scores
                            recommendations['remedial_courses'].append({
                                'name': course_name,
                                'category': category['name'],
                                'reason': f"Strengthen fundamentals in {course.category}",
                                'description': catalog_course.get('description', '')
                            })
                        elif score >= 80 and course_level == 'advanced':
                            # Suggest advanced courses for high scores
                            recommendations['advanced_courses'].append({
                                'name': course_name,
                                'category': category['name'],
                                'reason': f"Build on your {course.category} expertise",
                                'description': catalog_course.get('description', '')
                            })
                        elif course_level == 'intermediate':
                            # General next step courses
                            recommendations['next_courses'].append({
                                'name': course_name,
                                'category': category['name'],
                                'reason': f"Natural progression from {course.course_name}",
                                'description': catalog_course.get('description', '')
                            })
            
            # Limit recommendations
            recommendations['next_courses'] = recommendations['next_courses'][:3]
            recommendations['remedial_courses'] = recommendations['remedial_courses'][:2]
            recommendations['advanced_courses'] = recommendations['advanced_courses'][:3]
            
            return recommendations
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

    # Add route for testing podcast generation
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

    @app.route('/webhook/quiz-completed', methods=['POST'])
    def quiz_completion_webhook():
        """Handle quiz completion notifications from the quiz system"""
        try:
            data = request.get_json()
            
            # Validate webhook data
            required_fields = ['user_id', 'quiz_id', 'score', 'course_context']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400
            
            user_id = data['user_id']
            quiz_id = data['quiz_id'] 
            score = data['score']
            course_context = data['course_context']  # Should contain course_id
            weak_areas = data.get('weak_areas', [])
            strong_areas = data.get('strong_areas', [])
            
            # Find the course
            course_id = course_context.get('course_id')
            if not course_id:
                return jsonify({'error': 'Course ID not provided'}), 400
                
            course = UserCourse.query.filter_by(
                id=course_id, 
                user_id=user_id
            ).first()
            
            if not course:
                return jsonify({'error': 'Course not found'}), 404
            
            # Generate recommendations based on quiz performance
            recommendations = generate_personalized_recommendations(
                course, score, weak_areas, strong_areas
            )
            
            # Store quiz attempt
            quiz_attempt = CourseQuizAttempt(
                user_id=user_id,
                course_id=course_id,
                quiz_api_id=quiz_id,
                score=score,
                weak_areas=json.dumps(weak_areas),
                strong_areas=json.dumps(strong_areas),
                recommendations_generated=json.dumps(recommendations)
            )
            db.session.add(quiz_attempt)
            
            # Update course details with latest quiz results
            course_details = CourseDetail.query.filter_by(user_course_id=course_id).first()
            if course_details:
                quiz_results = {
                    'score': score,
                    'weak_areas': weak_areas,
                    'strong_areas': strong_areas,
                    'recommendations': recommendations,
                    'completed_at': datetime.datetime.utcnow().isoformat(),
                    'quiz_id': quiz_id
                }
                course_details.quiz_results = json.dumps(quiz_results)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'recommendations': recommendations,
                'message': 'Quiz results processed successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"Error processing quiz completion webhook: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/course/<int:course_id>/quiz-recommendations')
    @login_required
    def get_quiz_recommendations(course_id):
        """API endpoint to get quiz-based recommendations for a course"""
        course = UserCourse.query.filter_by(id=course_id, user_id=current_user.id).first_or_404()
        
        # Get latest quiz attempt
        latest_attempt = CourseQuizAttempt.query.filter_by(
            user_id=current_user.id,
            course_id=course_id
        ).order_by(CourseQuizAttempt.completed_at.desc()).first()
        
        if not latest_attempt:
            return jsonify({'error': 'No quiz attempts found'}), 404
        
        try:
            recommendations = json.loads(latest_attempt.recommendations_generated)
            return jsonify({
                'score': latest_attempt.score,
                'recommendations': recommendations,
                'completed_at': latest_attempt.completed_at.isoformat()
            })
        except Exception as e:
            print(f"Error getting quiz recommendations: {e}")
            return jsonify({'error': 'Failed to get recommendations'}), 500
    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(get_url_for('index'))

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
                    course_details.completed_at = datetime.datetime.utcnow()
            
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
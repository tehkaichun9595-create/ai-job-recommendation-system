"""
AI Job Recommendation System - Flask Backend API
Email Verification and Password Reset Integrated Version
"""

from flask import Flask, request, jsonify, url_for, send_from_directory, send_file
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import os
import pymongo
from itsdangerous import URLSafeTimedSerializer as Serializer
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

# Resume parsing
try:
    from resume_parser import parse_resume
    resume_parser_available = True
    print("✅ Resume parser loaded successfully.")
except ImportError as e:
    resume_parser_available = False
    print(f"⚠️ Resume parser not available: {e}")

# AI Engine for semantic matching
try:
    from ai_engine import (
        calculate_ai_match_score,
        semantic_skill_similarity,
        is_ai_available,
        get_ai_status,
        initialize as initialize_ai
    )
    ai_engine_available = True
    print("🤖 AI Engine module loaded. Initializing...")
    initialize_ai()  # Pre-load the model
except ImportError as e:
    ai_engine_available = False
    print(f"⚠️ AI Engine not available (will use keyword matching): {e}")

# Ollama Engine for chat and advanced AI features
try:
    from ollama_engine import (
        is_ollama_available,
        chat_with_ollama,
        explain_job_match,
        extract_skills_from_text,
        get_career_advice,
        suggest_skills_to_learn,
        get_ollama_status
    )
    ollama_available = True
    print("🦙 Ollama Engine module loaded.")
except ImportError as e:
    ollama_available = False
    print(f"⚠️ Ollama Engine not available: {e}")

# --- Configuration & Initialization ---
try:
    from config import MONGO_URI, MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER
    from config import JOOBLE_API_KEY
    use_mongo = True
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    db = client.get_database('alumni_database')
    
    _ = db.list_collection_names() 
    users_collection = db['profiles']
    jobs_collection = db['jobs']
    tokens_collection = db['verification_tokens']
    applications_collection = db['applications']
    bookmarks_collection = db['bookmarks']
    
    print("✅ MongoDB connection successful.")
except Exception as e:
    use_mongo = False
    print(f"❌ MongoDB connection failed. Password reset feature disabled. Error: {e}")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JOBS_STATIC_FILE = os.path.join(BASE_DIR, 'jobs.json')
USERS_FILE = os.path.join(BASE_DIR, 'users_data.json')
JOBS_DATA_FILE = os.path.join(BASE_DIR, 'jobs_data.json')

# Configure upload folders
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
RESUME_FOLDER = os.path.join(UPLOAD_FOLDER, 'resumes')
COVER_LETTER_FOLDER = os.path.join(UPLOAD_FOLDER, 'cover_letters')
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.docx', '.txt'}

# Allowed file extensions for resume and cover letter (strict PDF/DOCX only)
os.makedirs(RESUME_FOLDER, exist_ok=True)
os.makedirs(COVER_LETTER_FOLDER, exist_ok=True)

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Email Configuration (using smtplib)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-secret-key-12345')
serializer = Serializer(app.config['SECRET_KEY'], salt='email-confirm')

print("Starting Flask server...")

# --- Utility Functions ---

def load_json(filepath, default=[]):
    """Load data from JSON file for fallback."""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
    except Exception:
        pass
    return default

def save_json(filename, data):
    """Save data to JSON file for fallback."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Error saving {filename}: {e}")

def convert_objectid(data_list):
    """Converts MongoDB ObjectId to string for JSON serialization."""
    for item in data_list:
        if '_id' in item:
            item['_id'] = str(item['_id'])
    return data_list

def validate_password_strength(password):
    """
    Validate password strength requirements.
    Returns (is_valid, error_message)
    """
    import re
    
    if len(password) < 8:
        return False, 'Password must be at least 8 characters'
    
    if not re.search(r'[A-Z]', password):
        return False, 'Password must contain at least one uppercase letter'
    
    if not re.search(r'[a-z]', password):
        return False, 'Password must contain at least one lowercase letter'
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, 'Password must contain at least one special symbol (!@#$%^&* etc)'
    
    return True, None

def get_all_users():
    if use_mongo:
        users = list(users_collection.find({}, {"password_hash": 0}))
        # FIX: Convert ObjectIds before returning
        return convert_objectid(users)
    return load_json(USERS_FILE, [])

def get_user_by_email(email):
    email_lower = email.lower()
    if use_mongo:
        user = users_collection.find_one({'email': email_lower})
        # FIX: Convert ObjectId for the single user object returned here
        if user and '_id' in user:
             user['_id'] = str(user['_id'])
        return user
    
    users = load_json(USERS_FILE, [])
    return next((u for u in users if u.get('email', '').lower() == email_lower), None)

def get_all_jobs():
    if use_mongo:
        jobs = list(jobs_collection.find())
        if not jobs:
             static_jobs = load_json(JOBS_STATIC_FILE, [])
             if static_jobs:
                 jobs_collection.insert_many(static_jobs)
                 # FIX: Convert ObjectIds for static jobs if inserted
                 return convert_objectid(static_jobs)
        # FIX: Convert ObjectIds before returning
        return convert_objectid(jobs)
        
    jobs = load_json(JOBS_DATA_FILE, [])
    if not jobs:
        jobs = load_json(JOBS_STATIC_FILE, [])
        if jobs: save_json(JOBS_DATA_FILE, jobs)
    return jobs

def save_user(user):
    if use_mongo:
        update_data = user.copy()
        if '_id' in update_data:
            del update_data['_id']
        users_collection.update_one(
            {'email': user['email']},
            {'$set': update_data},
            upsert=True
        )
    else:
        users = load_json(USERS_FILE, [])
        email_lower = user['email'].lower()
        user_index = next((i for i, u in enumerate(users) if u.get('email', '').lower() == email_lower), -1)
        
        if user_index == -1:
            user['id'] = max([u.get('id', 0) for u in users] or [0]) + 1
            users.append(user)
        else:
            users[user_index] = user
        save_json(USERS_FILE, users)

# --- Email Functions ---

def generate_verification_token(email):
    return serializer.dumps(email, salt='email-confirm')

def generate_password_reset_token(email):
    """Generate a password reset token valid for 1 hour"""
    return serializer.dumps(email, salt='password-reset')

def verify_password_reset_token(token, max_age=3600):
    """Verify password reset token and return email if valid"""
    try:
        email = serializer.loads(token, salt='password-reset', max_age=max_age)
        return email
    except Exception:
        return None

def save_verification_token(email, token):
    """Save verification token to database"""
    if not use_mongo:
        return False
    try:
        # Remove any existing tokens for this email
        tokens_collection.delete_many({'email': email.lower(), 'type': 'email_verification'})
        
        token_doc = {
            'email': email.lower(),
            'token': token,
            'type': 'email_verification',
            'created_at': datetime.now(),
            'expires_at': datetime.now().replace(hour=datetime.now().hour + 1),
            'used': False
        }
        tokens_collection.insert_one(token_doc)
        print(f"✅ Verification token saved for {email}")
        return True
    except Exception as e:
        print(f"❌ Failed to save verification token: {e}")
        return False

def get_verification_token(token):
    """Retrieve verification token from database"""
    if not use_mongo:
        return None
    try:
        token_doc = tokens_collection.find_one({
            'token': token,
            'type': 'email_verification',
            'used': False
        })
        return token_doc
    except Exception as e:
        print(f"❌ Failed to get verification token: {e}")
        return None

def invalidate_token(token):
    """Mark token as used to prevent reuse"""
    if not use_mongo:
        return False
    try:
        tokens_collection.update_one(
            {'token': token},
            {'$set': {'used': True}}
        )
        return True
    except Exception as e:
        print(f"❌ Failed to invalidate token: {e}")
        return False

def send_verification_email(user_email):
    if not use_mongo:
        print(f"⚠️ Cannot send email for {user_email}. MongoDB/Email config failed.")
        return False
        
    try:
        token = generate_verification_token(user_email)
        
        # Save token to database for tracking
        if not save_verification_token(user_email, token):
            print(f"⚠️ Warning: Token not saved to DB for {user_email}")
        
        verification_link = f"http://127.0.0.1:5000/api/verify_email/{token}"
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = MAIL_DEFAULT_SENDER
        msg['To'] = user_email
        msg['Subject'] = "AI JobMatch Pro: Verify Your Email Address"
        
        body = f"""
Hello from AI JobMatch Pro,

Thank you for registering! Please click the link below to verify your email address:

{verification_link}

This link will expire in 1 hour.

If you did not request this, please ignore this email.
"""
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email using smtplib
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.sendmail(MAIL_DEFAULT_SENDER, user_email, msg.as_string())
        
        print(f"✅ Verification email sent to {user_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send verification email to {user_email}: {e}")
        return False

def send_password_reset_email(user_email):
    """Send password reset email with token using smtplib"""
    if not use_mongo:
        print(f"⚠️ Cannot send email for {user_email}. MongoDB/Email config failed.")
        return False
        
    try:
        token = generate_password_reset_token(user_email)
        reset_link = f"http://127.0.0.1:5000/api/reset_password/{token}"
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = MAIL_DEFAULT_SENDER
        msg['To'] = user_email
        msg['Subject'] = "AI JobMatch Pro: Password Reset Request"
        
        body = f"""
Hello from AI JobMatch Pro,

You requested to reset your password. Please click the link below to reset it:

{reset_link}

This link will expire in 1 hour.

If you did not request this password reset, please ignore this email and your password will remain unchanged.

For security reasons, this link can only be used once.
"""
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email using smtplib
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.sendmail(MAIL_DEFAULT_SENDER, user_email, msg.as_string())
        
        print(f"✅ Password reset email sent to {user_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send password reset email to {user_email}: {e}")
        return False

# --- NEW: 6-Digit Password Reset Code System ---

import random

def generate_reset_code():
    """Generate a random 6-digit code"""
    return str(random.randint(100000, 999999))

def save_reset_code(email, code):
    """Save reset code to database with 10-minute expiry"""
    if not use_mongo:
        return False
    try:
        # Delete any existing codes for this email
        tokens_collection.delete_many({'email': email.lower(), 'type': 'password_reset_code'})
        
        token_doc = {
            'email': email.lower(),
            'code': code,
            'type': 'password_reset_code',
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(minutes=2),
            'used': False,
            'verified': False
        }
        tokens_collection.insert_one(token_doc)
        print(f"✅ Reset code saved for {email}")
        return True
    except Exception as e:
        print(f"❌ Failed to save reset code: {e}")
        return False

def verify_reset_code(email, code):
    """Verify the 6-digit code matches and is not expired"""
    if not use_mongo:
        return False, "Database not available"
    try:
        token_doc = tokens_collection.find_one({
            'email': email.lower(),
            'code': code,
            'type': 'password_reset_code',
            'used': False
        })
        
        if not token_doc:
            return False, "Invalid code"
        
        if datetime.now() > token_doc.get('expires_at', datetime.now()):
            return False, "Code expired"
        
        # Mark as verified but not used yet (will be used when password is actually reset)
        tokens_collection.update_one(
            {'_id': token_doc['_id']},
            {'$set': {'verified': True}}
        )
        
        return True, "Code verified"
    except Exception as e:
        print(f"❌ Failed to verify reset code: {e}")
        return False, str(e)

def send_reset_code_email(user_email, code):
    """Send 6-digit reset code via email"""
    if not use_mongo:
        print(f"⚠️ Cannot send email for {user_email}. MongoDB/Email config failed.")
        return False
        
    try:
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = MAIL_DEFAULT_SENDER
        msg['To'] = user_email
        msg['Subject'] = "AI JobMatch Pro: Your Password Reset Code"
        
        body = f"""
Hello from AI JobMatch Pro,

You requested to reset your password. Your verification code is:

    {code}

This code will expire in 2 minutes.

If you did not request this password reset, please ignore this email.

For security reasons, never share this code with anyone.
"""
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email using smtplib
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.sendmail(MAIL_DEFAULT_SENDER, user_email, msg.as_string())
        
        print(f"✅ Reset code email sent to {user_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send reset code email to {user_email}: {e}")
        return False

# --- Core Logic Functions ---

# Skill aliases for better matching (maps user skill to possible variations in job postings)
SKILL_ALIASES = {
    'python': ['python', 'python3', 'py'],
    'javascript': ['javascript', 'js', 'ecmascript', 'es6', 'es2015'],
    'typescript': ['typescript', 'ts'],
    'react': ['react', 'reactjs', 'react.js', 'react js'],
    'angular': ['angular', 'angularjs', 'angular.js', 'angular js'],
    'vue': ['vue', 'vuejs', 'vue.js', 'vue js'],
    'node': ['node', 'nodejs', 'node.js', 'node js'],
    'next': ['next', 'nextjs', 'next.js'],
    'express': ['express', 'expressjs', 'express.js'],
    'django': ['django'],
    'flask': ['flask'],
    'java': ['java', 'j2ee', 'jee'],
    'c++': ['c++', 'cpp', 'cplusplus'],
    'c#': ['c#', 'csharp', 'c sharp', '.net'],
    'sql': ['sql', 'mysql', 'postgresql', 'postgres', 'sqlite', 'mssql', 'oracle'],
    'mongodb': ['mongodb', 'mongo', 'nosql'],
    'aws': ['aws', 'amazon web services', 'amazon cloud', 'ec2', 's3', 'lambda'],
    'azure': ['azure', 'microsoft azure', 'ms azure'],
    'gcp': ['gcp', 'google cloud', 'google cloud platform'],
    'docker': ['docker', 'containerization', 'containers'],
    'kubernetes': ['kubernetes', 'k8s', 'container orchestration'],
    'machine learning': ['machine learning', 'ml', 'deep learning', 'ai', 'artificial intelligence'],
    'data science': ['data science', 'data scientist', 'data analytics', 'data analysis'],
    'tensorflow': ['tensorflow', 'tf'],
    'pytorch': ['pytorch', 'torch'],
    'git': ['git', 'github', 'gitlab', 'version control'],
    'html': ['html', 'html5'],
    'css': ['css', 'css3', 'scss', 'sass', 'tailwind', 'bootstrap'],
    'php': ['php', 'laravel', 'symfony'],
    'ruby': ['ruby', 'rails', 'ruby on rails'],
    'go': ['go', 'golang'],
    'rust': ['rust'],
    'swift': ['swift', 'ios', 'swiftui'],
    'kotlin': ['kotlin', 'android'],
    'flutter': ['flutter', 'dart'],
    'react native': ['react native', 'reactnative', 'mobile development'],
    'agile': ['agile', 'scrum', 'kanban', 'sprint'],
    'devops': ['devops', 'ci/cd', 'cicd', 'continuous integration', 'continuous deployment'],
    'api': ['api', 'rest', 'restful', 'graphql', 'soap'],
    'testing': ['testing', 'qa', 'quality assurance', 'unit test', 'automation testing'],
    'linux': ['linux', 'unix', 'bash', 'shell'],
    'excel': ['excel', 'spreadsheet', 'microsoft office', 'ms office'],
    'power bi': ['power bi', 'powerbi', 'business intelligence', 'bi'],
    'tableau': ['tableau', 'data visualization'],
}

def match_skill_in_text(skill, text):
    """
    Check if a skill matches in the given text using aliases.
    Returns True if any variation of the skill is found.
    """
    skill_lower = skill.lower().strip()
    text_lower = text.lower()
    
    # First, try direct match
    if skill_lower in text_lower:
        return True
    
    # Then, check aliases
    for base_skill, aliases in SKILL_ALIASES.items():
        # If the user skill matches a base skill or any of its aliases
        if skill_lower == base_skill or skill_lower in aliases:
            # Check if any alias appears in the job text
            for alias in aliases:
                if alias in text_lower:
                    return True
            break
    
    # Try partial matching for compound skills
    skill_words = skill_lower.split()
    if len(skill_words) > 1:
        # For compound skills like "Machine Learning", check if both words appear close together
        for word in skill_words:
            if len(word) > 2 and word in text_lower:
                return True
    
    return False

def calculate_match_score(user_skills, job_skills, user_exp, job_exp, 
                          user_location='', job_location='', user_bio='',
                          job_title='', job_description='', use_ai=True):
    """
    Calculate job match score using AI-powered semantic matching if available.
    Falls back to keyword matching if AI is unavailable.
    """
    job_skills_str = job_skills if isinstance(job_skills, str) else ','.join(job_skills)
    
    # Try AI-powered matching first
    if use_ai and ai_engine_available and is_ai_available():
        try:
            result = calculate_ai_match_score(
                user_skills=user_skills,
                job_skills=job_skills_str,
                user_exp=user_exp,
                job_exp=job_exp,
                user_location=user_location,
                job_location=job_location,
                user_bio=user_bio,
                job_title=job_title,
                job_description=job_description
            )
            return result['match_score'], result
        except Exception as e:
            print(f"⚠️ AI scoring failed, falling back to keyword matching: {e}")
    
    # Fallback: Keyword-based matching with score breakdown
    user_skill_set = set([s.strip().lower() for s in user_skills.split(',') if s.strip()])
    job_skill_set = set([s.strip().lower() for s in job_skills_str.split(',') if s.strip()])
    
    if len(job_skill_set) == 0:
        return 0, {'ai_powered': False, 'method': 'keyword', 'components': {}}
    
    matched_skills = user_skill_set.intersection(job_skill_set)
    skill_match_ratio = len(matched_skills) / len(job_skill_set)
    skill_score = round(skill_match_ratio * 100, 2)
    
    # Calculate experience score
    if user_exp >= job_exp:
        exp_score = 100
    else:
        exp_score = round((user_exp / job_exp) * 100, 2) if job_exp > 0 else 0
    
    # Calculate location score (basic matching)
    location_score = 50  # Default neutral
    if user_location and job_location:
        user_loc = user_location.lower().strip()
        job_loc = job_location.lower().strip()
        if user_loc in job_loc or job_loc in user_loc:
            location_score = 100
        elif 'remote' in job_loc or 'wfh' in job_loc:
            location_score = 80
        else:
            # Check state matching
            location_match = _check_location_match(user_loc, job_loc)
            if location_match == 'exact':
                location_score = 100
            elif location_match == 'same_state':
                location_score = 90
            elif location_match == 'remote':
                location_score = 80
            else:
                location_score = 30
    
    # Title fit (basic - just check if any skill appears in title)
    title_score = 50  # Default
    if job_title:
        job_title_lower = job_title.lower()
        for skill in user_skill_set:
            if skill in job_title_lower:
                title_score = 80
                break
    
    # Penalize experience when skills are completely irrelevant
    if skill_score < 15:
        exp_score = exp_score * 0.3
    elif skill_score < 35:
        exp_score = exp_score * 0.6
        
    # Weighted final score (same weights as AI)
    final_score = round(
        skill_score * 0.45 + 
        exp_score * 0.25 + 
        location_score * 0.15 + 
        title_score * 0.15, 
        2
    )
    
    return final_score, {
        'match_score': final_score,
        'ai_powered': False,
        'method': 'keyword',
        'matched_skills': list(matched_skills),
        'components': {
            'skill_similarity': skill_score,
            'experience_fit': exp_score,
            'location_relevance': location_score,
            'title_alignment': title_score
        }
    }

def generate_recommendations(user, location_filter=True):
    """
    Generate job recommendations using AI-powered matching.
    Returns recommendations sorted by match score.
    
    Args:
        user: User profile dict
        location_filter: If True, heavily prioritize jobs matching user's location
    """
    jobs = get_all_jobs()
    recommendations = []
    
    user_skills_str = user.get('skills', '')
    user_exp_int = int(user.get('experience', 0))
    user_location = user.get('location', '').lower().strip()
    user_bio = user.get('bio', '')
    
    for job in jobs:
        job_exp_int = int(job.get('experience_required', 0))
        job_skills = job.get('required_skills', '')
        job_location = job.get('location', '').lower().strip()
        job_title = job.get('title', '')
        job_description = job.get('description', '')
        
        match_score, score_details = calculate_match_score(
            user_skills=user_skills_str,
            job_skills=job_skills,
            user_exp=user_exp_int,
            job_exp=job_exp_int,
            user_location=user_location,
            job_location=job_location,
            user_bio=user_bio,
            job_title=job_title,
            job_description=job_description
        )
        
        # Enhanced location filtering
        if location_filter and user_location:
            location_match = _check_location_match(user_location, job_location)
            if location_match == 'exact':
                match_score = min(100, match_score * 1.2)  # Boost exact matches
            elif location_match == 'same_state':
                match_score = min(100, match_score * 1.1)  # Boost same state
            elif location_match == 'remote':
                pass  # Keep original score for remote jobs
            elif location_match == 'different':
                match_score = match_score * 0.5  # Penalize different locations
        
        # Only include jobs with meaningful match score AND skill relevance
        skill_score = score_details.get('components', {}).get('skill_similarity', 0)
        
        # Filter: overall score >= 40% AND skill score > 20% (to avoid unrelated jobs)
        if match_score >= 40 and skill_score > 20:
            job_rec = job.copy()
            job_rec['match_score'] = round(match_score, 2)
            job_rec['ai_powered'] = score_details.get('ai_powered', False)
            # Always include score breakdown (works for both AI and keyword matching)
            job_rec['score_breakdown'] = score_details.get('components', {})
            recommendations.append(job_rec)
    
    recommendations.sort(key=lambda x: x['match_score'], reverse=True)
    return recommendations


def _check_location_match(user_location, job_location):
    """Check how well job location matches user location."""
    if not user_location or not job_location:
        return 'unknown'
    
    user_loc = user_location.lower().strip()
    job_loc = job_location.lower().strip()
    
    # Check for remote/WFH
    remote_keywords = ['remote', 'work from home', 'wfh', 'hybrid', 'anywhere']
    if any(kw in job_loc for kw in remote_keywords):
        return 'remote'
    
    # Exact match or contains
    if user_loc in job_loc or job_loc in user_loc:
        return 'exact'
    
    # Malaysian state matching
    malaysia_states = {
        'kuala lumpur': ['kuala lumpur', 'kl'],
        'selangor': ['selangor', 'petaling jaya', 'pj', 'shah alam', 'cyberjaya', 'subang', 'puchong', 'klang', 'kajang', 'damansara'],
        'penang': ['penang', 'pulau pinang', 'georgetown', 'butterworth', 'bayan lepas'],
        'johor': ['johor', 'johor bahru', 'jb', 'iskandar'],
        'perak': ['perak', 'ipoh'],
        'pahang': ['pahang', 'kuantan'],
        'negeri sembilan': ['negeri sembilan', 'seremban', 'nilai'],
        'melaka': ['melaka', 'malacca'],
        'kedah': ['kedah', 'alor setar', 'langkawi'],
        'kelantan': ['kelantan', 'kota bharu'],
        'terengganu': ['terengganu', 'kuala terengganu'],
        'sabah': ['sabah', 'kota kinabalu'],
        'sarawak': ['sarawak', 'kuching', 'miri'],
    }
    
    # Find user's state
    user_state = None
    for state, cities in malaysia_states.items():
        for city in cities:
            if city in user_loc:
                user_state = state
                break
        if user_state:
            break
    
    # Find job's state
    job_state = None
    for state, cities in malaysia_states.items():
        for city in cities:
            if city in job_loc:
                job_state = state
                break
        if job_state:
            break
    
    # Compare states
    if user_state and job_state:
        if user_state == job_state:
            return 'same_state'
        # KL-Selangor metro area
        kl_metro = {'kuala lumpur', 'selangor'}
        if user_state in kl_metro and job_state in kl_metro:
            return 'same_state'
    
    return 'different'




# --- Jooble External Job API (Malaysia Only) ---

# Jooble country domain - Malaysia only
JOOBLE_COUNTRY_DOMAIN = 'my.jooble.org'  # Malaysia

def fetch_jooble_jobs(keywords='', location='', page=1, results_per_page=20, country='my'):
    """
    Fetch jobs from Jooble API for Malaysia.
    System is designed specifically for the Malaysian job market.
    API Docs: https://jooble.org/api/about
    """
    try:
        if not JOOBLE_API_KEY or JOOBLE_API_KEY == 'YOUR_JOOBLE_API_KEY':
            print("⚠️ Jooble API key not configured. Please add your key to config.py")
            return {'jobs': [], 'error': 'Jooble API key not configured', 'total_count': 0}
        
        # Build API URL - Jooble uses POST request with API key in URL
        base_url = f"https://jooble.org/api/{JOOBLE_API_KEY}"
        
        # Jooble API heavily relies on keywords for specific Malaysian states.
        # We append the location (state) to the keywords, and strictly search 'Malaysia' as the location.
        combined_keywords = f"{keywords} {location}".strip() if location else keywords
        
        # Request payload
        payload = {
            'keywords': combined_keywords,
            'location': "Malaysia",
            'page': str(page)
        }
        
        print(f"📍 Jooble API - Searching for '{combined_keywords}' in 'Malaysia'")
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        response = requests.post(base_url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        jobs = []
        
        # Normalize Jooble job format to match our local format
        for result in data.get('jobs', []):
            # Parse salary if available
            salary_str = result.get('salary', '')
            salary_min = None
            salary_max = None
            if salary_str:
                # Try to extract numbers from salary string
                import re
                numbers = re.findall(r'[\d,]+', salary_str.replace(',', ''))
                if len(numbers) >= 2:
                    try:
                        salary_min = int(numbers[0])
                        salary_max = int(numbers[1])
                    except:
                        pass
                elif len(numbers) == 1:
                    try:
                        salary_min = int(numbers[0])
                    except:
                        pass
            
            job = {
                'title': result.get('title', 'Unknown Title'),
                'company': result.get('company', 'Unknown Company'),
                'description': result.get('snippet', '')[:500] + '...' if len(result.get('snippet', '')) > 500 else result.get('snippet', ''),
                'location': location if location else result.get('location', 'Malaysia'),
                'required_skills': '',  # Jooble doesn't provide skills directly
                'experience_required': 0,  # Not available from Jooble
                'salary_min': salary_min,
                'salary_max': salary_max,
                'salary_text': salary_str,
                'url': result.get('link', ''),
                'source': 'jooble',
                'created': result.get('updated', ''),
                'type': result.get('type', '')
            }
            jobs.append(job)
        
        total_count = data.get('totalCount', len(jobs))
        
        print(f"✅ Jooble API returned {len(jobs)} jobs for '{keywords}' in {country}")
        
        return {
            'jobs': jobs[:results_per_page],  # Limit results
            'total_count': total_count,
            'page': page,
            'results_per_page': results_per_page,
            'source': 'jooble',
            'country': country
        }
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Jooble API error: {e}")
        return {'jobs': [], 'error': str(e), 'total_count': 0}
    except Exception as e:
        print(f"❌ Unexpected error fetching Jooble jobs: {e}")
        return {'jobs': [], 'error': str(e), 'total_count': 0}

# --- Location-based Country Detection ---

# Mapping of location keywords to country codes
LOCATION_TO_COUNTRY = {
    # Malaysia
    'malaysia': 'my', 'kuala lumpur': 'my', 'kl': 'my', 'selangor': 'my', 'penang': 'my',
    'johor': 'my', 'johor bahru': 'my', 'jb': 'my', 'sabah': 'my', 'sarawak': 'my',
    'melaka': 'my', 'malacca': 'my', 'perak': 'my', 'ipoh': 'my', 'kedah': 'my',
    'pahang': 'my', 'kelantan': 'my', 'terengganu': 'my', 'perlis': 'my', 'cyberjaya': 'my',
    'putrajaya': 'my', 'petaling jaya': 'my', 'subang': 'my', 'shah alam': 'my',
    # Singapore
    'singapore': 'sg', 'sg': 'sg',
    # Philippines
    'philippines': 'ph', 'manila': 'ph', 'cebu': 'ph', 'davao': 'ph', 'quezon': 'ph',
    # Indonesia
    'indonesia': 'id', 'jakarta': 'id', 'surabaya': 'id', 'bandung': 'id', 'bali': 'id',
    # Thailand
    'thailand': 'th', 'bangkok': 'th', 'chiang mai': 'th', 'phuket': 'th',
    # Vietnam
    'vietnam': 'vn', 'ho chi minh': 'vn', 'hanoi': 'vn', 'saigon': 'vn',
    # Hong Kong
    'hong kong': 'hk', 'hongkong': 'hk',
    # Japan
    'japan': 'jp', 'tokyo': 'jp', 'osaka': 'jp', 'kyoto': 'jp',
    # South Korea
    'korea': 'kr', 'south korea': 'kr', 'seoul': 'kr', 'busan': 'kr',
    # Taiwan
    'taiwan': 'tw', 'taipei': 'tw',
    # India
    'india': 'in', 'bangalore': 'in', 'mumbai': 'in', 'delhi': 'in', 'hyderabad': 'in',
    'chennai': 'in', 'pune': 'in', 'kolkata': 'in', 'ahmedabad': 'in',
    # UK
    'uk': 'gb', 'united kingdom': 'gb', 'london': 'gb', 'manchester': 'gb', 'birmingham': 'gb',
    'england': 'gb', 'scotland': 'gb', 'wales': 'gb',
    # USA
    'usa': 'us', 'united states': 'us', 'america': 'us', 'new york': 'us', 'california': 'us',
    'los angeles': 'us', 'san francisco': 'us', 'seattle': 'us', 'chicago': 'us', 'texas': 'us',
    # Australia
    'australia': 'au', 'sydney': 'au', 'melbourne': 'au', 'brisbane': 'au', 'perth': 'au',
    # Germany
    'germany': 'de', 'berlin': 'de', 'munich': 'de', 'frankfurt': 'de', 'hamburg': 'de',
    # Canada
    'canada': 'ca', 'toronto': 'ca', 'vancouver': 'ca', 'montreal': 'ca', 'ottawa': 'ca',
    # UAE
    'uae': 'ae', 'dubai': 'ae', 'abu dhabi': 'ae',
}

def detect_country_from_location(location):
    """
    Detect the country code from a user's location string.
    Returns the country code (e.g., 'my', 'sg', 'us') or 'my' as default for Malaysia.
    """
    if not location:
        return 'my'  # Default to Malaysia
    
    location_lower = location.lower().strip()
    
    # Check for exact or partial matches
    for loc_keyword, country_code in LOCATION_TO_COUNTRY.items():
        if loc_keyword in location_lower:
            return country_code
    
    # Default to Malaysia if no match found
    return 'my'

def fetch_external_jobs_for_location(keywords, location, results_per_page=15):
    """
    Fetch external jobs using Jooble API for Malaysia only.
    System is designed specifically for the Malaysian job market.
    """
    # Always use Malaysia - system is designed for Malaysian job market
    country = 'my'
    
    print(f"📍 Fetching jobs for Malaysia using Jooble API")
    result = fetch_jooble_jobs(
        keywords=keywords,
        location=location,
        results_per_page=results_per_page,
        country=country
    )
    
    return result, country

def generate_recommendations_with_external(user):
    """Generate job recommendations from both local DB and external jobs based on location."""
    # Get local recommendations
    local_recommendations = generate_recommendations(user)
    
    # Fetch external jobs based on user skills AND location
    user_skills = user.get('skills', '')
    keywords = user_skills.split(',')[0].strip() if user_skills else 'developer'
    user_location = user.get('location', '')
    
    # Use smart location-based API selection
    external_result, detected_country = fetch_external_jobs_for_location(
        keywords=keywords, 
        location=user_location, 
        results_per_page=10
    )
    external_jobs = external_result.get('jobs', [])
    
    # Mark local jobs with source
    for job in local_recommendations:
        job['source'] = 'local'
    
    # Combine results
    combined = local_recommendations + external_jobs
    
    return {
        'local': local_recommendations,
        'external': external_jobs,
        'combined': combined,
        'detected_country': detected_country
    }

# --- API Endpoints ---

@app.route('/api/ai/status', methods=['GET'])
def ai_status():
    """Get AI engine status and capabilities."""
    if ai_engine_available:
        status = get_ai_status()
        return jsonify({
            'success': True,
            'ai_engine': status
        })
    else:
        return jsonify({
            'success': True,
            'ai_engine': {
                'ai_available': False,
                'model_name': None,
                'model_loaded': False,
                'features': {
                    'semantic_matching': False,
                    'ml_scoring': False,
                    'skill_extraction': False
                },
                'fallback': 'keyword_matching'
            }
        })


@app.route('/api/register', methods=['POST'])
def register_user():
    """Register a new user and automatically set as verified."""
    if not use_mongo:
         return jsonify({'error': 'MongoDB/Email configuration required for full registration.'}), 503
    try:
        data = request.json
        required_fields = ['name', 'email', 'password', 'phone', 'skills', 'experience', 'bio', 'location']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing field: {field}'}), 400
        
        email = data['email'].lower()

        if get_user_by_email(email):
            return jsonify({'error': 'Email already registered. Try logging in.'}), 400
        
        user = {
            'email': email,
            'name': data['name'],
            'password_hash': generate_password_hash(data['password'], method='pbkdf2:sha256'),
            'phone': data['phone'],
            'skills': data['skills'],
            'experience': int(data['experience']),
            'bio': data['bio'],
            'location': data['location'],
            'is_verified': True,  # Auto-verified
            'created_at': datetime.now().isoformat()
        }
        
        save_user(user)
        
        # No verification email needed
        return jsonify({
            'message': 'Registration successful! You may now login.',
            'user': {'email': email, 'is_verified': True}
        }), 201
        
    except ValueError:
        return jsonify({'error': 'Invalid value for experience. Must be a number.'}), 400
    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/verify_email/<token>')
def verify_email(token):
    """Verify user's email via token."""
    if not use_mongo:
         return jsonify({'error': 'MongoDB/Email configuration required for verification.'}), 503
    
    # Check token in database first
    token_doc = get_verification_token(token)
    
    # Verify the signed token
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=3600)
    except Exception:
        return jsonify({'error': 'The verification link is invalid or has expired.'}), 400
    
    # Check if token was used (if found in DB)
    if token_doc and token_doc.get('used'):
        return jsonify({'error': 'This verification link has already been used.'}), 400
        
    user = get_user_by_email(email)
    if not user:
        return jsonify({'error': 'User not found.'}), 404
        
    if user.get('is_verified'):
        return jsonify({'message': 'Email already verified. You can now log in.'}), 200
    
    # Mark token as used
    invalidate_token(token)
    
    # Update user as verified
    user['is_verified'] = True
    if '_id' in user:
        del user['_id']
    save_user(user)
    
    return """
        <script>
            alert('✅ Email verified successfully! You can now log in.');
            window.location.href = '/'; 
        </script>
        """

@app.route('/api/resend_verification', methods=['POST'])
def resend_verification():
    """Resend verification email to user."""
    if not use_mongo:
        return jsonify({'error': 'MongoDB/Email configuration required.'}), 503
    
    try:
        data = request.json
        email = data.get('email', '').lower()
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        user = get_user_by_email(email)
        
        if not user:
            return jsonify({'error': 'User not found. Please register first.'}), 404
        
        if user.get('is_verified'):
            return jsonify({'message': 'Email is already verified. You can log in.'}), 200
        
        # Send new verification email
        email_sent = send_verification_email(email)
        
        if email_sent:
            return jsonify({
                'message': 'Verification email sent. Please check your inbox.'
            }), 200
        else:
            return jsonify({'error': 'Failed to send verification email. Please try again.'}), 500
            
    except Exception as e:
        print(f"Resend verification error: {e}")
        return jsonify({'error': 'An error occurred. Please try again.'}), 500

@app.route('/api/forgot_password', methods=['POST'])
def forgot_password():
    """Send 6-digit password reset code to user's email."""
    try:
        data = request.json
        email = data.get('email', '').lower()
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        user = get_user_by_email(email)
        
        if not user:
            # For security, still return success message
            return jsonify({
                'success': True,
                'message': 'If an account with that email exists, a reset code has been sent.'
            }), 200
        
        # Generate and save 6-digit code
        code = generate_reset_code()
        save_reset_code(email, code)
        
        # Send code via email
        send_success = send_reset_code_email(email, code)
        
        if send_success:
            return jsonify({
                'success': True,
                'message': 'A 6-digit reset code has been sent to your email.'
            }), 200
        else:
            return jsonify({'error': 'Failed to send reset code. Please try again.'}), 500
            
    except Exception as e:
        print(f"Forgot password error: {e}")
        return jsonify({'error': 'An error occurred. Please try again.'}), 500

@app.route('/api/verify_reset_code', methods=['POST'])
def verify_reset_code_endpoint():
    """Verify the 6-digit reset code."""
    try:
        data = request.json
        email = data.get('email', '').lower()
        code = data.get('code', '')
        
        if not email or not code:
            return jsonify({'valid': False, 'error': 'Email and code are required'}), 400
        
        valid, message = verify_reset_code(email, code)
        
        if valid:
            return jsonify({
                'valid': True,
                'message': 'Code verified successfully'
            }), 200
        else:
            return jsonify({
                'valid': False,
                'error': message
            }), 400
            
    except Exception as e:
        print(f"Verify reset code error: {e}")
        return jsonify({'valid': False, 'error': 'An error occurred'}), 500

@app.route('/api/reset_password_with_code', methods=['POST'])
def reset_password_with_code():
    """Reset password after code verification."""
    try:
        data = request.json
        email = data.get('email', '').lower()
        code = data.get('code', '')
        new_password = data.get('new_password', '')
        
        if not email or not code or not new_password:
            return jsonify({'success': False, 'error': 'All fields are required'}), 400
        
        # Password strength validation
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            return jsonify({'success': False, 'error': error_msg}), 400
        
        # Verify the code is still valid and verified
        if not use_mongo:
            return jsonify({'success': False, 'error': 'Database not available'}), 503
            
        token_doc = tokens_collection.find_one({
            'email': email,
            'code': code,
            'type': 'password_reset_code',
            'verified': True,
            'used': False
        })
        
        if not token_doc:
            return jsonify({'success': False, 'error': 'Invalid or expired code. Please request a new one.'}), 400
        
        # Update user password
        user = get_user_by_email(email)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        # Update user password
        user['password_hash'] = generate_password_hash(new_password, method='pbkdf2:sha256')
        if '_id' in user:
            del user['_id']
        save_user(user)
        
        # Mark code as used
        tokens_collection.update_one(
            {'_id': token_doc['_id']},
            {'$set': {'used': True}}
        )
        
        return jsonify({
            'success': True,
            'message': 'Password reset successfully! You can now log in.'
        }), 200
        
    except Exception as e:
        print(f"Reset password error: {e}")
        return jsonify({'success': False, 'error': 'An error occurred'}), 500

@app.route('/api/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with valid token."""
    if not use_mongo:
        return jsonify({'error': 'MongoDB/Email configuration required for password reset.'}), 503
    
    # Verify token
    email = verify_password_reset_token(token)
    
    if not email:
        if request.method == 'GET':
            return """
                <script>
                    alert('❌ This password reset link is invalid or has expired. Please request a new one.');
                    window.location.href = '/';
                </script>
            """
        return jsonify({'error': 'Invalid or expired reset token'}), 400
    
    # GET request - show reset form
    if request.method == 'GET':
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Reset Password - AI JobMatch Pro</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gradient-to-br from-blue-50 to-indigo-100 min-h-screen flex items-center justify-center">
            <div class="bg-white p-8 rounded-xl shadow-lg max-w-md w-full">
                <h2 class="text-3xl font-bold mb-6 text-center text-gray-800">Reset Your Password</h2>
                <p class="text-gray-600 mb-6 text-center">Enter your new password for: <strong>{email}</strong></p>
                <form id="resetForm">
                    <div class="mb-4">
                        <label class="block text-sm font-medium text-gray-700 mb-2">New Password</label>
                        <input type="password" id="newPassword" class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500" required minlength="6" placeholder="Enter new password">
                    </div>
                    <div class="mb-6">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Confirm Password</label>
                        <input type="password" id="confirmPassword" class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500" required minlength="6" placeholder="Confirm new password">
                    </div>
                    <button type="submit" class="w-full bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700 transition">
                        Reset Password
                    </button>
                    <div id="message" class="mt-4 text-center"></div>
                </form>
            </div>
            <script>
                document.getElementById('resetForm').addEventListener('submit', async (e) => {{
                    e.preventDefault();
                    const newPassword = document.getElementById('newPassword').value;
                    const confirmPassword = document.getElementById('confirmPassword').value;
                    const messageDiv = document.getElementById('message');
                    
                    if (newPassword !== confirmPassword) {{
                        messageDiv.innerHTML = '<p class="text-red-600">Passwords do not match!</p>';
                        return;
                    }}
                    
                    if (newPassword.length < 6) {{
                        messageDiv.innerHTML = '<p class="text-red-600">Password must be at least 6 characters!</p>';
                        return;
                    }}
                    
                    try {{
                        const response = await fetch('/api/reset_password/{token}', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ new_password: newPassword }})
                        }});
                        
                        const data = await response.json();
                        
                        if (response.ok) {{
                            // Show styled success modal
                            document.body.innerHTML = `
                                <div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
                                    <div class="bg-white p-8 rounded-2xl shadow-2xl max-w-md w-full text-center">
                                        <div class="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                                            <svg class="w-12 h-12 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                                            </svg>
                                        </div>
                                        <h2 class="text-2xl font-bold text-gray-800 mb-4">Password Reset Successful!</h2>
                                        <p class="text-gray-600 mb-6">Your password has been updated. You can now login with your new password.</p>
                                        <a href="/index.html" class="inline-block w-full bg-indigo-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-indigo-700 transition duration-300 shadow-lg hover:shadow-xl">
                                            Back to Login
                                        </a>
                                    </div>
                                </div>
                            `;
                        }} else {{
                            messageDiv.innerHTML = '<p class="text-red-600">' + data.error + '</p>';
                        }}
                    }} catch (error) {{
                        messageDiv.innerHTML = '<p class="text-red-600">An error occurred. Please try again.</p>';
                    }}
                }});
            </script>
        </body>
        </html>
        """
    
    # POST request - process password reset
    try:
        data = request.json
        new_password = data.get('new_password')
        
        if not new_password:
            return jsonify({'error': 'New password is required'}), 400
        
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        user = get_user_by_email(email)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update password
        user['password_hash'] = generate_password_hash(new_password, method='pbkdf2:sha256')
        # User proved email ownership by clicking reset link, so verify them
        user['is_verified'] = True
        # Remove _id to prevent MongoDB immutable field error
        if '_id' in user:
            del user['_id']
        save_user(user)
        
        return jsonify({
            'message': 'Password has been reset successfully. You can now log in with your new password.'
        }), 200
        
    except Exception as e:
        print(f"Reset password error: {e}")
        return jsonify({'error': 'An error occurred. Please try again.'}), 500

@app.route('/api/login', methods=['POST'])
def login_user():
    """Login existing user."""
    try:
        data = request.json
        email = data.get('email', '').lower()
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        user = get_user_by_email(email)
        
        if not user:
            return jsonify({'error': 'Email or password is incorrect.'}), 401
            
        stored_hash = user.get('password_hash', '')
        
        # Check if the stored password is a hash (starts with pbkdf2: or scrypt:)
        is_hashed = stored_hash.startswith('pbkdf2:') or stored_hash.startswith('scrypt:')
        
        if is_hashed:
            try:
                if not check_password_hash(stored_hash, password):
                    return jsonify({'error': 'Email or password is incorrect.'}), 401
                # If old scrypt hash verified OK, re-hash with pbkdf2 for future logins
                if stored_hash.startswith('scrypt:'):
                    print(f"🔒 Re-hashing scrypt password to pbkdf2 for {email}")
                    user['password_hash'] = generate_password_hash(password, method='pbkdf2:sha256')
                    save_user(user)
            except (ValueError, AttributeError) as hash_err:
                # scrypt not supported on this system — prompt user to reset password
                print(f"⚠️ Cannot verify scrypt hash for {email}: {hash_err}")
                return jsonify({'error': 'Your account password needs to be reset. Please use Forgot Password to set a new one.'}), 401
        else:
            # Legacy plaintext fallback migration
            if stored_hash != password:
                return jsonify({'error': 'Email or password is incorrect.'}), 401
            # If match is successful, automatically upgrade their password to a hash
            print(f"🔒 Migrating legacy plaintext password to hash for {email}")
            user['password_hash'] = generate_password_hash(password, method='pbkdf2:sha256')
            save_user(user) # Save the upgraded hash back to the db
        
        # Email verification check disabled - allow direct login
        # if user.get('is_verified') is False:
        #     return jsonify({'error': 'Please verify your email address before logging in. Check your inbox.'}), 401

        recommendations = generate_recommendations(user)
        
        # Fetch external job recommendations based on user's skills AND location
        user_skills = user.get('skills', '')
        user_location = user.get('location', '')
        skill_list = [s.strip().lower() for s in user_skills.split(',') if s.strip()]
        
        # Priority technical skills for better job search results
        PRIORITY_SKILLS = {'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node', 'sql', 
                          'aws', 'azure', 'docker', 'kubernetes', 'tensorflow', 'pytorch', 'machine learning',
                          'data', 'c++', 'c#', 'go', 'rust', 'swift', 'kotlin', 'flutter', 'php', 'ruby',
                          'django', 'flask', 'spring', 'mongodb', 'postgresql', 'mysql', 'devops', 'cloud'}
        
        # Find priority skills first, then use others
        priority_matches = [s for s in skill_list if any(p in s for p in PRIORITY_SKILLS)]
        
        # Detect country first to determine search strategy
        detected_country = detect_country_from_location(user_location)
        jooble_countries = ['my', 'ph', 'id', 'th', 'vn', 'hk', 'pk', 'bd', 'jp', 'kr', 'tw', 'ae', 'sa']
        
        # Use only 1 keyword for Jooble Malaysia
        search_keywords = priority_matches[0] if priority_matches else 'developer'
        
        print(f"🔍 Login - Searching with keywords: '{search_keywords}' for location: '{user_location}' (Malaysia)")
        
        # Use Jooble for Malaysia
        external_result, detected_country = fetch_external_jobs_for_location(
            keywords=search_keywords,
            location=user_location,
            results_per_page=15
        )
        external_jobs = external_result.get('jobs', [])
        api_used = external_result.get('source', 'unknown')
        print(f"📊 Login - Found {len(external_jobs)} external jobs from {detected_country.upper()} ({api_used})")
        
        # Calculate match score for each external job based on user skills
        # External jobs already match the search keyword, so they get a baseline score
        user_exp = user.get('experience', 0)
        user_bio = user.get('bio', '').lower()
        
        for job in external_jobs:
            job_text = f"{job.get('title', '')} {job.get('description', '')} {job.get('category', '')}".lower()
            job_title = job.get('title', '').lower()
            job_location = job.get('location', '').lower()
            matched_skills = []
            for skill in skill_list:
                if match_skill_in_text(skill, job_text):
                    matched_skills.append(skill)
            
            # Calculate skill similarity (0-100%)
            if skill_list:
                skill_match_ratio = len(matched_skills) / len(skill_list)
                skill_similarity = round(skill_match_ratio * 100)
            else:
                skill_similarity = 50  # Default if no skills
            
            # Calculate location relevance (external jobs searched for Malaysia)
            location_relevance = 80 if 'malaysia' in job_location or user_location.lower() in job_location else 60
            
            # Experience fit - external jobs don't have experience requirements, so default to good fit
            experience_fit = 75
            
            # Title alignment - check if job title matches user bio keywords OR skills
            bio_keywords = [w.lower() for w in user_bio.split() if len(w) > 3]
            # Also include user skills for title matching (skills like 'python', 'engineer' often appear in titles)
            all_keywords = list(set(bio_keywords + skill_list))
            title_matches = sum(1 for kw in all_keywords if kw in job_title)
            title_alignment = min(round((title_matches / max(len(all_keywords), 1)) * 100), 100) if all_keywords else 50
            
            # Calculate weighted score (similar to local jobs)
            # Skills: 50%, Location: 15%, Experience: 25%, Title: 10%
            # But external jobs get baseline 50% since they matched search keyword
            base_score = 50
            bonus_score = (skill_similarity * 0.50) + (location_relevance * 0.15) + (experience_fit * 0.25) + (title_alignment * 0.10)
            match_score = round(base_score + (bonus_score * 0.5))  # Scale bonus to add up to 50 more
            
            job['match_score'] = min(match_score, 100)  # Cap at 100%
            job['matched_skills'] = matched_skills
            job['score_breakdown'] = {
                'skill_similarity': skill_similarity,
                'location_relevance': location_relevance,
                'experience_fit': experience_fit,
                'title_alignment': title_alignment
            }
        
        # Sort by match score (highest first) and take top 10
        external_jobs.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        external_recommendations = external_jobs[:10]
        
        user.pop('password_hash', None)
        
        return jsonify({
            'message': 'Login successful',
            'user': user,
            'recommendations': recommendations,
            'external_recommendations': external_recommendations
        }), 200
        
    except Exception as e:
        # If the ObjectId fix in get_user_by_email was missed in login, this catches it
        print(f"Login error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/index.html')
def serve_index():
    """Serve the main index.html file"""
    return send_from_directory(BASE_DIR, 'index.html')

# In app.py (Around Line 520)

@app.route('/api/profile', methods=['PUT'])
def update_profile():
    """Update existing user profile."""
    try:
        data = request.json
        email = data.get('email', '').lower()

        if not email:
            return jsonify({'error': 'Email is required for update'}), 400

        user = get_user_by_email(email)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        updateable_fields = ['name', 'phone', 'skills', 'experience', 'bio', 'location']
        
        updated = False
        for field in updateable_fields:
            # We get the user data using get_user_by_email, which returns a dictionary
            # that might contain the original _id. We check against the incoming data.
            if field in data and str(data[field]) != str(user.get(field)):
                if field == 'experience':
                    user[field] = int(data[field])
                else:
                    user[field] = data[field]
                updated = True

        if 'new_password' in data and data['new_password']:
             user['password_hash'] = generate_password_hash(data['new_password'], method='pbkdf2:sha256')
             updated = True

        if not updated:
            # Even if no changes, still return recommendations and external jobs
            recommendations = generate_recommendations(user)
            
            # Fetch external jobs
            user_skills = user.get('skills', '')
            skill_list = [s.strip().lower() for s in user_skills.split(',') if s.strip()]
            PRIORITY_SKILLS = {'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node', 'sql', 
                              'aws', 'azure', 'docker', 'kubernetes', 'tensorflow', 'pytorch', 'machine learning',
                              'data', 'c++', 'c#', 'go', 'rust', 'swift', 'kotlin', 'flutter', 'php', 'ruby',
                              'django', 'flask', 'spring', 'mongodb', 'postgresql', 'mysql', 'devops', 'cloud'}
            priority_matches = [s for s in skill_list if any(p in s for p in PRIORITY_SKILLS)]
            # Use single keyword for Jooble (Malaysia/Asia)
            user_loc = user.get('location', '')
            det_country = detect_country_from_location(user_loc)
            jooble_countries = ['my', 'ph', 'id', 'th', 'vn', 'hk', 'pk', 'bd', 'jp', 'kr', 'tw', 'ae', 'sa']
            if det_country in jooble_countries:
                search_keywords = priority_matches[0] if priority_matches else 'developer'
            else:
                search_keywords = ' '.join(priority_matches[:2]) if priority_matches else 'developer'
            print(f"🔍 Profile (no changes) - Searching with keywords: '{search_keywords}' for location: '{user_loc}'") 
            external_result, detected_country = fetch_external_jobs_for_location(
                keywords=search_keywords,
                location=user_loc,
                results_per_page=15
            )
            external_jobs = external_result.get('jobs', [])
            print(f"📊 Profile (no changes) - Found {len(external_jobs)} external jobs from {detected_country.upper()}")
            
            # Calculate match scores using comprehensive scoring (same as login)
            user_exp = user.get('experience', 0)
            user_bio = user.get('bio', '').lower()
            
            for job in external_jobs:
                job_text = f"{job.get('title', '')} {job.get('description', '')} {job.get('category', '')}".lower()
                job_title = job.get('title', '').lower()
                job_location = job.get('location', '').lower()
                matched_skills = [skill for skill in skill_list if match_skill_in_text(skill, job_text)]
                
                # Calculate skill similarity (0-100%)
                if skill_list:
                    skill_match_ratio = len(matched_skills) / len(skill_list)
                    skill_similarity = round(skill_match_ratio * 100)
                else:
                    skill_similarity = 50
                
                # Calculate location relevance
                location_relevance = 80 if 'malaysia' in job_location or user_loc.lower() in job_location else 60
                
                # Experience fit - external jobs don't have experience requirements
                experience_fit = 75
                
                # Title alignment
                bio_keywords = [w.lower() for w in user_bio.split() if len(w) > 3]
                all_keywords = list(set(bio_keywords + skill_list))
                title_matches = sum(1 for kw in all_keywords if kw in job_title)
                title_alignment = min(round((title_matches / max(len(all_keywords), 1)) * 100), 100) if all_keywords else 50
                
                # Calculate weighted score with 50% baseline
                base_score = 50
                bonus_score = (skill_similarity * 0.50) + (location_relevance * 0.15) + (experience_fit * 0.25) + (title_alignment * 0.10)
                match_score = round(base_score + (bonus_score * 0.5))
                
                job['match_score'] = min(match_score, 100)
                job['matched_skills'] = matched_skills
                job['score_breakdown'] = {
                    'skill_similarity': skill_similarity,
                    'location_relevance': location_relevance,
                    'experience_fit': experience_fit,
                    'title_alignment': title_alignment
                }
            
            external_jobs.sort(key=lambda x: x.get('match_score', 0), reverse=True)
            external_recommendations = external_jobs[:10]
            
            user.pop('password_hash', None)
            return jsonify({
                'message': 'No changes detected',
                'user': user,
                'recommendations': recommendations,
                'external_recommendations': external_recommendations
            }), 200

        # >>>>>>>>>>> FIX APPLIED HERE <<<<<<<<<<<
        # Remove the immutable _id field before passing the dictionary to save_user,
        # otherwise MongoDB will reject the update with the immutable field error.
        if '_id' in user:
            del user['_id']
        # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

        save_user(user)
        
        recommendations = generate_recommendations(user)
        
        # Fetch external job recommendations based on updated skills
        user_skills = user.get('skills', '')
        skill_list = [s.strip().lower() for s in user_skills.split(',') if s.strip()]
        
        # Use top skill as keyword for Jooble Malaysia search
        # Priority technical skills for better job search results
        PRIORITY_SKILLS = {'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node', 'sql', 
                          'aws', 'azure', 'docker', 'kubernetes', 'tensorflow', 'pytorch', 'machine learning',
                          'data', 'c++', 'c#', 'go', 'rust', 'swift', 'kotlin', 'flutter', 'php', 'ruby',
                          'django', 'flask', 'spring', 'mongodb', 'postgresql', 'mysql', 'devops', 'cloud'}
        
        # Find priority skills first
        priority_matches = [s for s in skill_list if any(p in s for p in PRIORITY_SKILLS)]
        
        # Use single keyword for Jooble Malaysia
        user_loc = user.get('location', '')
        search_keywords = priority_matches[0] if priority_matches else 'developer'
        print(f"🔍 Profile Update - Searching with keywords: '{search_keywords}' for location: '{user_loc}' (Malaysia)")
        external_result, detected_country = fetch_external_jobs_for_location(
            keywords=search_keywords,
            location=user_loc,
            results_per_page=15
        )
        external_jobs = external_result.get('jobs', [])
        print(f"📊 Profile Update - Found {len(external_jobs)} external jobs from {detected_country.upper()}")
        
        # Calculate match score for each external job using comprehensive scoring (same as login)
        user_exp = user.get('experience', 0)
        user_bio = user.get('bio', '').lower()
        
        for job in external_jobs:
            job_text = f"{job.get('title', '')} {job.get('description', '')} {job.get('category', '')}".lower()
            job_title = job.get('title', '').lower()
            job_location = job.get('location', '').lower()
            matched_skills = []
            for skill in skill_list:
                if match_skill_in_text(skill, job_text):
                    matched_skills.append(skill)
            
            # Calculate skill similarity (0-100%)
            if skill_list:
                skill_match_ratio = len(matched_skills) / len(skill_list)
                skill_similarity = round(skill_match_ratio * 100)
            else:
                skill_similarity = 50
            
            # Calculate location relevance
            location_relevance = 80 if 'malaysia' in job_location or user_loc.lower() in job_location else 60
            
            # Experience fit - external jobs don't have experience requirements
            experience_fit = 75
            
            # Title alignment
            bio_keywords = [w.lower() for w in user_bio.split() if len(w) > 3]
            all_keywords = list(set(bio_keywords + skill_list))
            title_matches = sum(1 for kw in all_keywords if kw in job_title)
            title_alignment = min(round((title_matches / max(len(all_keywords), 1)) * 100), 100) if all_keywords else 50
            
            # Calculate weighted score with 50% baseline
            base_score = 50
            bonus_score = (skill_similarity * 0.50) + (location_relevance * 0.15) + (experience_fit * 0.25) + (title_alignment * 0.10)
            match_score = round(base_score + (bonus_score * 0.5))
            
            job['match_score'] = min(match_score, 100)
            job['matched_skills'] = matched_skills
            job['score_breakdown'] = {
                'skill_similarity': skill_similarity,
                'location_relevance': location_relevance,
                'experience_fit': experience_fit,
                'title_alignment': title_alignment
            }
        
        # Sort by match score (highest first) and take top 10
        external_jobs.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        external_recommendations = external_jobs[:10]
        
        # When sending the user object back, we must ensure the _id (if present) is valid JSON, 
        # but since save_user doesn't return the updated doc, we just clean up and return the known state.
        user.pop('password_hash', None) 
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user,
            'recommendations': recommendations,
            'external_recommendations': external_recommendations
        }), 200
        
    except ValueError:
        return jsonify({'error': 'Invalid value for experience. Must be a number.'}), 400
    except Exception as e:
        print(f"Update profile error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def home():
    """API Health Check"""
    return jsonify({
        'status': 'online',
        'message': 'AI Job Recommendation System API',
        'version': '1.2.0 (Email Verification/Password Reset/MongoDB)',
        'database': 'MongoDB' if use_mongo else 'JSON Files (Local/Fallback)'
    })

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """Get all jobs"""
    jobs = get_all_jobs()
    return jsonify({'jobs': jobs}), 200

@app.route('/api/external-jobs', methods=['GET'])
def get_external_jobs():
    """Get jobs from Jooble API for Malaysia"""
    try:
        keywords = request.args.get('keywords', '')
        location = request.args.get('location', '')
        page = int(request.args.get('page', 1))
        results_per_page = int(request.args.get('limit', 20))
        
        # Always use Jooble for Malaysia
        result = fetch_jooble_jobs(
            keywords=keywords,
            location=location,
            page=page,
            results_per_page=results_per_page,
            country='my'
        )
        api_name = 'Jooble'
        
        if 'error' in result and result['error']:
            return jsonify({
                'jobs': [],
                'error': result['error'],
                'message': f'Failed to fetch jobs from {api_name}. Please check API credentials.',
                'api': api_name
            }), 503
        
        result['api'] = api_name
        return jsonify(result), 200
        
    except Exception as e:
        print(f"External jobs error: {e}")
        return jsonify({'error': str(e), 'jobs': []}), 500

@app.route('/api/upload-resume', methods=['POST'])
def upload_resume():
    """Upload, parse and SAVE resume to user profile. Only PDF and DOCX allowed."""
    if not resume_parser_available:
        return jsonify({
            'success': False,
            'error': 'Resume parser not available. Please install PyPDF2 and python-docx.'
        }), 503
    
    try:
        # Check if file was uploaded
        if 'resume' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No resume file provided. Please upload a PDF or DOCX file.'
            }), 400
        
        file = request.files['resume']
        email = request.form.get('email', '').lower().strip()
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected.'
            }), 400
        
        # Validate file type — ONLY PDF and DOCX allowed
        file_ext = os.path.splitext(file.filename.lower())[1]
        
        if file_ext not in ALLOWED_DOCUMENT_EXTENSIONS:
            return jsonify({
                'success': False,
                'error': f'Invalid file format: {file_ext}. Only PDF (.pdf) and Word (.docx) files are accepted. Please upload a valid resume.'
            }), 400
        
        # Read file bytes
        file_bytes = file.read()
        
        # Check file size (max 5MB)
        if len(file_bytes) > 5 * 1024 * 1024:
            return jsonify({
                'success': False,
                'error': 'File too large. Maximum size is 5MB.'
            }), 400
        # Save the file to disk
        safe_filename = secure_filename(file.filename)
        
        # Extract information using resume_parser
        extracted_data = {}
        try:
            from resume_parser import parse_resume
            parse_result = parse_resume(file_bytes, safe_filename)
            if parse_result.get('success'):
                extracted_data = {
                    'skills': parse_result.get('skills', []),
                    'personal_info': parse_result.get('personal_info', {})
                }

                # ── Terminal output for testing/verification ──────────────────
                print(f"\n{'='*55}")
                print(f"📄 RESUME PARSED: {safe_filename}")
                print(f"{'='*55}")
                print(f"  ✅ Skills extracted  : {parse_result.get('skills', [])}")
                info = parse_result.get('personal_info', {})
                print(f"  ✅ Name              : {info.get('name', 'Not found')}")
                print(f"  ✅ Email             : {info.get('email', 'Not found')}")
                print(f"  ✅ Phone             : {info.get('phone', 'Not found')}")
                print(f"  ✅ Location          : {info.get('location', 'Not found')}")
                print(f"  ✅ Biography         : {str(info.get('bio', 'Not found'))[:60]}...")
                print(f"{'='*55}\n")
                # ─────────────────────────────────────────────────────────────

                # Save extracted text to database so we don't have to parse it again later
                if use_mongo and email and 'full_text' in parse_result:
                    users_collection.update_one(
                        {'email': email},
                        {'$set': {'resume_text': parse_result['full_text']}}
                    )
        except Exception as e:
            print(f"⚠️ Non-fatal error during resume extraction: {e}")

        # Save the file to disk
        if email:
            user_resume_dir = os.path.join(RESUME_FOLDER, email.replace('@', '_at_'))
            os.makedirs(user_resume_dir, exist_ok=True)
            
            # Remove any previously saved resume for this user
            for old_file in os.listdir(user_resume_dir):
                os.remove(os.path.join(user_resume_dir, old_file))
            
            save_path = os.path.join(user_resume_dir, safe_filename)
            with open(save_path, 'wb') as f:
                f.write(file_bytes)
            
            # Update user profile with resume file info
            if use_mongo:
                update_data = {
                    'resume_file': safe_filename,
                    'resume_path': save_path,
                    'resume_uploaded_at': datetime.now().isoformat()
                }
                    
                users_collection.update_one(
                    {'email': email},
                    {'$set': update_data}
                )
            
            print(f"✅ Resume saved for {email}: {safe_filename}")
        
        response_data = {
            'success': True,
            'resume_saved': True if email else False,
            'resume_filename': safe_filename
        }
        
        # Merge extracted data into response
        response_data.update(extracted_data)
        
        return jsonify(response_data), 200
            
    except Exception as e:
        print(f"❌ Upload resume error: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/api/upload-cover-letter', methods=['POST'])
def upload_cover_letter():
    """Upload and save cover letter. Only PDF and DOCX allowed."""
    try:
        if 'cover_letter' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No cover letter file provided. Please upload a PDF or DOCX file.'
            }), 400
        
        file = request.files['cover_letter']
        email = request.form.get('email', '').lower().strip()
        
        if not email:
            return jsonify({
                'success': False,
                'error': 'Email is required to save cover letter.'
            }), 400
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected.'
            }), 400
        
        # Validate file type — ONLY PDF and DOCX allowed
        file_ext = os.path.splitext(file.filename.lower())[1]
        
        if file_ext not in ALLOWED_DOCUMENT_EXTENSIONS:
            return jsonify({
                'success': False,
                'error': f'Invalid file format: {file_ext}. Only PDF (.pdf) and Word (.docx) files are accepted. Please upload a valid cover letter.'
            }), 400
        
        # Read file bytes
        file_bytes = file.read()
        
        # Check file size (max 5MB)
        if len(file_bytes) > 5 * 1024 * 1024:
            return jsonify({
                'success': False,
                'error': 'File too large. Maximum size is 5MB.'
            }), 400
        
        # Save the file to disk
        safe_filename = secure_filename(file.filename)
        user_cl_dir = os.path.join(COVER_LETTER_FOLDER, email.replace('@', '_at_'))
        os.makedirs(user_cl_dir, exist_ok=True)
        
        # Remove any previously saved cover letter for this user
        for old_file in os.listdir(user_cl_dir):
            os.remove(os.path.join(user_cl_dir, old_file))
        
        save_path = os.path.join(user_cl_dir, safe_filename)
        with open(save_path, 'wb') as f:
            f.write(file_bytes)
        
        # Update user profile with cover letter file info
        if use_mongo:
            users_collection.update_one(
                {'email': email},
                {'$set': {
                    'cover_letter_file': safe_filename,
                    'cover_letter_path': save_path,
                    'cover_letter_uploaded_at': datetime.now().isoformat()
                }}
            )
        
        print(f"✅ Cover letter saved for {email}: {safe_filename}")
        
        return jsonify({
            'success': True,
            'message': 'Cover letter uploaded successfully.',
            'cover_letter_filename': safe_filename
        }), 200
        
    except Exception as e:
        print(f"❌ Upload cover letter error: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/api/user-documents', methods=['GET'])
def get_user_documents():
    """Get the current user's saved resume and cover letter filenames."""
    try:
        email = request.args.get('email', '').lower().strip()
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        user = get_user_by_email(email)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'resume_file': user.get('resume_file', None),
            'resume_uploaded_at': user.get('resume_uploaded_at', None),
            'cover_letter_file': user.get('cover_letter_file', None),
            'cover_letter_uploaded_at': user.get('cover_letter_uploaded_at', None)
        }), 200
        
    except Exception as e:
        print(f"❌ Get user documents error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/easy-apply', methods=['POST'])
def easy_apply():
    """Easy Apply to a job using saved resume and cover letter."""
    if not use_mongo:
        return jsonify({'error': 'Database not available'}), 503
    
    try:
        data = request.json
        email = data.get('email', '').lower().strip()
        job_title = data.get('job_title', '')
        job_company = data.get('job_company', '')
        job_location = data.get('job_location', '')
        job_source = data.get('job_source', 'local')  # 'local' or 'external'
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        if not job_title or not job_company:
            return jsonify({'error': 'Job title and company are required'}), 400
        
        user = get_user_by_email(email)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check that resume is uploaded
        if not user.get('resume_file'):
            return jsonify({
                'error': 'Please upload your resume before applying.',
                'missing': 'resume'
            }), 400

        
        # Check if already applied to this job
        existing = applications_collection.find_one({
            'email': email,
            'job_title': job_title,
            'job_company': job_company
        })
        
        if existing:
            return jsonify({
                'error': 'You have already applied to this job.',
                'already_applied': True
            }), 400
        
        # Record the application
        application = {
            'email': email,
            'user_name': user.get('name', ''),
            'job_title': job_title,
            'job_company': job_company,
            'job_location': job_location,
            'job_source': job_source,
            'resume_file': user.get('resume_file', ''),
            'cover_letter_file': user.get('cover_letter_file', ''),
            'applied_at': datetime.now().isoformat(),
            'status': 'applied'
        }
        
        applications_collection.insert_one(application)
        
        print(f"✅ {email} applied to {job_title} at {job_company}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully applied to {job_title} at {job_company}!',
            'application': {
                'job_title': job_title,
                'job_company': job_company,
                'applied_at': application['applied_at']
            }
        }), 201
        
    except Exception as e:
        print(f"❌ Easy apply error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/my-applications', methods=['GET'])
def get_my_applications():
    """Get list of jobs the user has applied to."""
    if not use_mongo:
        return jsonify({'applications': []}), 200
    
    try:
        email = request.args.get('email', '').lower().strip()
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        applications = list(applications_collection.find(
            {'email': email},
            {'_id': 0}
        ).sort('applied_at', -1))
        
        return jsonify({
            'applications': applications,
            'count': len(applications)
        }), 200
        
    except Exception as e:
        print(f"❌ Get applications error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download-resume', methods=['GET'])
def download_resume():
    """Download user's saved resume."""
    try:
        email = request.args.get('email', '').lower().strip()
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        user = get_user_by_email(email)
        if not user or not user.get('resume_file'):
            return jsonify({'error': 'No resume found'}), 404
        
        resume_path = user.get('resume_path', '')
        if not os.path.exists(resume_path):
            return jsonify({'error': 'Resume file not found on server'}), 404
        
        return send_file(resume_path, as_attachment=True, download_name=user['resume_file'])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download-cover-letter', methods=['GET'])
def download_cover_letter():
    """Download user's saved cover letter."""
    try:
        email = request.args.get('email', '').lower().strip()
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        user = get_user_by_email(email)
        if not user or not user.get('cover_letter_file'):
            return jsonify({'error': 'No cover letter found'}), 404
        
        cl_path = user.get('cover_letter_path', '')
        if not os.path.exists(cl_path):
            return jsonify({'error': 'Cover letter file not found on server'}), 404
        
        return send_file(cl_path, as_attachment=True, download_name=user['cover_letter_file'])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/all-jobs', methods=['GET'])
def get_all_jobs_combined():
    """Get combined local + external jobs"""
    try:
        keywords = request.args.get('keywords', '')
        location = request.args.get('location', '')
        
        # Get local jobs
        local_jobs = get_all_jobs()
        for job in local_jobs:
            job['source'] = 'local'
        
        # Get external jobs from Jooble Malaysia
        external_result = fetch_jooble_jobs(keywords=keywords, location=location, results_per_page=20, country='my')
        external_jobs = external_result.get('jobs', [])
        
        return jsonify({
            'local_jobs': local_jobs,
            'external_jobs': external_jobs,
            'total_local': len(local_jobs),
            'total_external': len(external_jobs)
        }), 200
        
    except Exception as e:
        print(f"All jobs error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs', methods=['POST'])
def post_job():
    """Post a new job"""
    try:
        data = request.json
        required_fields = ['title', 'company', 'description', 'required_skills', 'experience_required', 'location']
        
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing field: {field}'}), 400
        
        job = {
            'title': data['title'],
            'company': data['company'],
            'description': data['description'],
            'required_skills': data['required_skills'],
            'experience_required': int(data['experience_required']),
            'location': data['location']
        }
        
        if use_mongo:
            jobs_collection.insert_one(job)
        else:
            jobs = load_json(JOBS_DATA_FILE, [])
            jobs.append(job)
            save_json(JOBS_DATA_FILE, jobs)
        
        return jsonify({'message': 'Job posted successfully', 'job': job}), 201
        
    except ValueError:
        return jsonify({'error': 'Invalid value for experience_required. Must be a number.'}), 400
    except Exception as e:
        print(f"Post job error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get system statistics including local and external job counts"""
    users = get_all_users()
    jobs = get_all_jobs()
    
    local_jobs = len(jobs)
    external_jobs = 0
    
    # Try to get external job count from Jooble (quick search)
    try:
        result = fetch_jooble_jobs(keywords='', location='Malaysia', results_per_page=1)
        external_jobs = result.get('total_count', 0)
    except:
        external_jobs = 0  # Fallback if API fails
    
    return jsonify({
        'total_users': len(users),
        'total_jobs': local_jobs,
        'local_jobs': local_jobs,
        'external_jobs': external_jobs,
        'combined_jobs': local_jobs + external_jobs
    }), 200


# --- Ollama AI Endpoints ---

@app.route('/api/ollama/status', methods=['GET'])
def ollama_status():
    """Check Ollama availability and status"""
    if not ollama_available:
        return jsonify({
            'available': False,
            'error': 'Ollama engine module not loaded'
        }), 200
    
    status = get_ollama_status()
    return jsonify(status), 200


@app.route('/api/chat', methods=['POST'])
def ai_chat():
    """
    AI Chat endpoint for career advice and general questions.
    Uses Ollama qwen3:8b model.
    """
    if not ollama_available:
        return jsonify({'error': 'Ollama not available'}), 503
    
    data = request.json or {}
    message = data.get('message', '')
    user_email = data.get('email', '')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    # Get user context if available
    user = get_user_by_email(user_email) if user_email else None
    
    if user:
        response = get_career_advice(
            user_skills=user.get('skills', ''),
            user_experience=int(user.get('experience', 0)),
            user_bio=user.get('bio', ''),
            question=message
        )
    else:
        # Use get_career_advice even without user context to get hardcoded system responses
        response = get_career_advice(
            user_skills='',
            user_experience=0,
            user_bio='',
            question=message
        )
    
    return jsonify({
        'response': response,
        'model': 'qwen3:8b'
    }), 200


@app.route('/api/explain-match', methods=['POST'])
def explain_match():
    """
    Generate natural language explanation for why a job matches a user.
    """
    if not ollama_available:
        return jsonify({'error': 'Ollama not available'}), 503
    
    data = request.json or {}
    
    user_email = data.get('email')
    if not user_email:
        return jsonify({'error': 'Email is required'}), 400
    
    user = get_user_by_email(user_email)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    explanation = explain_job_match(
        user_skills=user.get('skills', ''),
        user_experience=int(user.get('experience', 0)),
        user_location=user.get('location', ''),
        job_title=data.get('job_title', ''),
        job_skills=data.get('job_skills', ''),
        job_location=data.get('job_location', ''),
        match_score=data.get('match_score', 0),
        score_breakdown=data.get('score_breakdown')
    )
    
    return jsonify({
        'explanation': explanation,
        'job_title': data.get('job_title', '')
    }), 200


@app.route('/api/extract-skills', methods=['POST'])
def extract_skills():
    """
    Extract skills from resume or profile text using AI.
    """
    if not ollama_available:
        return jsonify({'error': 'Ollama not available'}), 503
    
    data = request.json or {}
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    skills = extract_skills_from_text(text)
    
    return jsonify({
        'skills': skills,
        'skills_string': ', '.join(skills),
        'count': len(skills)
    }), 200


@app.route('/api/suggest-skills', methods=['POST'])
def suggest_skills():
    """
    Suggest skills to learn based on current skills and target role.
    """
    if not ollama_available:
        return jsonify({'error': 'Ollama not available'}), 503
    
    data = request.json or {}
    current_skills = data.get('current_skills', '')
    target_role = data.get('target_role', '')
    
    if not current_skills:
        return jsonify({'error': 'Current skills are required'}), 400
    
    suggestions = suggest_skills_to_learn(current_skills, target_role)
    
    return jsonify({
        'suggestions': suggestions,
        'target_role': target_role
    }), 200

@app.route('/api/generate-cover-letter', methods=['POST'])
def generate_ai_cover_letter():
    """Generate a cover letter using AI based on user profile and job details."""
    data = request.json
    email = data.get('email')
    job_title = data.get('job_title')
    job_company = data.get('job_company')
    
    if not email or not job_title or not job_company:
        return jsonify({'error': 'Missing required fields'}), 400
        
    user = get_user_by_email(email)
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    user_skills = user.get('skills', '')
    if isinstance(user_skills, list):
        user_skills = ', '.join(user_skills)
        
    from ollama_engine import generate_cover_letter
    cover_letter_text = generate_cover_letter(
        user_name=user.get('name', 'Applicant'),
        user_skills=user_skills,
        user_experience=user.get('experience', 0),
        job_title=job_title,
        job_company=job_company
    )
    
    return jsonify({
        'success': True,
        'cover_letter': cover_letter_text
    })

@app.route('/api/save-generated-cover-letter', methods=['POST'])
def save_generated_cover_letter():
    """Save the AI generated cover letter text as a file."""
    data = request.json
    email = data.get('email')
    text = data.get('text')
    
    if not email or not text:
        return jsonify({'error': 'Missing required fields'}), 400
        
    user = get_user_by_email(email)
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    # Create user-specific directory
    user_cl_folder = os.path.join(COVER_LETTER_FOLDER, email)
    os.makedirs(user_cl_folder, exist_ok=True)
    
    # Save as text file
    filename = 'ai_generated_cover_letter.txt'
    file_path = os.path.join(user_cl_folder, filename)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
            
        # Update user profile
        user['cover_letter_file'] = filename
        user['cover_letter_path'] = file_path
        user['cover_letter_uploaded_at'] = datetime.now().isoformat()
        
        update_data = user.copy()
        if '_id' in update_data:
            del update_data['_id']
        save_user(update_data)
        
        return jsonify({
            'success': True,
            'message': 'Cover letter saved successfully',
            'filename': filename
        })
    except Exception as e:
        print(f"Error saving generated cover letter: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/review-resume', methods=['POST'])
def api_review_resume():
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'Missing email'}), 400
        
    user = get_user_by_email(email)
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    resume_text = user.get('resume_text')
    
    # Fallback: if user uploaded resume before we started saving resume_text to db
    if not resume_text:
        resume_path = user.get('resume_path')
        if resume_path and os.path.exists(resume_path):
            try:
                with open(resume_path, 'rb') as f:
                    file_bytes = f.read()
                from resume_parser import parse_resume
                filename = os.path.basename(resume_path)
                res = parse_resume(file_bytes, filename)
                if res.get('success') and 'full_text' in res:
                    resume_text = res['full_text']
                    # Optionally cache it in DB for next time
                    if use_mongo:
                        users_collection.update_one({'email': email}, {'$set': {'resume_text': resume_text}})
            except Exception as e:
                print(f"Error parsing resume from disk: {e}")

    if not resume_text:
        return jsonify({'error': 'No resume text found. Please upload your resume first.'}), 400
        
    from ollama_engine import review_resume
    feedback = review_resume(resume_text)
    
    return jsonify({
        'success': True,
        'feedback': feedback
    })

@app.route('/api/analyze-gap', methods=['POST'])
def api_analyze_gap():
    data = request.json
    email = data.get('email')
    job_title = data.get('job_title')
    job_desc = data.get('job_description')
    
    if not email or not job_title or not job_desc:
        return jsonify({'error': 'Missing required fields'}), 400
        
    user = get_user_by_email(email)
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    user_skills = user.get('skills', '')
    if isinstance(user_skills, list):
        user_skills = ', '.join(user_skills)
        
    from ollama_engine import analyze_skill_gap
    analysis = analyze_skill_gap(user_skills, job_title, job_desc)
    
    return jsonify({
        'success': True,
        'gap_analysis': analysis
    })

# ==================== BOOKMARKS API ====================

@app.route('/api/bookmarks', methods=['POST'])
def add_bookmark():
    """Save a job to user's bookmarks."""
    if not use_mongo:
        return jsonify({'error': 'Database unavailable'}), 503
        
    try:
        data = request.json
        email = data.get('email')
        job = data.get('job')
        
        if not email or not job:
            return jsonify({'error': 'Email and job data required'}), 400
            
        # Add to bookmarks
        bookmark = {
            'email': email,
            'job': job,
            'job_title': job.get('title'),
            'job_company': job.get('company'),
            'saved_at': datetime.now().isoformat()
        }
        
        # Check if already bookmarked
        existing = bookmarks_collection.find_one({
            'email': email,
            'job_title': job.get('title'),
            'job_company': job.get('company')
        })
        
        if not existing:
            bookmarks_collection.insert_one(bookmark)
            
        return jsonify({'success': True}), 200
        
    except Exception as e:
        print(f"Error adding bookmark: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bookmarks', methods=['DELETE'])
def remove_bookmark():
    """Remove a job from user's bookmarks."""
    if not use_mongo:
        return jsonify({'error': 'Database unavailable'}), 503
        
    try:
        data = request.json
        email = data.get('email')
        job_title = data.get('job_title')
        job_company = data.get('job_company')
        
        if not email or not job_title or not job_company:
            return jsonify({'error': 'Missing required fields'}), 400
            
        bookmarks_collection.delete_one({
            'email': email,
            'job_title': job_title,
            'job_company': job_company
        })
            
        return jsonify({'success': True}), 200
        
    except Exception as e:
        print(f"Error removing bookmark: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bookmarks', methods=['GET'])
def get_bookmarks():
    """Get all bookmarked jobs for a user."""
    if not use_mongo:
        return jsonify({'bookmarks': []}), 200
        
    try:
        email = request.args.get('email')
        if not email:
            return jsonify({'error': 'Email required'}), 400
            
        bookmarks = list(bookmarks_collection.find(
            {'email': email},
            {'_id': 0}
        ).sort('saved_at', -1))
        
        # Extract just the job objects
        jobs = [b.get('job') for b in bookmarks if b.get('job')]
        
        return jsonify({'bookmarks': jobs}), 200
        
    except Exception as e:
        print(f"Error getting bookmarks: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== MAIN ====================


@app.route('/api/application-status', methods=['PUT'])
def update_application_status():
    data = request.json
    email = data.get('email')
    job_title = data.get('job_title')
    job_company = data.get('job_company')
    new_status = data.get('status')
    
    if not email or not job_title or not job_company or not new_status:
        return jsonify({'error': 'Missing required fields'}), 400
        
    try:
        from bson.objectid import ObjectId
        # Find the application
        result = applications_collection.update_one(
            {'email': email, 'job_title': job_title, 'job_company': job_company},
            {'$set': {'status': new_status}}
        )
        if result.matched_count == 0:
            return jsonify({'error': 'Application not found'}), 404
            
        return jsonify({'success': True, 'message': 'Status updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Disable debug/reloader to prevent deadlocks with AI libraries
    app.run(debug=False, port=5000)
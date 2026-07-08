"""
Ollama Engine Module for Job Recommendation System
Provides AI chat and embedding capabilities using local Ollama models.

Models used:
- qwen3:8b - For chat, explanations, and skill extraction
- qwen3-embedding (optional) - For advanced embeddings
"""

import requests
import json
from typing import Dict, List, Optional, Tuple

# Ollama configuration
OLLAMA_BASE_URL = "http://localhost:11434"
CHAT_MODEL = "qwen3:8b"  # Upgraded to 8B model for much smarter, high-quality responses
EMBEDDING_MODEL = "nomic-embed-text"  # Lightweight embedding model

_ollama_available = None


def clean_response(text: str) -> str:
    """
    Clean up AI response by removing markdown formatting and thinking tags.
    """
    import re
    # CRITICAL: Remove qwen3 <think>...</think> reasoning blocks first
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Remove markdown headers ### ## #
    text = re.sub(r'^#{1,3}\s*', '', text, flags=re.MULTILINE)
    # Remove horizontal rules ---
    text = re.sub(r'^-{3,}$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\*{3,}$', '', text, flags=re.MULTILINE)
    # Remove markdown bold **text**
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    # Remove markdown italic *text*
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    # Remove backticks `code`
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Remove arrow symbols
    text = text.replace('→', '-')
    text = text.replace('💎', '')
    text = text.replace('🔹', '•')
    text = text.replace('🔸', '•')
    text = text.replace('✅', '•')
    text = text.replace('❌', '•')
    # Clean up excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Clean up lines that are just whitespace
    text = re.sub(r'^\s*$\n', '', text, flags=re.MULTILINE)
    return text.strip()


def is_ollama_available() -> bool:
    """Check if Ollama is running and accessible."""
    global _ollama_available
    
    if _ollama_available is not None:
        return _ollama_available
    
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        _ollama_available = response.status_code == 200
        if _ollama_available:
            print("✅ Ollama is available and running")
        return _ollama_available
    except Exception as e:
        print(f"⚠️ Ollama not available: {e}")
        _ollama_available = False
        return False


def get_available_models() -> List[str]:
    """Get list of available Ollama models."""
    if not is_ollama_available():
        return []
    
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [model['name'] for model in data.get('models', [])]
        return []
    except Exception:
        return []


def chat_with_ollama(
    prompt: str,
    system_prompt: str = None,
    model: str = None,
    temperature: float = 0.7
) -> Tuple[str, bool]:
    """
    Chat with Ollama model.
    
    Args:
        prompt: User message/prompt
        system_prompt: Optional system prompt for context
        model: Model to use (defaults to CHAT_MODEL)
        temperature: Response creativity (0-1)
        
    Returns:
        Tuple of (response_text, success_bool)
    """
    if not is_ollama_available():
        return "Ollama is not available. Please ensure Ollama is running.", False
    
    model = model or CHAT_MODEL
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            },
            timeout=90  # Resume extraction needs more time
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('message', {}).get('content', ''), True
        else:
            return f"Error: {response.status_code}", False
            
    except requests.exceptions.Timeout:
        return "Request timed out. The model may be loading.", False
    except Exception as e:
        return f"Error: {str(e)}", False


def explain_job_match(
    user_skills: str,
    user_experience: int,
    user_location: str,
    job_title: str,
    job_skills: str,
    job_location: str,
    match_score: float,
    score_breakdown: Dict = None
) -> str:
    """
    Generate a natural language explanation of why a job matches a user.
    
    Args:
        user_skills: User's skills (comma-separated)
        user_experience: User's years of experience
        user_location: User's location
        job_title: Job title
        job_skills: Required job skills
        job_location: Job location
        match_score: Overall match percentage
        score_breakdown: Optional dict with component scores
        
    Returns:
        Natural language explanation
    """
    system_prompt = """You are a career advisor helping job seekers understand why certain jobs match their profile.
    Be concise, helpful, and encouraging. Focus on the key matching factors.
    Keep your response under 150 words."""
    
    breakdown_text = ""
    if score_breakdown:
        breakdown_text = f"""
Score Breakdown:
- Skill Match: {score_breakdown.get('skill_similarity', 'N/A')}%
- Experience Fit: {score_breakdown.get('experience_fit', 'N/A')}%
- Location Match: {score_breakdown.get('location_relevance', 'N/A')}%
- Career Alignment: {score_breakdown.get('title_alignment', 'N/A')}%"""
    
    prompt = f"""Explain why this job matches this candidate:

CANDIDATE PROFILE:
- Skills: {user_skills}
- Experience: {user_experience} years
- Location: {user_location}

JOB DETAILS:
- Title: {job_title}
- Required Skills: {job_skills}
- Location: {job_location}

MATCH SCORE: {match_score}%
{breakdown_text}

Provide a brief, encouraging explanation of why this is a good match and any areas for improvement."""

    response, success = chat_with_ollama(prompt, system_prompt)
    
    if success:
        return response
    else:
        # Fallback to simple explanation
        return f"This job has a {match_score}% match with your profile based on skill similarity, experience level, and location proximity."


def extract_skills_from_text(text: str) -> List[str]:
    """
    Extract technical and professional skills from resume or profile text.
    
    Args:
        text: Resume or profile text
        
    Returns:
        List of extracted skills
    """
    system_prompt = """You are a skill extraction expert. Extract technical skills, programming languages, 
    frameworks, tools, and professional skills from the given text.
    Return ONLY a comma-separated list of skills, nothing else.
    Focus on job-relevant skills like programming languages, frameworks, tools, and soft skills."""
    
    prompt = f"""Extract all technical and professional skills from this text:

{text[:2000]}  # Limit to first 2000 chars

Return only a comma-separated list of skills (e.g., Python, JavaScript, Project Management, SQL)."""

    response, success = chat_with_ollama(prompt, system_prompt, temperature=0.3)
    
    if success:
        # Parse comma-separated skills
        skills = [s.strip() for s in response.split(',') if s.strip()]
        # Remove any markdown or extra formatting
        skills = [s.strip('*').strip('-').strip() for s in skills]
        return skills[:20]  # Limit to 20 skills
    else:
        return []

def generate_cover_letter(user_name: str, user_skills: str, user_experience: int, job_title: str, job_company: str) -> str:
    """
    Generate a professional cover letter using AI.
    """
    system_prompt = """You are an expert career coach writing a professional, compelling cover letter.
    Write exactly 3 concise paragraphs.
    Do NOT include placeholder addresses like [Your Address] or [Date]. Start directly with "Dear Hiring Manager,".
    Keep the tone confident, professional, and directly highlight the candidate's skills and experience.
    Output only the body of the cover letter, nothing else."""
    
    prompt = f"""Write a cover letter for {user_name} applying for the {job_title} position at {job_company}.
    
    Candidate Profile:
    - Skills: {user_skills}
    - Years of Experience: {user_experience}
    
    Write a 3-paragraph letter:
    1. Introduction and excitement for the role
    2. Highlight relevant skills and experience
    3. Strong closing"""

    response, success = chat_with_ollama(prompt, system_prompt, temperature=0.7)
    
    if success:
        return clean_response(response)
    else:
        # Fallback if AI fails
        return f"Dear Hiring Manager,\n\nI am writing to express my strong interest in the {job_title} position at {job_company}. With {user_experience} years of experience and a strong background in {user_skills}, I am confident in my ability to contribute effectively to your team.\n\nThroughout my career, I have developed expertise that aligns well with the requirements of this role. I am eager to bring my skills to {job_company} and help drive your continued success.\n\nThank you for considering my application. I look forward to the opportunity to discuss how my background, skills, and certifications will be beneficial to your organization.\n\nSincerely,\n{user_name}"

def review_resume(resume_text: str) -> str:
    """
    Provide constructive, professional feedback on a resume.
    """
    system_prompt = """You are an expert, supportive career coach and tech recruiter.
    Analyze the provided resume text and provide exactly 3 bullet points of constructive feedback on how to improve it.
    Focus on areas like adding quantifiable metrics, strengthening action verbs, or highlighting skills better.
    Be encouraging, professional, and clear. Output only the 3 bullet points starting with an emoji."""
    
    prompt = f"Please review and critique this resume text:\n\n{resume_text[:2000]}"
    
    response, success = chat_with_ollama(prompt, system_prompt, temperature=0.7)
    if success:
        return clean_response(response)
    return "⚠️ Could not analyze resume at this time."

def analyze_skill_gap(user_skills: str, job_title: str, job_desc: str) -> str:
    """
    Identify missing skills between a user's profile and a job description.
    """
    system_prompt = """You are a career development coach.
    Compare the user's skills with the job description.
    List exactly 3 skills or technologies the user is MISSING or needs to improve to get this job.
    Format your response as a short, encouraging paragraph, followed by a bulleted list of the 3 missing skills."""
    
    prompt = f"User Skills: {user_skills}\n\nJob Title: {job_title}\nJob Description: {job_desc[:1500]}"
    
    response, success = chat_with_ollama(prompt, system_prompt, temperature=0.4)
    if success:
        return clean_response(response)
    return "⚠️ Could not analyze skill gap at this time."





def get_career_advice(
    user_skills: str,
    user_experience: int,
    user_bio: str,
    question: str
) -> str:
    """
    Provide personalized career advice based on user profile.
    
    Args:
        user_skills: User's skills
        user_experience: Years of experience
        user_bio: User's bio/description
        question: User's career question
        
    Returns:
        Career advice response
    """
    # Check if question is career-related BEFORE sending to LLM
    if not is_career_related(question):
        return "I'm your AI Career Advisor, and I specialize in helping with jobs, skills, and career guidance. I'm not able to help with that topic, but feel free to ask me anything about your career journey!"
    
    # Handle system-specific questions with hardcoded responses (more reliable than LLM)
    question_lower = question.lower()
    import re
    
    # === GREETINGS (use word boundary to avoid matching 'hi' in 'achieve') ===
    greeting_patterns = [r'\bhello\b', r'\bhi\b', r'\bhey\b', r'\bgood morning\b', r'\bgood afternoon\b', r'\bgood evening\b']
    is_greeting = any(re.search(pattern, question_lower) for pattern in greeting_patterns)
    # Only trigger greeting if the message is SHORT (just a greeting, not a question)
    if is_greeting and len(question_lower.split()) <= 5:
        return """Hello! 👋 Welcome to AI JobMatch Pro!

I'm your AI Career Assistant. How can I help you today?

Common questions I can help with:
• How to upload resume?
• How to use this system?
• What is match score?
• How to find jobs?
• How to update my profile?

Just type your question and I'll guide you! 😊"""
    
    # === RESUME UPLOAD ===
    has_upload = 'upload' in question_lower
    has_resume = 'resume' in question_lower or 'cv' in question_lower
    if has_upload and has_resume:
        return """📄 How to Upload Resume:

1. Click "Edit Profile" in the top menu
2. Scroll down to "Upload Resume" section
3. Click the upload area or drag your file
   (Supported: PDF, DOCX, JPG, PNG)
4. Wait for automatic skill extraction
5. Review and select the skills you want
6. Click "Use Selected Skills"
7. Click "Save Profile Changes"

Your skills will be extracted automatically! 🎉"""
    
    # === HOW TO USE SYSTEM ===
    if any(phrase in question_lower for phrase in ['how to use', 'how does this', 'how do i use', 'guide me', 'help me use', 'getting started', 'new user', 'first time']):
        return """🚀 Getting Started with AI JobMatch Pro:

1. Register/Login - Create your account first
2. Complete Profile - Add skills, experience, location
3. Upload Resume - Auto-extract skills (optional)
4. View Matches - Check "My Matches" for recommendations
5. Browse Jobs - See all jobs in "Jobs" tab
6. Apply Filter - Use slider for high-match jobs only

💡 Tip: The more complete your profile, the better your job matches!

Need help with anything specific? Just ask! 😊"""
    
    # === MATCH SCORE ===
    if any(word in question_lower for word in ['match score', 'score mean', 'percentage', 'how is score', 'scoring']):
        return """📊 Understanding Match Score:

Your match score shows job compatibility:

• Skills (50%) - Your skills vs job requirements
• Experience (25%) - Your years vs required experience
• Location (15%) - Job proximity to your location
• Title Fit (10%) - Career alignment with role

🎯 Higher score = Better match!

Use the filter slider to show only jobs above your preferred match percentage."""
    
    # === FIND/SEARCH JOBS ===
    if any(word in question_lower for word in ['find job', 'search job', 'look for job', 'browse job', 'see job', 'view job']):
        return """🔍 How to Find Jobs:

1. Go to "Jobs" tab - See all available positions
2. Check "My Matches" - View personalized recommendations
3. Use Match Filter - Slider to show high-match jobs only

💡 Job Sources:
• Local Jobs - From our database
• External Jobs - From Jooble API (Malaysia)

Complete your profile for better recommendations!"""
    
    # === EDIT/UPDATE PROFILE ===
    if any(word in question_lower for word in ['edit profile', 'update profile', 'change profile', 'modify profile', 'update skill', 'add skill', 'change skill']):
        return """✏️ How to Update Your Profile:

1. Click "Edit Profile" in the top menu
2. Update your information:
   • Skills - Add/remove your skills
   • Experience - Update years of experience
   • Location - Change your preferred location
   • Bio - Describe yourself
3. Click "Save Profile Changes"

💡 You can also upload a resume to auto-extract skills!"""
    
    # === REGISTER/SIGN UP ===
    if any(word in question_lower for word in ['register', 'sign up', 'create account', 'new account']):
        return """📝 How to Register:

1. Click "Register" button on the homepage
2. Fill in your details:
   • Name & Email
   • Skills (comma-separated)
   • Years of Experience
   • Location
   • Bio (optional)
3. Click "Create Account"

After registration, you'll see personalized job recommendations! 🎉"""
    
    # === LOGIN ISSUES ===
    if any(word in question_lower for word in ['login', 'log in', 'sign in', 'cannot login', 'forgot password']):
        return """🔐 Login Help:

To login:
1. Go to the homepage
2. Enter your registered email
3. Click "Login"

Having trouble?
• Make sure you've registered first
• Check your email spelling
• Try registering with a new email

Need more help? Just ask! 😊"""
    
    # === THANK YOU ===
    if any(word in question_lower for word in ['thank', 'thanks', 'thx', 'appreciate']):
        return """You're welcome! 😊

I'm always here to help you with:
• Job recommendations
• System navigation
• Career advice

Good luck with your job search! 🍀"""
    
    system_prompt = """You are the AI Career Assistant for AI JobMatch Pro, a Malaysian job recommendation system.

/no_think

YOUR IDENTITY: You help users with career advice, job searching, skill development, and navigating this system.

SYSTEM FEATURES:
- Register: Create account with name, email, skills, experience, location
- Upload Resume: Edit Profile > Upload Resume > Auto-extract skills
- My Matches: View personalized job recommendations
- Match Score: skill 50%, experience 25%, location 15%, title 10%
- Jobs Tab: Browse all available jobs with state filter
- Match Filter: Slider to filter by minimum match percentage

RESPONSE RULES:
1. Keep responses SHORT and CLEAR (under 80 words)
2. Do NOT use markdown formatting (no **, no ##, no backticks)
3. Use simple numbered lists or bullet points with dashes
4. Be friendly, encouraging, and professional
5. For system questions: Answer ONLY about THIS system (AI JobMatch Pro)
6. If the question is NOT about careers, jobs, skills, or this system, politely say: 'I specialize in career guidance and job recommendations. Please ask me about jobs, skills, or career advice!'
7. Do NOT ramble or repeat yourself
8. Give direct, actionable answers"""
    
    prompt = f"""USER PROFILE:
- Skills: {user_skills}
- Experience: {user_experience} years
- Bio: {user_bio}

USER QUESTION:
{question}

Please provide helpful career advice."""

    response, success = chat_with_ollama(prompt, system_prompt, temperature=0.4)
    
    if success:
        return clean_response(response)
    else:
        # Fallback responses when Ollama is unavailable
        return get_fallback_career_response(question, user_skills)


def get_fallback_career_response(question: str, user_skills: str = "") -> str:
    """
    Provide helpful fallback responses when Ollama is unavailable.
    Returns contextual advice based on keywords in the question.
    """
    q = question.lower()
    
    # System usage questions
    if any(kw in q for kw in ['upload resume', 'upload cv', 'how to upload']):
        return """Great question! 📄 Here's how to upload your resume:

1. Login to your account
2. Click 'Edit Profile' in the menu
3. Scroll to 'Upload Resume' section
4. Click the upload area or drag your file (PDF, DOCX, JPG, PNG)
5. Wait for automatic skill extraction - it's like magic! ✨
6. Click 'Use Selected Skills' to add them
7. Click 'Save Profile Changes'

I'll automatically detect your skills from your resume! 🎯"""

    if any(kw in q for kw in ['how to use', 'how does this work', 'getting started']):
        return """Welcome! 👋 I'm happy to help you get started!

Here's how to use AI JobMatch Pro:
1. Register an account with your skills and experience
2. Upload your resume - I'll extract your skills automatically!
3. Go to 'My Matches' to see personalized job recommendations
4. Use the match filter slider to find your perfect fit
5. Click on any job to see why it matches you
6. Browse all jobs in the 'Jobs' tab

Let me know if you need help with anything else! 😊"""

    # Skills-related questions
    if any(kw in q for kw in ['skill', 'learn', 'improve', 'develop', 'become']):
        # Try to detect specific roles mentioned
        role_advice = ""
        if any(role in q for role in ['driver', 'driving', 'delivery']):
            role_advice = """🚗 **To become a Driver:**
- Valid driving license (class D/E for commercial)
- Clean driving record
- GPS navigation skills
- Customer service skills
- Time management
- Basic vehicle maintenance knowledge

"""
        elif any(role in q for role in ['developer', 'programmer', 'coding', 'software']):
            role_advice = """� **To become a Developer:**
- Programming languages (Python, JavaScript, Java)
- Version control (Git)
- Problem-solving skills
- Understanding of databases
- Web frameworks or mobile development
- Continuous learning mindset

"""
        elif any(role in q for role in ['designer', 'design', 'ui', 'ux', 'graphic']):
            role_advice = """🎨 **To become a Designer:**
- Design tools (Figma, Adobe Creative Suite)
- Color theory and typography
- User experience principles
- Prototyping skills
- Attention to detail
- Portfolio of work

"""
        elif any(role in q for role in ['data', 'analyst', 'analytics']):
            role_advice = """📊 **To become a Data Analyst:**
- Excel/Google Sheets (advanced)
- SQL for database queries
- Data visualization (Tableau, Power BI)
- Basic statistics
- Python or R for analysis
- Critical thinking

"""
        elif any(role in q for role in ['manager', 'management', 'leader']):
            role_advice = """👔 **To become a Manager:**
- Leadership and communication
- Project management tools
- Team building skills
- Decision-making abilities
- Conflict resolution
- Strategic thinking

"""
        elif any(role in q for role in ['marketing', 'marketer', 'digital']):
            role_advice = """📱 **To become a Marketer:**
- Social media management
- Content creation
- SEO/SEM basics
- Analytics tools (Google Analytics)
- Email marketing
- Creativity and trend awareness

"""
        elif any(role in q for role in ['engineer', 'engineering', 'technical']):
            role_advice = """🔧 **To become an Engineer:**
- Strong foundation in math and science
- Technical/engineering degree (preferred)
- Problem-solving and analytical skills
- CAD software or programming (depending on field)
- Project management basics
- Attention to detail and safety standards

**Types of Engineering:**
• Software Engineer: Python, Java, system design
• Mechanical Engineer: CAD, mechanics, thermodynamics
• Electrical Engineer: circuits, electronics, control systems
• Civil Engineer: AutoCAD, structural analysis
• IT Engineer: networking, servers, troubleshooting

"""
        elif any(role in q for role in ['doctor', 'medical', 'physician', 'surgeon']):
            role_advice = """🩺 **To become a Doctor:**
- Medical degree (MBBS/MD) - 5-7 years
- Pre-med subjects: Biology, Chemistry, Physics
- Clinical rotations and internship
- Licensing exams (varies by country)
- Specialization training (optional)
- Strong communication and empathy
- Continuous medical education

"""
        elif any(role in q for role in ['nurse', 'nursing', 'healthcare']):
            role_advice = """👩‍⚕️ **To become a Nurse:**
- Nursing degree (Diploma/BSN)
- Clinical skills and patient care
- Medical terminology
- CPR and first aid certification
- Compassion and patience
- Physical stamina
- Attention to detail

"""
        elif any(role in q for role in ['teacher', 'teaching', 'educator', 'lecturer']):
            role_advice = """👩‍🏫 **To become a Teacher:**
- Teaching degree/certification
- Subject matter expertise
- Classroom management skills
- Patience and communication
- Lesson planning abilities
- Educational technology skills
- Continuous learning mindset

"""
        elif any(role in q for role in ['accountant', 'accounting', 'finance', 'auditor']):
            role_advice = """📊 **To become an Accountant:**
- Accounting degree or certification
- Knowledge of accounting principles (GAAP)
- Proficiency in Excel and accounting software
- Attention to detail
- Analytical skills
- Professional certifications (CPA, ACCA)
- Tax law knowledge

"""
        elif any(role in q for role in ['lawyer', 'legal', 'attorney', 'law']):
            role_advice = """⚖️ **To become a Lawyer:**
- Law degree (LLB/JD)
- Bar exam and licensing
- Strong research and writing skills
- Critical thinking and argumentation
- Public speaking abilities
- Knowledge of legal procedures
- Ethical judgment

"""
        elif any(role in q for role in ['chef', 'cook', 'culinary', 'kitchen']):
            role_advice = """👨‍🍳 **To become a Chef:**
- Culinary arts training/degree
- Food safety certification
- Kitchen equipment knowledge
- Creativity and presentation skills
- Time management under pressure
- Team leadership
- Menu planning and costing

"""
        elif any(role in q for role in ['pilot', 'aviation', 'flying', 'airline']):
            role_advice = """✈️ **To become a Pilot:**
- Pilot's license (PPL then CPL)
- Flight training hours (150-250+)
- Medical certificate
- Aviation English proficiency
- Physics and mathematics
- Quick decision-making
- Instrument rating certification

"""
        elif any(role in q for role in ['photographer', 'photography', 'camera']):
            role_advice = """📷 **To become a Photographer:**
- Camera operation and settings
- Lighting and composition
- Photo editing (Lightroom, Photoshop)
- Portfolio building
- Client communication
- Business/marketing skills
- Creativity and artistic eye

"""
        elif any(role in q for role in ['writer', 'writing', 'author', 'content', 'copywriter']):
            role_advice = """✍️ **To become a Writer:**
- Strong grammar and vocabulary
- Creative or technical writing skills
- Research abilities
- SEO knowledge (for digital content)
- Meeting deadlines
- Portfolio of published work
- Adaptability to different styles

"""
        elif any(role in q for role in ['sales', 'salesperson', 'selling', 'business development']):
            role_advice = """💼 **To become a Sales Professional:**
- Communication and persuasion skills
- Product/service knowledge
- Customer relationship management
- Negotiation abilities
- CRM software (Salesforce, HubSpot)
- Goal-oriented mindset
- Resilience and persistence

"""
        elif any(role in q for role in ['hr', 'human resource', 'recruitment', 'recruiter']):
            role_advice = """👥 **To become an HR Professional:**
- HR degree or certification
- Knowledge of labor laws
- Recruitment and interviewing skills
- Conflict resolution
- HRIS software proficiency
- Communication skills
- Confidentiality and ethics

"""
        elif any(role in q for role in ['mechanic', 'automotive', 'car repair', 'technician']):
            role_advice = """🔧 **To become a Mechanic:**
- Automotive/mechanical certification
- Diagnostic equipment knowledge
- Engine and parts expertise
- Problem-solving skills
- Physical stamina
- Customer service
- Safety procedures

"""
        elif any(role in q for role in ['electrician', 'electrical', 'wiring']):
            role_advice = """⚡ **To become an Electrician:**
- Electrical certification/license
- Understanding of electrical codes
- Safety procedures
- Blueprint reading
- Math and physics basics
- Manual dexterity
- Problem-solving skills

"""
        elif any(role in q for role in ['pharmacist', 'pharmacy', 'pharmaceutical']):
            role_advice = """💊 **To become a Pharmacist:**
- Pharmacy degree (BPharm/PharmD)
- Licensing exam
- Drug knowledge and interactions
- Patient counseling skills
- Attention to detail
- Chemistry background
- Healthcare regulations knowledge

"""
        elif any(role in q for role in ['architect', 'architecture', 'building design']):
            role_advice = """🏛️ **To become an Architect:**
- Architecture degree
- CAD/BIM software (AutoCAD, Revit)
- Design and creativity
- Building codes knowledge
- Project management
- 3D visualization skills
- Engineering principles

"""

        # If we have specific role advice, just return that with a friendly closing
        if role_advice:
            return f"""{role_advice}Good luck on your journey! If you need more specific advice or have questions about this career path, feel free to ask. �"""
        
        # Only show general tips when there's NO specific career advice
        return f"""Great question! Here are some tips to build your skills:

1. Browse job listings to see what employers want
2. Take online courses (Coursera, Udemy, LinkedIn Learning)
3. Practice with real projects or volunteer work
4. Get certifications relevant to your field
5. Network with professionals in your target industry

{("Your current skills (" + user_skills + ") are a great foundation!" if user_skills else "Tell me what career you're interested in, and I can give you more specific advice!")} 😊"""

    # Resume/CV questions
    if any(kw in q for kw in ['resume', 'cv', 'cover letter']):
        return """📝 Let's make your resume shine!

My top tips:
1. Keep it to 1-2 pages max
2. Use action verbs (developed, managed, created)
3. Quantify your achievements (increased sales by 20%)
4. Tailor your skills to each job application
5. Use a clean, professional format
6. Proofread carefully - typos matter!

Pro tip: Upload your resume here and I'll extract your skills automatically! 🎯"""

    # Job search questions - more conversational handling
    if any(kw in q for kw in ['job', 'find job', 'job search', 'apply', 'application']):
        # Check if it's an opinion/preference question
        if any(word in q for word in ['prefer', 'recommend', 'suggest', 'best', 'good for me', 'should i', 'what job']):
            if user_skills:
                return f"""That's a great question! 😊

Based on your skills ({user_skills}), I'd recommend exploring jobs that match your strengths! Here's what I suggest:

1. Check out 'My Matches' - I've already found jobs that fit your profile
2. Look for roles that use your strongest skills
3. Consider positions where you'd enjoy using those skills daily

Your skills are valuable! The best job for you is one where you enjoy the work and can grow. Would you like tips on a specific career path? Just ask! 🎯"""
            else:
                return """That's a great question! 😊

The best job for you depends on:
• What you enjoy doing
• Your natural strengths and skills  
• Your values and work-life preferences
• What you want to learn and where you want to grow

To help you better, try:
1. Adding your skills to your profile
2. Taking a career aptitude test online
3. Thinking about what activities make you lose track of time

Tell me what you're good at or interested in, and I can give specific suggestions! 🎯"""
        
        # General job search advice
        return f"""I'd love to help you find a job! 😊

Here's how to get started:
1. Make sure your profile has all your skills listed
2. Check 'My Matches' - I'll show you jobs that fit your profile
3. Jobs with 70%+ match are your best bet - apply to those first!
4. Customize your application for each role
5. Don't give up - the right job is out there for you!

{("With your skills in " + user_skills + ", you have great options!" if user_skills else "Add your skills to your profile and I'll find matching jobs for you!")}

What specific help do you need? 🎯"""

    # Interview questions
    if any(kw in q for kw in ['interview', 'prepare', 'question']):
        return """🎤 Interview time? Let's prepare you to shine!

My tips for success:
1. Research the company thoroughly
2. Practice common questions (Tell me about yourself, Why this role?)
3. Use the STAR method (Situation, Task, Action, Result)
4. Prepare questions to ask the interviewer
5. Dress professionally
6. Arrive 10-15 minutes early
7. Send a thank-you email within 24 hours

You're going to do great! Good luck! 🍀"""

    # Salary/Negotiation questions
    if any(kw in q for kw in ['salary', 'pay', 'negotiate', 'offer']):
        return """💰 Let's talk salary negotiation!

My tips:
1. Research market rates for your role and location
2. Consider total compensation (benefits, bonuses, equity)
3. Let them make the first offer if possible
4. Be confident but professional
5. Justify your ask with your skills and experience
6. Get the offer in writing

Remember: You deserve to be paid fairly for your skills! 💪"""

    # Career change questions
    if any(kw in q for kw in ['career change', 'switch', 'transition', 'new field']):
        return """🔄 Thinking about a career change? That's exciting!

Here's my advice:
1. Identify transferable skills from your current role
2. Take courses or certifications in the new field
3. Network with people in your target industry
4. Consider internships or volunteer work for experience
5. Update your resume to highlight relevant skills
6. Start with entry-level positions to gain experience

A new adventure awaits! 🚀"""

    # General career advice
    if any(kw in q for kw in ['advice', 'help', 'tip', 'recommend', 'suggest', 'career']):
        return """🌟 Here's my career advice for you!

1. Set clear short-term and long-term goals
2. Continuously learn and update your skills
3. Build a professional network
4. Seek feedback and mentorship
5. Keep your resume and profile updated
6. Stay positive and persistent

Use this system to find jobs that match your profile - I'm here to help! 😊"""

    # Default fallback - friendly greeting with topic list
    return """👋 Hi there! I'm your AI Career Assistant!

I'm here to help you with your career journey. Here's what I can help you with:

📄 **Resume & Profile**
   - How to upload your resume
   - Resume writing tips
   - Cover letter advice

💼 **Job Search**
   - Finding the right job
   - Job application tips
   - Using the matching system

🎯 **Skills & Growth**
   - What skills to learn
   - How to improve your skills
   - Career development advice

🎤 **Interviews**
   - Interview preparation
   - Common interview questions
   - What to wear and do

💰 **Salary & Offers**
   - Salary negotiation tips
   - Evaluating job offers

🔄 **Career Changes**
   - Switching industries
   - Transitioning to new roles

Just ask me anything related to jobs, careers, or skills! What would you like to know? 😊"""


def is_career_related(question: str) -> bool:
    """
    Check if a question is related to careers, jobs, skills, or system usage.
    Returns True if relevant, False otherwise.
    """
    question_lower = question.lower()
    
    # System usage keywords (made more specific to prevent off-topic matching)
    system_keywords = [
        'how to use this system', 'how to use this website', 'how do i register',
        'how to upload', 'upload resume', 'upload cv', 'my profile', 'edit profile',
        'match score', 'job recommendation', 'job filter', 'search jobs', 'find jobs'
    ]
    
    # Career-related keywords
    career_keywords = [
        # Jobs and work
        'job', 'jobs', 'work', 'career', 'careers', 'profession', 'employment',
        'employer', 'employee', 'hire', 'hiring', 'fired', 'resign', 'quit',
        'salary', 'pay', 'income', 'wage', 'wages', 'compensation',
        'interview', 'resume', 'cv', 'cover letter', 'application', 'apply',
        'promote', 'promotion', 'raise', 'bonus',
        
        # Skills and learning
        'skill', 'skills', 'learn', 'learning', 'study', 'course', 'courses',
        'certificate', 'certification', 'degree', 'training', 'workshop',
        'improve', 'development', 'develop', 'experience', 'expertise',
        'qualified', 'qualification', 'competency', 'ability',
        
        # Industries and roles
        'industry', 'sector', 'field', 'position', 'role', 'title',
        'manager', 'developer', 'engineer', 'analyst', 'designer',
        'intern', 'internship', 'junior', 'senior', 'lead', 'director',
        
        # Career actions
        'switch career', 'change job', 'find job', 'get hired', 'freelance',
        'remote', 'office', 'hybrid', 'company', 'startup', 'corporate',
        'portfolio', 'project', 'projects', 'networking', 'linkedin',
        
        # Advice seeking (must be combined with career context)
        'career advice', 'career path', 'career roadmap', 'job tips',
        'interview tips', 'resume help'
    ]
    
    # Check system keywords first
    for keyword in system_keywords:
        if keyword in question_lower:
            return True
    
    # Check if any career keyword is in the question
    for keyword in career_keywords:
        if keyword in question_lower:
            return True
    
    # If no keywords found, it's probably off-topic
    return False


def suggest_skills_to_learn(
    current_skills: str,
    target_job_title: str = None
) -> str:
    """
    Suggest skills to learn based on current skills and career goals.
    
    Args:
        current_skills: User's current skills
        target_job_title: Optional target job role
        
    Returns:
        Skill recommendations
    """
    system_prompt = """You are a career development expert. Suggest relevant skills for career growth.
    Focus on in-demand skills in the tech industry. Be specific and actionable."""
    
    target_text = f" for a {target_job_title} role" if target_job_title else ""
    
    prompt = f"""Based on these current skills: {current_skills}

Suggest 3-5 skills to learn{target_text}. For each skill:
1. Name the skill
2. Why it's valuable
3. How to start learning

Keep it concise and practical."""

    response, success = chat_with_ollama(prompt, system_prompt)
    
    if success:
        return response
    else:
        return "Unable to generate skill suggestions at this time."


def get_ollama_embedding(text: str) -> Optional[List[float]]:
    """
    Get embedding vector from Ollama.
    
    Args:
        text: Text to embed
        
    Returns:
        Embedding vector or None if unavailable
    """
    if not is_ollama_available():
        return None
    
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={
                "model": EMBEDDING_MODEL,
                "prompt": text
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('embedding')
        return None
        
    except Exception as e:
        print(f"Embedding error: {e}")
        return None


def get_ollama_status() -> Dict:
    """Get current Ollama status and available models."""
    available = is_ollama_available()
    models = get_available_models() if available else []
    
    return {
        'available': available,
        'base_url': OLLAMA_BASE_URL,
        'chat_model': CHAT_MODEL,
        'embedding_model': EMBEDDING_MODEL,
        'installed_models': models,
        'chat_model_ready': CHAT_MODEL in models or any(CHAT_MODEL.split(':')[0] in m for m in models)
    }


# Test function
if __name__ == "__main__":
    print("Testing Ollama Engine...")
    print(f"Status: {get_ollama_status()}")
    
    if is_ollama_available():
        # Test chat
        response, success = chat_with_ollama("Hello! What skills are important for a software developer?")
        print(f"\nChat test: {response[:200]}...")
        
        # Test skill extraction
        test_text = "I have experience with Python, JavaScript, and React. I've worked on machine learning projects using TensorFlow."
        skills = extract_skills_from_text(test_text)
        print(f"\nExtracted skills: {skills}")

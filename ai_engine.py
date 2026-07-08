"""
AI Engine Module for Job Recommendation System
Provides semantic skill matching and ML-based job scoring using:
- Sentence Transformers (all-MiniLM-L6-v2) for semantic embeddings
- Multinomial Naive Bayes for job category classification
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# Global variables for lazy loading
_model = None
_model_loading = False
_ai_available = False

# Naive Bayes classifier for job category prediction
_nb_classifier = None
_nb_vectorizer = None
_nb_trained = False

# Model configuration
MODEL_NAME = 'all-MiniLM-L6-v2'  # Small, fast, CPU-friendly model (~80MB)


def _load_model():
    """Lazy load the sentence transformer model."""
    global _model, _model_loading, _ai_available
    
    if _model is not None:
        return _model
    
    if _model_loading:
        return None
    
    _model_loading = True
    
    try:
        from sentence_transformers import SentenceTransformer
        print(f"🔄 Loading AI model ({MODEL_NAME})... This may take a moment on first run.")
        _model = SentenceTransformer(MODEL_NAME)
        _ai_available = True
        print("✅ AI Engine loaded successfully!")
        return _model
    except ImportError:
        print("⚠️ sentence-transformers not installed. AI features disabled.")
        print("   Run: pip install sentence-transformers")
        _ai_available = False
        return None
    except Exception as e:
        print(f"⚠️ Failed to load AI model: {e}")
        _ai_available = False
        return None
    finally:
        _model_loading = False


def is_ai_available() -> bool:
    """Check if AI features are available."""
    global _ai_available, _model
    if _model is None:
        _load_model()
    return _ai_available


def get_embedding(text: str) -> Optional[np.ndarray]:
    """
    Get embedding vector for a text string.
    
    Args:
        text: Input text to embed
        
    Returns:
        numpy array of embedding or None if unavailable
    """
    model = _load_model()
    if model is None:
        return None
    
    try:
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding
    except Exception as e:
        print(f"⚠️ Embedding error: {e}")
        return None


def get_embeddings_batch(texts: List[str]) -> Optional[np.ndarray]:
    """
    Get embeddings for multiple texts efficiently.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        numpy array of shape (n_texts, embedding_dim) or None
    """
    model = _load_model()
    if model is None:
        return None
    
    try:
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return embeddings
    except Exception as e:
        print(f"⚠️ Batch embedding error: {e}")
        return None


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    if vec1 is None or vec2 is None:
        return 0.0
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


# Skill synonyms and variations
SKILL_SYNONYMS = {
    'drive': ['driving', 'driver', 'drives'],
    'driving': ['drive', 'driver', 'drives'],
    'program': ['programming', 'programmer', 'programs'],
    'programming': ['program', 'programmer', 'programs'],
    'code': ['coding', 'coder'],
    'coding': ['code', 'coder'],
    'develop': ['development', 'developer', 'developing'],
    'development': ['develop', 'developer', 'developing'],
    'manage': ['management', 'manager', 'managing'],
    'management': ['manage', 'manager', 'managing'],
    'design': ['designing', 'designer', 'designs'],
    'test': ['testing', 'tester', 'tests'],
    'testing': ['test', 'tester', 'tests'],
    'analyze': ['analysis', 'analyst', 'analyzing'],
    'analysis': ['analyze', 'analyst', 'analyzing'],
    'write': ['writing', 'writer'],
    'writing': ['write', 'writer'],
    'cook': ['cooking', 'chef'],
    'cooking': ['cook', 'chef'],
    'clean': ['cleaning', 'cleaner'],
    'cleaning': ['clean', 'cleaner'],
    'teach': ['teaching', 'teacher'],
    'teaching': ['teach', 'teacher'],
    'sell': ['selling', 'sales', 'seller'],
    'sales': ['sell', 'selling', 'seller'],
}


def normalize_skill(skill: str) -> str:
    """
    Normalize a skill by removing common suffixes.
    Examples: driving -> drive, programming -> program
    """
    skill = skill.lower().strip()
    
    # Common suffix patterns to remove
    suffixes = ['ing', 'ment', 'tion', 'er', 'or', 'ist', 'ed', 's']
    
    # Don't stem very short words
    if len(skill) <= 4:
        return skill
    
    for suffix in suffixes:
        if skill.endswith(suffix) and len(skill) > len(suffix) + 2:
            stemmed = skill[:-len(suffix)]
            # Check if stemmed version is a valid base (not too short)
            if len(stemmed) >= 3:
                return stemmed
    
    return skill


def expand_skill_synonyms(skill: str) -> List[str]:
    """
    Expand a skill to include its synonyms and variations.
    Example: 'driving' -> ['driving', 'drive', 'driver', 'drives']
    """
    skill_lower = skill.lower().strip()
    synonyms = [skill_lower]
    
    if skill_lower in SKILL_SYNONYMS:
        synonyms.extend(SKILL_SYNONYMS[skill_lower])
    
    # Also add base form (stemmed)
    base_form = normalize_skill(skill_lower)
    if base_form != skill_lower:
        synonyms.append(base_form)
    
    return list(set(synonyms))  # Remove duplicates


def semantic_skill_similarity(user_skills: str, job_skills: str) -> Tuple[float, Dict]:
    """
    Calculate semantic similarity between user skills and job requirements.
    Uses a hybrid approach: exact/synonym matching PLUS AI semantic matching
    for remaining unmatched skills.
    
    Args:
        user_skills: Comma-separated user skills
        job_skills: Comma-separated job required skills
        
    Returns:
        Tuple of (similarity_score, details_dict)
    """
    model = _load_model()
    
    # Parse skills
    user_skill_list = [s.strip().lower() for s in user_skills.split(',') if s.strip()]
    job_skill_list = [s.strip().lower() for s in job_skills.split(',') if s.strip()]
    
    if not user_skill_list or not job_skill_list:
        return 0.0, {'matched_skills': [], 'similarity_matrix': [], 'no_skills': True}
    
    # Expand user skills with synonyms (drive -> [drive, driving, driver])
    expanded_user_skills = []
    original_skill_map = {}  # Map expanded skill back to original
    for skill in user_skill_list:
        expanded = expand_skill_synonyms(skill)
        for exp_skill in expanded:
            if exp_skill not in expanded_user_skills:
                expanded_user_skills.append(exp_skill)
                original_skill_map[exp_skill] = skill
    
    # Phase 1: Check for exact/synonym matches
    exact_matches = []
    matched_job_skills = set()
    for user_skill in expanded_user_skills:
        for job_skill in job_skill_list:
            if job_skill in matched_job_skills:
                continue
            user_base = normalize_skill(user_skill)
            job_base = normalize_skill(job_skill)
            if user_skill == job_skill or user_base == job_base:
                original = original_skill_map.get(user_skill, user_skill)
                exact_matches.append({
                    'job_skill': job_skill,
                    'user_skill': original,
                    'score': 1.0,
                    'match_type': 'exact'
                })
                matched_job_skills.add(job_skill)
    
    # Phase 2: For remaining unmatched job skills, try semantic matching
    unmatched_job_skills = [s for s in job_skill_list if s not in matched_job_skills]
    semantic_matches = []
    
    if unmatched_job_skills and model is not None:
        try:
            user_embeddings = get_embeddings_batch(user_skill_list)
            unmatched_embeddings = get_embeddings_batch(unmatched_job_skills)
            
            if user_embeddings is not None and unmatched_embeddings is not None:
                similarity_matrix = np.dot(unmatched_embeddings, user_embeddings.T)
                
                for i, job_skill in enumerate(unmatched_job_skills):
                    best_idx = np.argmax(similarity_matrix[i])
                    best_score = float(similarity_matrix[i][best_idx])
                    best_user_skill = user_skill_list[best_idx]
                    
                    # Use 0.5 threshold for semantic matches
                    if best_score > 0.5:
                        semantic_matches.append({
                            'job_skill': job_skill,
                            'user_skill': best_user_skill,
                            'score': best_score,
                            'match_type': 'semantic'
                        })
        except Exception as e:
            print(f"⚠️ Semantic matching error: {e}")
    
    # Combine results
    all_matches = exact_matches + semantic_matches
    total_job_skills = len(job_skill_list)
    
    if not all_matches:
        # No matches at all
        return 0.05, {
            'matched_skills': [],
            'method': 'no_match',
            'match_count': 0,
            'total_required': total_job_skills
        }
    
    # Calculate weighted score: exact matches count as 1.0, semantic by their score
    total_score = sum(m['score'] for m in all_matches)
    overall_score = total_score / total_job_skills
    
    return float(min(1.0, overall_score)), {
        'matched_skills': all_matches,
        'method': 'hybrid',
        'exact_count': len(exact_matches),
        'semantic_count': len(semantic_matches),
        'match_count': len(all_matches),
        'total_required': total_job_skills
    }


def calculate_experience_score(user_exp: int, job_exp: int) -> float:
    """
    Calculate experience fit score.
    
    Returns a score between 0 and 1:
    - 1.0 if user experience >= job requirement
    - Partial score if under-qualified
    - Slight penalty if significantly over-qualified
    """
    if job_exp <= 0:
        return 1.0
    
    if user_exp >= job_exp:
        # Over-qualified by more than 5 years gets slight penalty
        over_qualified_years = user_exp - job_exp
        if over_qualified_years > 5:
            return max(0.8, 1.0 - (over_qualified_years - 5) * 0.02)
        return 1.0
    else:
        # Under-qualified
        return user_exp / job_exp


# Malaysian location dictionary - maps states to their cities/areas
MALAYSIA_LOCATIONS = {
    'kuala lumpur': ['kuala lumpur', 'kl', 'bangsar', 'bangsar south', 'mid valley', 'bukit jalil', 'cheras', 'kepong', 'sentul', 'ampang', 'angkasapuri'],
    'selangor': ['petaling jaya', 'pj', 'shah alam', 'subang jaya', 'cyberjaya', 'sepang', 'port klang', 'setia alam', 'klang', 'kajang', 'puchong', 'damansara', 'kota damansara', 'usj'],
    'penang': ['penang', 'georgetown', 'bayan lepas', 'butterworth', 'bukit mertajam'],
    'johor': ['johor bahru', 'jb', 'iskandar', 'pasir gudang', 'senai', 'skudai'],
    'perak': ['ipoh', 'taiping', 'lumut'],
    'pahang': ['kuantan', 'gebeng', 'cameron highlands', 'genting'],
    'negeri sembilan': ['seremban', 'nilai', 'port dickson'],
    'melaka': ['melaka', 'malacca', 'ayer keroh'],
    'kedah': ['alor setar', 'langkawi', 'sungai petani'],
    'kelantan': ['kota bharu'],
    'terengganu': ['kuala terengganu'],
    'perlis': ['kangar'],
    'sabah': ['kota kinabalu', 'sandakan', 'tawau'],
    'sarawak': ['kuching', 'miri', 'sibu', 'bintulu'],
    'labuan': ['labuan'],
    'putrajaya': ['putrajaya'],
}

# Common abbreviations and aliases
LOCATION_ALIASES = {
    'kl': 'kuala lumpur',
    'pj': 'petaling jaya',
    'jb': 'johor bahru',
    'klia': 'sepang',
    'klia2': 'sepang',
}


def _normalize_location(location: str) -> str:
    """Normalize location by expanding aliases."""
    loc = location.lower().strip()
    return LOCATION_ALIASES.get(loc, loc)


def _get_state_for_location(location: str) -> Optional[str]:
    """Find which Malaysian state a location belongs to."""
    loc = _normalize_location(location)
    
    for state, cities in MALAYSIA_LOCATIONS.items():
        if loc == state or loc in cities:
            return state
        # Check if location contains any city name
        for city in cities:
            if city in loc or loc in city:
                return state
    return None


def calculate_location_score(user_location: str, job_location: str) -> float:
    """
    Calculate location relevance score with Malaysian state/city awareness.
    
    Scoring:
    - 1.0: Exact city/area match
    - 0.90: Same state (e.g., user in PJ, job in Cyberjaya - both Selangor)
    - 0.85: Adjacent regions (KL and Selangor)
    - 0.80: Remote/hybrid job
    - 0.5: Unknown location
    - 0.3: Different state/region
    """
    if not user_location or not job_location:
        return 0.5  # Unknown, neutral score
    
    user_loc = _normalize_location(user_location)
    job_loc = _normalize_location(job_location)
    
    # Exact match
    if user_loc == job_loc:
        return 1.0
    
    # Check if one contains the other
    if user_loc in job_loc or job_loc in user_loc:
        return 1.0
    
    # Check for remote/hybrid keywords
    remote_keywords = ['remote', 'work from home', 'wfh', 'hybrid', 'anywhere', 'various locations']
    if any(kw in job_loc for kw in remote_keywords):
        return 0.80
    
    # Get states for both locations
    user_state = _get_state_for_location(user_location)
    job_state = _get_state_for_location(job_location)
    
    if user_state and job_state:
        # Same state = high match
        if user_state == job_state:
            return 0.90
        
        # Adjacent regions: KL and Selangor are effectively one metro area
        kl_selangor = {'kuala lumpur', 'selangor', 'putrajaya'}
        if user_state in kl_selangor and job_state in kl_selangor:
            return 0.85
    
    # Partial word match fallback
    user_parts = set(user_loc.replace(',', ' ').split())
    job_parts = set(job_loc.replace(',', ' ').split())
    
    if user_parts.intersection(job_parts):
        return 0.70
    
    return 0.3


# ==================== MULTINOMIAL NAIVE BAYES CLASSIFIER ====================

# Predefined job categories for classification
JOB_CATEGORIES = [
    'Software Developer', 'Data Scientist', 'Web Developer', 'Mobile Developer',
    'DevOps Engineer', 'System Administrator', 'Database Administrator',
    'UI/UX Designer', 'Project Manager', 'Business Analyst', 'QA Engineer',
    'Security Engineer', 'Network Engineer', 'Cloud Engineer', 'AI/ML Engineer',
    'Full Stack Developer', 'Frontend Developer', 'Backend Developer',
    'Data Analyst', 'Product Manager'
]

# Training data: keywords associated with each job category
JOB_CATEGORY_KEYWORDS = {
    'Software Developer': 'programming coding software development java python c++ algorithms debugging applications',
    'Data Scientist': 'machine learning data science statistics python r tensorflow keras deep learning neural networks analytics',
    'Web Developer': 'html css javascript react angular vue web frontend backend nodejs php wordpress',
    'Mobile Developer': 'android ios swift kotlin flutter react native mobile app development',
    'DevOps Engineer': 'docker kubernetes jenkins ci/cd pipeline aws azure devops automation infrastructure',
    'System Administrator': 'linux windows server administration networking firewall system maintenance',
    'Database Administrator': 'sql mysql postgresql mongodb database administration query optimization backup',
    'UI/UX Designer': 'design figma sketch adobe user experience interface wireframe prototype usability',
    'Project Manager': 'project management agile scrum planning coordination stakeholder timeline budget',
    'Business Analyst': 'business analysis requirements documentation process improvement stakeholder communication',
    'QA Engineer': 'testing quality assurance automation selenium test cases bug tracking qa',
    'Security Engineer': 'cybersecurity security penetration testing encryption firewall vulnerability assessment',
    'Network Engineer': 'networking cisco router switch tcp/ip vpn lan wan configuration',
    'Cloud Engineer': 'aws azure gcp cloud computing infrastructure serverless lambda ec2',
    'AI/ML Engineer': 'artificial intelligence machine learning deep learning nlp computer vision tensorflow pytorch',
    'Full Stack Developer': 'fullstack full-stack frontend backend api database web application development',
    'Frontend Developer': 'html css javascript react angular vue frontend ui responsive design',
    'Backend Developer': 'api backend server node python java database rest graphql microservices',
    'Data Analyst': 'data analysis excel sql tableau power bi visualization reporting analytics',
    'Product Manager': 'product management roadmap strategy user research market analysis stakeholder'
}


def _train_naive_bayes():
    """
    Train Multinomial Naive Bayes classifier for job category prediction.
    Uses TF-IDF vectorization on job category keywords.
    """
    global _nb_classifier, _nb_vectorizer, _nb_trained
    
    if _nb_trained:
        return _nb_classifier, _nb_vectorizer
    
    try:
        from sklearn.naive_bayes import MultinomialNB
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        # Prepare training data
        texts = list(JOB_CATEGORY_KEYWORDS.values())
        labels = list(JOB_CATEGORY_KEYWORDS.keys())
        
        # Create TF-IDF vectorizer
        _nb_vectorizer = TfidfVectorizer(max_features=500, stop_words='english')
        X = _nb_vectorizer.fit_transform(texts)
        
        # Train Multinomial Naive Bayes
        _nb_classifier = MultinomialNB(alpha=1.0)
        _nb_classifier.fit(X, labels)
        
        _nb_trained = True
        print("✅ Naive Bayes classifier trained successfully!")
        return _nb_classifier, _nb_vectorizer
        
    except ImportError:
        print("⚠️ sklearn not installed. Naive Bayes features disabled.")
        return None, None
    except Exception as e:
        print(f"⚠️ Failed to train Naive Bayes: {e}")
        return None, None


def predict_job_category(user_bio: str, user_skills: str = '') -> Dict:
    """
    Predict the most suitable job category using Multinomial Naive Bayes.
    
    Args:
        user_bio: User's bio/description
        user_skills: User's skills (comma-separated)
        
    Returns:
        Dict with predicted category, probability, and all probabilities
    """
    classifier, vectorizer = _train_naive_bayes()
    
    if classifier is None or vectorizer is None:
        return {'category': 'Unknown', 'probability': 0.0, 'method': 'unavailable'}
    
    try:
        # Combine bio and skills for prediction
        combined_text = f"{user_bio} {user_skills}".lower()
        
        # Vectorize the input
        X = vectorizer.transform([combined_text])
        
        # Predict category and probabilities
        predicted_category = classifier.predict(X)[0]
        probabilities = classifier.predict_proba(X)[0]
        
        # Get probability for predicted category
        category_idx = list(classifier.classes_).index(predicted_category)
        confidence = probabilities[category_idx]
        
        # Get top 3 predictions
        top_indices = np.argsort(probabilities)[-3:][::-1]
        top_predictions = [
            {'category': classifier.classes_[i], 'probability': float(probabilities[i])}
            for i in top_indices
        ]
        
        return {
            'category': predicted_category,
            'probability': float(confidence),
            'top_predictions': top_predictions,
            'method': 'naive_bayes'
        }
        
    except Exception as e:
        print(f"⚠️ Job category prediction error: {e}")
        return {'category': 'Unknown', 'probability': 0.0, 'method': 'error'}


def calculate_title_fit_naive_bayes(
    user_bio: str,
    user_skills: str,
    job_title: str,
    job_description: str
) -> Tuple[float, Dict]:
    """
    Calculate job title fit using Multinomial Naive Bayes classification.
    
    Predicts user's suitable job category and compares with the job title.
    
    Args:
        user_bio: User's bio/description
        user_skills: User's skills
        job_title: Job title to match against
        job_description: Job description
        
    Returns:
        Tuple of (fit_score 0-1, details_dict)
    """
    # Get user's predicted job category
    user_prediction = predict_job_category(user_bio, user_skills)
    
    # Also predict what category this job belongs to
    job_text = f"{job_title} {job_description[:200] if job_description else ''}"
    job_prediction = predict_job_category(job_text, '')
    
    # Calculate fit score
    fit_score = 0.5  # Default neutral score
    
    if user_prediction['method'] != 'unavailable' and job_prediction['method'] != 'unavailable':
        # Exact category match
        if user_prediction['category'] == job_prediction['category']:
            fit_score = 0.9 + (user_prediction['probability'] * 0.1)  # 0.9 - 1.0
        else:
            # Check if job category is in user's top 3 predictions
            user_top_categories = [p['category'] for p in user_prediction.get('top_predictions', [])]
            if job_prediction['category'] in user_top_categories:
                # Partial match - in top 3
                idx = user_top_categories.index(job_prediction['category'])
                fit_score = 0.7 - (idx * 0.1)  # 0.7, 0.6, 0.5
            else:
                # No match - use raw probability comparison
                fit_score = 0.3 * user_prediction['probability']
    
    details = {
        'user_predicted_category': user_prediction.get('category', 'Unknown'),
        'user_confidence': user_prediction.get('probability', 0),
        'job_predicted_category': job_prediction.get('category', 'Unknown'),
        'job_confidence': job_prediction.get('probability', 0),
        'match_type': 'exact' if user_prediction.get('category') == job_prediction.get('category') else 'partial',
        'method': 'naive_bayes'
    }
    
    return float(min(1.0, max(0.0, fit_score))), details


def calculate_title_similarity(user_bio: str, job_title: str, job_description: str, user_skills: str = '') -> float:
    """
    Calculate how well the user profile matches the job title/role.
    
    Uses a hybrid approach:
    - Semantic embedding similarity (always reliable)
    - Naive Bayes category prediction (only when confident)
    """
    semantic_score = 0.5  # Default neutral
    nb_score = None
    
    # 1. Always try semantic similarity first (most reliable)
    model = _load_model()
    if model is not None and (user_bio or user_skills):
        try:
            user_text = f"{user_bio} Skills: {user_skills}" if user_skills else user_bio
            job_text = f"{job_title}. {job_description[:200]}" if job_description else job_title
            
            user_embedding = get_embedding(user_text)
            job_embedding = get_embedding(job_text)
            
            if user_embedding is not None and job_embedding is not None:
                similarity = cosine_similarity(user_embedding, job_embedding)
                semantic_score = float(max(0, min(1, similarity)))
        except Exception as e:
            print(f"⚠️ Title semantic similarity error: {e}")
    
    # 2. Try Naive Bayes as supplementary signal
    nb_result_score, nb_details = calculate_title_fit_naive_bayes(
        user_bio=user_bio,
        user_skills=user_skills,
        job_title=job_title,
        job_description=job_description
    )
    
    if nb_details.get('method') == 'naive_bayes':
        nb_confidence = nb_details.get('user_confidence', 0)
        # Only trust NB if it has reasonable confidence (> 20%)
        if nb_confidence > 0.20:
            nb_score = nb_result_score
    
    # 3. Blend scores
    if nb_score is not None:
        # Blend: 60% semantic + 40% Naive Bayes when NB is confident
        final_score = semantic_score * 0.6 + nb_score * 0.4
    else:
        # Pure semantic
        final_score = semantic_score
    
    return float(max(0, min(1, final_score)))


def calculate_ai_match_score(
    user_skills: str,
    job_skills: str,
    user_exp: int,
    job_exp: int,
    user_location: str = '',
    job_location: str = '',
    user_bio: str = '',
    job_title: str = '',
    job_description: str = ''
) -> Dict:
    """
    Calculate comprehensive AI-based job match score.
    
    Combines multiple signals:
    - Semantic skill similarity (50% weight)
    - Experience fit (25% weight)
    - Location relevance (15% weight)
    - Title/role alignment (10% weight)
    
    Returns:
        Dict with overall score and component breakdowns
    """
    # Calculate component scores
    skill_score, skill_details = semantic_skill_similarity(user_skills, job_skills)
    exp_score = calculate_experience_score(user_exp, job_exp)
    location_score = calculate_location_score(user_location, job_location)
    title_score = calculate_title_similarity(user_bio, job_title, job_description, user_skills)
    
    # Weighted combination matching methodology specification matching FYP proposal:
    # Final Score = (Skill x 0.50) + (Experience x 0.25) + (Location x 0.15) + (Title x 0.10)
    weights = {
        'skills': 0.50,      # Semantic skill matching (all-MiniLM-L6-v2)
        'experience': 0.25,  # Experience level fit
        'location': 0.15,    # Malaysian location intelligence
        'title_fit': 0.10    # Hybrid: semantic + Naive Bayes category prediction
    }
    
    overall_score = (
        skill_score * weights['skills'] +
        exp_score * weights['experience'] +
        location_score * weights['location'] +
        title_score * weights['title_fit']
    )
    
    # Scale to 0-100
    final_score = round(overall_score * 100, 2)
    
    return {
        'match_score': final_score,
        'ai_powered': is_ai_available(),
        'components': {
            'skill_similarity': round(skill_score * 100, 2),
            'experience_fit': round(exp_score * 100, 2),
            'location_relevance': round(location_score * 100, 2),
            'title_alignment': round(title_score * 100, 2)
        },
        'weights': weights,
        'skill_details': skill_details
    }


def extract_skills_semantic(text: str, skill_database: Dict[str, List[str]]) -> Dict:
    """
    Extract skills from text using semantic matching.
    
    Improves upon keyword matching by finding semantically similar skills
    even if they're not exact matches.
    
    Args:
        text: Resume or profile text
        skill_database: Dictionary of skill categories and skills
        
    Returns:
        Dict with extracted skills and confidence scores
    """
    model = _load_model()
    
    if model is None:
        return {'skills': [], 'method': 'ai_unavailable'}
    
    try:
        # Get embedding for the input text
        text_embedding = get_embedding(text.lower())
        
        if text_embedding is None:
            return {'skills': [], 'method': 'embedding_failed'}
        
        # Flatten skill database
        all_skills = []
        skill_to_category = {}
        for category, skills in skill_database.items():
            for skill in skills:
                all_skills.append(skill)
                skill_to_category[skill] = category
        
        # Get embeddings for all skills
        skill_embeddings = get_embeddings_batch(all_skills)
        
        if skill_embeddings is None:
            return {'skills': [], 'method': 'batch_embedding_failed'}
        
        # Calculate similarities
        similarities = np.dot(skill_embeddings, text_embedding)
        
        # Find skills with high similarity
        extracted_skills = []
        skills_by_category = {}
        
        threshold = 0.35  # Lower threshold to catch relevant skills
        
        for i, skill in enumerate(all_skills):
            if similarities[i] > threshold:
                category = skill_to_category[skill]
                skill_info = {
                    'skill': skill.title() if len(skill) > 3 else skill.upper(),
                    'confidence': float(similarities[i]),
                    'category': category
                }
                extracted_skills.append(skill_info)
                
                if category not in skills_by_category:
                    skills_by_category[category] = []
                skills_by_category[category].append(skill_info)
        
        # Sort by confidence
        extracted_skills.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Remove duplicates (keep highest confidence)
        seen_skills = set()
        unique_skills = []
        for skill_info in extracted_skills:
            skill_lower = skill_info['skill'].lower()
            if skill_lower not in seen_skills:
                seen_skills.add(skill_lower)
                unique_skills.append(skill_info)
        
        return {
            'skills': [s['skill'] for s in unique_skills[:30]],  # Top 30 skills
            'skills_with_confidence': unique_skills[:30],
            'skills_by_category': skills_by_category,
            'method': 'semantic',
            'total_found': len(unique_skills)
        }
        
    except Exception as e:
        print(f"⚠️ Semantic skill extraction error: {e}")
        return {'skills': [], 'method': 'error', 'error': str(e)}


def get_ai_status() -> Dict:
    """Get current AI engine status."""
    return {
        'ai_available': is_ai_available(),
        'model_name': MODEL_NAME,
        'model_loaded': _model is not None,
        'features': {
            'semantic_matching': is_ai_available(),
            'ml_scoring': is_ai_available(),
            'skill_extraction': is_ai_available()
        }
    }


# Pre-load model on module import (in background if possible)
def initialize():
    """Initialize the AI engine. Call this at application startup."""
    _load_model()


if __name__ == "__main__":
    # Test the AI engine
    print("Testing AI Engine...")
    print(f"AI Status: {get_ai_status()}")
    
    # Test semantic similarity
    user_skills = "Python, React, Machine Learning, SQL"
    job_skills = "Python programming, Frontend development, Data Science, Database management"
    
    score, details = semantic_skill_similarity(user_skills, job_skills)
    print(f"\nSemantic Skill Similarity: {score:.2f}")
    print(f"Details: {details}")
    
    # Test full scoring
    result = calculate_ai_match_score(
        user_skills=user_skills,
        job_skills=job_skills,
        user_exp=3,
        job_exp=2,
        user_location="Singapore",
        job_location="Singapore, Remote",
        user_bio="I am a software developer with experience in web development and data science",
        job_title="Full Stack Developer",
        job_description="Looking for a developer with Python and React experience"
    )
    print(f"\nAI Match Score: {result['match_score']}")
    print(f"Components: {result['components']}")

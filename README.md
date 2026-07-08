---

# AI Job Recommendation System

An intelligent job recommendation system leveraging machine learning and MongoDB to match users with suitable job opportunities based on their skills, experience, and locations.

---

## 🚀 Features

- **Skill-Based Recommendations**: Matches user skills with job requirements.  
- **Experience Filtering**: Recommends jobs aligning with the user's experience level.  
- **Automated Notifications**: Stores job recommendations as notifications in the database.  
- **MongoDB Integration**: Utilizes MongoDB for seamless data storage and retrieval.  

---

## 🛠️ Tech Stack

- **Python**  
- **MongoDB**  
- **scikit-learn** (Naive Bayes, TF-IDF Vectorizer, Label Encoding)  
- **pymongo**  

---

## 📂 Installation

1. **Clone the repository**:

```bash
git clone https://github.com/your-username/ai-job-recommendation.git
cd ai-job-recommendation
```

2. **Create a virtual environment and activate it**:

```bash
python -m venv venv
source venv/bin/activate  # On Windows use venv\\Scripts\\activate
```

3. **Install dependencies**:

```bash
pip install -r requirements.txt
```

4. **Configure MongoDB**:  
   Add your MongoDB URI in the `config.py` file:

```python
MONGO_URI = "mongodb://localhost:27017/" #replace with your connection string 
```

---

## ⚙️ Usage

1. **Run the script**:

```bash
python AIjobrecommendation.py
```

2. The system will:  
  - Fetch user profiles and job listings from MongoDB (when configured).  
  - Recommend suitable jobs based on skills and experience.  
  - Store recommendations as notifications (in MongoDB when configured).  
  - Display recommendations in the console.  

Note: If you do not provide a `config.py` with `MONGO_URI`, the script will fall back to using the local `profiles.json` and `jobs.json` files and will write recommendations to `notifications.json` in the project root. See `config.example.py` for an example.

---

## 📄 Sample match making data Format

```jobs.json
{
  "title": "Software Engineer",
  "description": "Develop machine learning models and optimize AI solutions.",
  "company": "TechCorp",
  "required_skills": "Python ML",
  "experience_required": 2,
  "location": "Chennai"
}
```

```userprofiles.json
{
  "name": "Moansri",
  "email": "monasri090@gmail.com",
  "skills": "Python ML Tensorflow",
  "experience": 2,
  "bio": "AI enthusiast with experience in ML models.",
  "location": "Chennai"
}
```

---

## 📚 Contributing

1. Fork the repository.  
2. Create your feature branch (`git checkout -b feature/recommendation-filter`).  
3. Commit your changes (`git commit -m 'Add experience level filter to job recommendations'`).  
4. Push to the branch (`git push origin feature/recommendation-filter`).  
5. Open a Pull Request.

---

## 🛡️ License

This project is licensed under the MIT License. See the [MIT License](LICENSE) file for details.

---

## 🤝 Acknowledgements

- Thanks to the open-source community for their valuable libraries and tools.

---

> Feel free to contribute, open issues, or provide feedback to make this project even better! 🚀

---

import json
import os
from pymongo import MongoClient

# Target states
new_jobs = [
    {
        "title": "Software Developer",
        "description": "Develop and maintain custom software solutions for local businesses.",
        "company": "Melaka Tech Solutions",
        "required_skills": "Python, JavaScript, HTML, CSS",
        "experience_required": 2,
        "location": "Melaka"
    },
    {
        "title": "Network Engineer",
        "description": "Manage and secure enterprise networks and infrastructure.",
        "company": "Borneo IT Services",
        "required_skills": "Networking, Cisco, CCNA, Cybersecurity",
        "experience_required": 3,
        "location": "Kuching, Sarawak"
    },
    {
        "title": "Data Analyst",
        "description": "Analyze operational data to improve supply chain efficiency in East Malaysia.",
        "company": "Sabah Logistics",
        "required_skills": "SQL, Excel, Data Analysis, PowerBI",
        "experience_required": 1,
        "location": "Kota Kinabalu, Sabah"
    },
    {
        "title": "IT Support Specialist",
        "description": "Provide technical support for hardware and software issues across multiple branches.",
        "company": "Kedah Retail Group",
        "required_skills": "IT Support, Windows Administration, Troubleshooting",
        "experience_required": 1,
        "location": "Alor Setar, Kedah"
    },
    {
        "title": "Web Developer",
        "description": "Design and build responsive websites for tourism and hospitality clients.",
        "company": "Heritage Web Design",
        "required_skills": "WordPress, PHP, React, UI/UX",
        "experience_required": 2,
        "location": "Melaka"
    },
    {
        "title": "System Administrator",
        "description": "Maintain Linux servers and manage database backups for government agencies.",
        "company": "Sarawak Govt IT Dept",
        "required_skills": "Linux, Bash, Database Administration",
        "experience_required": 4,
        "location": "Kuching, Sarawak"
    },
    {
        "title": "Digital Marketing Executive",
        "description": "Run social media campaigns to promote eco-tourism packages.",
        "company": "Sabah Eco Tours",
        "required_skills": "Social Media Marketing, SEO, Content Creation",
        "experience_required": 2,
        "location": "Sandakan, Sabah"
    },
    {
        "title": "Full Stack Engineer",
        "description": "Build modern e-commerce platforms for local SME clients.",
        "company": "East Coast Tech",
        "required_skills": "Node.js, React, MongoDB",
        "experience_required": 3,
        "location": "Kuala Terengganu, Terengganu"
    },
    {
        "title": "Database Administrator",
        "description": "Ensure high availability and performance of financial databases.",
        "company": "Kelantan Islamic Bank",
        "required_skills": "SQL Server, Oracle, Database Optimization",
        "experience_required": 5,
        "location": "Kota Bharu, Kelantan"
    },
    {
        "title": "Cloud Architect",
        "description": "Design cloud migration strategies for manufacturing plants.",
        "company": "Northern Tech Hub",
        "required_skills": "AWS, Azure, Cloud Computing",
        "experience_required": 5,
        "location": "Kangar, Perlis"
    },
    {
        "title": "Mobile App Developer",
        "description": "Develop mobile applications for public transport tracking.",
        "company": "Melaka Transit",
        "required_skills": "Flutter, React Native, Mobile Development",
        "experience_required": 2,
        "location": "Melaka"
    },
    {
        "title": "Machine Learning Engineer",
        "description": "Develop predictive models for agriculture and crop yield optimization.",
        "company": "AgriTech Sarawak",
        "required_skills": "Python, Machine Learning, Data Science",
        "experience_required": 3,
        "location": "Miri, Sarawak"
    },
    {
        "title": "Cybersecurity Analyst",
        "description": "Monitor and respond to security threats in regional networks.",
        "company": "Sabah Cyber Defense",
        "required_skills": "Cybersecurity, SIEM, Penetration Testing",
        "experience_required": 3,
        "location": "Kota Kinabalu, Sabah"
    },
    {
        "title": "Frontend Developer",
        "description": "Create engaging user interfaces for educational software.",
        "company": "Kedah EdTech",
        "required_skills": "Vue.js, HTML, CSS, JavaScript",
        "experience_required": 2,
        "location": "Sungai Petani, Kedah"
    },
    {
        "title": "Backend Developer",
        "description": "Develop robust APIs for logistics and tracking systems.",
        "company": "Terengganu Port Logistics",
        "required_skills": "Java, Spring Boot, REST API",
        "experience_required": 3,
        "location": "Kemaman, Terengganu"
    }
]

# Update jobs.json
file_path = 'jobs.json'
try:
    with open(file_path, 'r') as f:
        existing_jobs = json.load(f)
except Exception:
    existing_jobs = []

# Prevent duplicates if run multiple times
existing_titles_companies = set((j['title'], j['company']) for j in existing_jobs)

added_count = 0
for job in new_jobs:
    if (job['title'], job['company']) not in existing_titles_companies:
        existing_jobs.append(job)
        added_count += 1

with open(file_path, 'w') as f:
    json.dump(existing_jobs, f, indent=4)
print(f"Added {added_count} new jobs to jobs.json.")

# Attempt to update MongoDB
try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    client.server_info()
    db = client['job_recommendation_db']
    jobs_col = db['jobs']
    
    # Get existing in DB
    db_jobs = list(jobs_col.find({}, {"title": 1, "company": 1}))
    db_titles_companies = set((j['title'], j['company']) for j in db_jobs)
    
    db_added_count = 0
    for job in new_jobs:
        if (job['title'], job['company']) not in db_titles_companies:
            jobs_col.insert_one(job.copy())
            db_added_count += 1
            
    print(f"Added {db_added_count} new jobs to MongoDB.")
except Exception as e:
    print(f"MongoDB not updated (or not running): {e}")


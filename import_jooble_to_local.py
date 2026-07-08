import requests
import json
import random
import re
import os
import sys
from pymongo import MongoClient

# Pull API key from config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from config import JOOBLE_API_KEY
except ImportError:
    print("Cannot import JOOBLE_API_KEY")
    sys.exit(1)

if not JOOBLE_API_KEY or JOOBLE_API_KEY == 'YOUR_JOOBLE_API_KEY':
    print("Jooble API Key not found. Cannot fetch jobs.")
    sys.exit(1)

states = [
    "Kuala Lumpur", "Selangor", "Penang", "Johor", "Perak", 
    "Melaka", "Negeri Sembilan", "Pahang", "Kedah", "Terengganu", 
    "Kelantan", "Perlis", "Sabah", "Sarawak", "Labuan", "Putrajaya"
]

base_url = f"https://jooble.org/api/{JOOBLE_API_KEY}"
headers = {'Content-Type': 'application/json'}

new_jobs = []
max_pages_per_state = 1 # Just 1 page (20 jobs) per state to avoid massive payload

for state in states:
    print(f"Fetching Jooble jobs for {state}...")
    try:
        # Search for jobs specifically in this state
        payload = {
            'keywords': '',
            'location': f"{state}, Malaysia",
            'page': "1"
        }
        response = requests.post(base_url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            for job in data.get('jobs', []):
                title = job.get('title', '').strip()
                company = job.get('company', '').strip() or "Confidential Company"
                description = job.get('snippet', '').strip()
                
                # Strip HTML tags from description
                description = re.sub(r'<[^>]+>', '', description)
                
                # Parse salary if available
                salary_str = job.get('salary', '')
                salary_min = None
                salary_max = None
                if salary_str:
                    numbers = re.findall(r'\d+(?:,\d+)*', salary_str)
                    if len(numbers) >= 2:
                        salary_min = int(numbers[0].replace(',', ''))
                        salary_max = int(numbers[1].replace(',', ''))
                    elif len(numbers) == 1:
                        salary_min = int(numbers[0].replace(',', ''))
                        salary_max = salary_min + random.randint(1000, 3000)
                
                if not salary_min:
                    # Give realistic mock salary
                    base = random.randint(2500, 5000)
                    salary_min = base
                    salary_max = base + random.randint(1000, 3000)

                job_doc = {
                    "title": title,
                    "description": description[:300] + "..." if len(description) > 300 else description,
                    "company": company,
                    "required_skills": "",
                    "experience_required": random.randint(1, 5),
                    "location": state,  # Override Jooble's generic "Malaysia" with the actual state!
                    "salary_min": salary_min,
                    "salary_max": salary_max
                }
                new_jobs.append(job_doc)
    except Exception as e:
        print(f"Failed fetching for {state}: {e}")

print(f"Successfully fetched {len(new_jobs)} jobs from Jooble.")

if not new_jobs:
    sys.exit(0)

# 1. Update JSON files
file_path = 'jobs.json'
try:
    with open(file_path, 'r') as f:
        existing_jobs = json.load(f)
except Exception:
    existing_jobs = []

existing_titles_companies = set((j['title'], j['company']) for j in existing_jobs)

added_json = 0
for job in new_jobs:
    if (job['title'], job['company']) not in existing_titles_companies:
        existing_jobs.append(job)
        added_json += 1

with open(file_path, 'w') as f:
    json.dump(existing_jobs, f, indent=4)
with open('jobs_data.json', 'w') as f:
    json.dump(existing_jobs, f, indent=4)
print(f"Added {added_json} Jooble jobs to JSON files.")

# 2. Update MongoDB
try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    db = client.get_database('alumni_database')
    jobs_col = db['jobs']
    
    db_jobs = list(jobs_col.find({}, {"title": 1, "company": 1}))
    db_titles_companies = set((j['title'], j['company']) for j in db_jobs)
    
    db_added = 0
    for job in new_jobs:
        if (job['title'], job['company']) not in db_titles_companies:
            jobs_col.insert_one(job.copy())
            db_added += 1
            
    print(f"Added {db_added} Jooble jobs to alumni_database MongoDB.")
except Exception as e:
    print(f"MongoDB error: {e}")


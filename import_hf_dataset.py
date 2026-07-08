from datasets import load_dataset
from pymongo import MongoClient
import json
import random

print("Downloading dataset from Hugging Face...")
# We will load the dataset in streaming mode to just grab the first few hundred
dataset = load_dataset("azrai99/job-dataset", split="train", streaming=True)

new_jobs = []
max_jobs = 150  # Cap it so we don't blow up the frontend DOM

count = 0
for row in dataset:
    if count >= max_jobs:
        break
        
    # Example fields from standard job datasets on HF
    # job_title, company, location, job_description, category...
    title = row.get('job_title', '') or row.get('title', '')
    company = row.get('company', '')
    
    if not title or not company:
        continue
        
    description = row.get('job_description', '') or row.get('description', '')
    # Truncate extremely long descriptions so they don't break UI
    if len(description) > 300:
        description = description[:300] + "..."
        
    location = row.get('location', 'Malaysia')
    
    job_doc = {
        "title": title.strip(),
        "description": description.strip(),
        "company": company.strip(),
        "required_skills": "", # Can't always extract skills cleanly from dataset
        "experience_required": 0,
        "location": location.strip()
    }
    
    new_jobs.append(job_doc)
    count += 1

print(f"Downloaded {len(new_jobs)} jobs from Hugging Face.")

if not new_jobs:
    print("No jobs found in dataset.")
    exit(0)

# Update jobs.json
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
print(f"Added {added_json} real jobs to jobs.json.")

# Update MongoDB
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
            
    print(f"Added {db_added} real jobs to MongoDB.")
except Exception as e:
    print(f"MongoDB error: {e}")


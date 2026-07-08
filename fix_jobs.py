import json
from pymongo import MongoClient

file_path = 'jobs.json'
with open(file_path, 'r') as f:
    all_jobs = json.load(f)

# The new jobs are at the end of jobs.json, basically the whole file is now exactly what we want in the DB.
# Let's insert all 135 jobs into alumni_database.jobs if they don't exist

try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    client.server_info()
    db = client.get_database('alumni_database')
    jobs_col = db['jobs']
    
    db_jobs = list(jobs_col.find({}, {"title": 1, "company": 1}))
    db_titles_companies = set((j['title'], j['company']) for j in db_jobs)
    
    db_added_count = 0
    for job in all_jobs:
        if (job['title'], job['company']) not in db_titles_companies:
            jobs_col.insert_one(job.copy())
            db_added_count += 1
            
    print(f"Added {db_added_count} missing jobs to alumni_database MongoDB.")
except Exception as e:
    print(f"MongoDB not updated: {e}")


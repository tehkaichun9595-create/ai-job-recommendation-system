import json
import random
from pymongo import MongoClient

file_paths = ['jobs.json', 'jobs_data.json']

for file_path in file_paths:
    try:
        with open(file_path, 'r') as f:
            jobs = json.load(f)
            
        modified = False
        for job in jobs:
            if 'salary_min' not in job or 'salary_max' not in job:
                exp = job.get('experience_required', 0)
                base = 3000 + (exp * 1000)
                job['salary_min'] = base + random.randint(-500, 500)
                job['salary_max'] = job['salary_min'] + random.randint(1000, 4000)
                modified = True
                
        if modified:
            with open(file_path, 'w') as f:
                json.dump(jobs, f, indent=4)
            print(f"Updated salaries in {file_path}")
    except Exception as e:
        print(f"Error with {file_path}: {e}")

try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    db = client.get_database('alumni_database')
    jobs_col = db['jobs']
    
    db_jobs = list(jobs_col.find({}))
    updated = 0
    for job in db_jobs:
        if 'salary_min' not in job:
            exp = job.get('experience_required', 0)
            base = 3000 + (exp * 1000)
            sal_min = base + random.randint(-500, 500)
            sal_max = sal_min + random.randint(1000, 4000)
            
            jobs_col.update_one({'_id': job['_id']}, {'$set': {'salary_min': sal_min, 'salary_max': sal_max}})
            updated += 1
            
    print(f"Updated {updated} salaries in MongoDB alumni_database.jobs")
except Exception as e:
    print(f"MongoDB error: {e}")


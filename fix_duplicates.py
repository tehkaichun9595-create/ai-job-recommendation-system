import json
from pymongo import MongoClient

file_paths = ['jobs.json', 'jobs_data.json']

for path in file_paths:
    with open(path, 'r') as f:
        jobs = json.load(f)
    
    if len(jobs) > 331:
        good_jobs = jobs[:331]
        with open(path, 'w') as f:
            json.dump(good_jobs, f, indent=4)
        print(f"Restored {path} to 331 jobs.")

# Re-sync MongoDB
try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    db = client.get_database('alumni_database')
    jobs_col = db['jobs']
    
    jobs_col.delete_many({}) # Clear it all
    
    with open('jobs.json', 'r') as f:
        good_jobs = json.load(f)
        
    jobs_col.insert_many(good_jobs)
    print(f"Restored alumni_database.jobs to {len(good_jobs)} jobs.")
except Exception as e:
    print(f"MongoDB error: {e}")


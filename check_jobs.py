from config import MONGO_URI
import pymongo
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JOBS_STATIC_FILE = os.path.join(BASE_DIR, 'jobs.json')

print(f"Checking JOBS_STATIC_FILE: {JOBS_STATIC_FILE}")
if os.path.exists(JOBS_STATIC_FILE):
    print("✅ jobs.json exists")
    with open(JOBS_STATIC_FILE, 'r') as f:
        data = json.load(f)
        print(f"📄 Jobs in json file: {len(data)}")
else:
    print("❌ jobs.json NOT found")

try:
    print(f"\nChecking MongoDB: {MONGO_URI}")
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    db = client.get_database('alumni_database')
    jobs_collection = db['jobs']
    
    count = jobs_collection.count_documents({})
    print(f"✅ Connection successful!")
    print(f"💼 Total jobs in database: {count}")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")

import csv
import json
import os
import sys
from pymongo import MongoClient
import argparse

# Usage: python import_csv_dataset.py path/to/dataset.csv

def main():
    parser = argparse.ArgumentParser(description='Import jobs from CSV to MongoDB and jobs.json')
    parser.add_argument('csv_file', help='Path to the CSV file to import')
    args = parser.parse_args()

    if not os.path.exists(args.csv_file):
        print(f"Error: File '{args.csv_file}' not found.")
        sys.exit(1)

    new_jobs = []
    
    # Try to intelligently map CSV columns to our database schema
    print(f"Reading {args.csv_file}...")
    with open(args.csv_file, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        if not headers:
            print("Error: Empty CSV or no headers found.")
            sys.exit(1)
            
        headers_lower = [h.lower() for h in headers]
        
        # Mapping logic
        title_col = next((h for h in headers if 'title' in h.lower() or 'role' in h.lower()), None)
        desc_col = next((h for h in headers if 'desc' in h.lower() or 'summary' in h.lower()), None)
        comp_col = next((h for h in headers if 'company' in h.lower() or 'employer' in h.lower()), None)
        loc_col = next((h for h in headers if 'location' in h.lower() or 'city' in h.lower() or 'state' in h.lower()), None)
        skills_col = next((h for h in headers if 'skill' in h.lower() or 'requirement' in h.lower()), None)
        exp_col = next((h for h in headers if 'experience' in h.lower() or 'year' in h.lower()), None)

        if not title_col or not comp_col:
            print("Error: Could not identify 'Job Title' or 'Company' columns in the CSV.")
            print(f"Available columns: {headers}")
            sys.exit(1)

        print(f"Mapped columns:")
        print(f"  Title -> {title_col}")
        print(f"  Company -> {comp_col}")
        print(f"  Description -> {desc_col or 'N/A'}")
        print(f"  Location -> {loc_col or 'N/A'}")
        
        for row in reader:
            title = row.get(title_col, '').strip()
            company = row.get(comp_col, '').strip()
            
            if not title or not company:
                continue

            # Fallbacks for missing columns
            description = row.get(desc_col, f"Job opportunity at {company}") if desc_col else f"Job opportunity at {company}"
            location = row.get(loc_col, "Malaysia") if loc_col else "Malaysia"
            skills = row.get(skills_col, "") if skills_col else ""
            
            # Try to parse experience as integer
            exp_raw = row.get(exp_col, "0") if exp_col else "0"
            experience = 0
            try:
                import re
                numbers = re.findall(r'\d+', exp_raw)
                if numbers:
                    experience = int(numbers[0])
            except:
                pass

            job_doc = {
                "title": title,
                "description": description,
                "company": company,
                "required_skills": skills,
                "experience_required": experience,
                "location": location
            }
            new_jobs.append(job_doc)

    print(f"Successfully parsed {len(new_jobs)} jobs from CSV.")
    if len(new_jobs) == 0:
        sys.exit(0)

    # 1. Update jobs.json and jobs_data.json
    file_path = 'jobs.json'
    existing_jobs = []
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                existing_jobs = json.load(f)
        except Exception:
            pass

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
        
    print(f"Added {added_json} new jobs to jobs.json.")

    # 2. Update MongoDB
    try:
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
        client.server_info()
        db = client.get_database('alumni_database')
        jobs_col = db['jobs']
        
        db_jobs = list(jobs_col.find({}, {"title": 1, "company": 1}))
        db_titles_companies = set((j['title'], j['company']) for j in db_jobs)
        
        db_added = 0
        for job in new_jobs:
            if (job['title'], job['company']) not in db_titles_companies:
                jobs_col.insert_one(job.copy())
                db_added += 1
                
        print(f"Added {db_added} new jobs to alumni_database MongoDB.")
    except Exception as e:
        print(f"MongoDB not updated: {e}")

if __name__ == "__main__":
    main()


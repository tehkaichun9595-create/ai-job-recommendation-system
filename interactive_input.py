#!/usr/bin/env python3
"""Interactive input script to add user profiles and jobs to JSON files."""

import json
import os


def load_json(filepath):
    """Load JSON file or return empty list."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def save_json(filepath, data):
    """Save data to JSON file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f'✅ Saved to {filepath}')


def add_profile():
    """Interactive input for user profile."""
    print('\n--- Add New User Profile ---')
    profile = {}
    
    profile['name'] = input('Name: ').strip()
    profile['email'] = input('Email: ').strip()
    profile['skills'] = input('Skills (comma-separated, e.g., Python, ML, TensorFlow): ').strip()
    
    while True:
        try:
            profile['experience'] = int(input('Years of experience: ').strip())
            break
        except ValueError:
            print('Please enter a valid number.')
    
    profile['bio'] = input('Bio (brief description): ').strip()
    profile['location'] = input('Location (city): ').strip()
    
    return profile


def add_job():
    """Interactive input for job listing."""
    print('\n--- Add New Job Listing ---')
    job = {}
    
    job['title'] = input('Job Title: ').strip()
    job['description'] = input('Job Description: ').strip()
    job['company'] = input('Company Name: ').strip()
    job['required_skills'] = input('Required Skills (comma-separated): ').strip()
    
    while True:
        try:
            job['experience_required'] = int(input('Years of experience required: ').strip())
            break
        except ValueError:
            print('Please enter a valid number.')
    
    job['location'] = input('Location (city): ').strip()
    
    return job


def display_profiles(profiles):
    """Display all profiles."""
    if not profiles:
        print('No profiles found.')
        return
    
    print('\n--- User Profiles ---')
    for i, p in enumerate(profiles, 1):
        print(f'\n{i}. {p.get("name", "N/A")}')
        print(f'   Email: {p.get("email", "N/A")}')
        print(f'   Skills: {p.get("skills", "N/A")}')
        print(f'   Experience: {p.get("experience", 0)} years')
        print(f'   Bio: {p.get("bio", "N/A")}')
        print(f'   Location: {p.get("location", "N/A")}')


def display_jobs(jobs):
    """Display all jobs."""
    if not jobs:
        print('No jobs found.')
        return
    
    print('\n--- Job Listings ---')
    for i, j in enumerate(jobs, 1):
        print(f'\n{i}. {j.get("title", "N/A")} at {j.get("company", "N/A")}')
        print(f'   Description: {j.get("description", "N/A")}')
        print(f'   Required Skills: {j.get("required_skills", "N/A")}')
        print(f'   Experience Required: {j.get("experience_required", 0)} years')
        print(f'   Location: {j.get("location", "N/A")}')


def main():
    profiles_file = 'profiles.json'
    jobs_file = 'jobs.json'
    
    profiles = load_json(profiles_file)
    jobs = load_json(jobs_file)
    
    while True:
        print('\n========== AI Job Recommendation System ==========')
        print('1. Add User Profile')
        print('2. Add Job Listing')
        print('3. View All Profiles')
        print('4. View All Jobs')
        print('5. Run Recommendation Engine')
        print('6. Exit')
        print('==================================================')
        
        choice = input('\nEnter your choice (1-6): ').strip()
        
        if choice == '1':
            profile = add_profile()
            profiles.append(profile)
            save_json(profiles_file, profiles)
            print(f'✅ Profile for {profile["name"]} added!')
        
        elif choice == '2':
            job = add_job()
            jobs.append(job)
            save_json(jobs_file, jobs)
            print(f'✅ Job "{job["title"]}" at {job["company"]} added!')
        
        elif choice == '3':
            display_profiles(profiles)
        
        elif choice == '4':
            display_jobs(jobs)
        
        elif choice == '5':
            if not profiles or not jobs:
                print('⚠️  Please add at least one profile and one job before running recommendations.')
            else:
                print('\n⏳ Running recommendation engine...\n')
                os.system('python3 AIjobrecommendation.py')
        
        elif choice == '6':
            print('👋 Goodbye!')
            break
        
        else:
            print('Invalid choice. Please try again.')


if __name__ == '__main__':
    main()

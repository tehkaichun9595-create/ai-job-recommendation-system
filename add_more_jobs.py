import json
from pymongo import MongoClient

new_jobs = [
    {
        "title": "Registered Nurse",
        "description": "Provide compassionate care and administer treatments to patients in the critical care unit.",
        "company": "Melaka General Hospital",
        "required_skills": "Nursing, Patient Care, Critical Care, First Aid",
        "experience_required": 2,
        "location": "Melaka"
    },
    {
        "title": "Financial Advisor",
        "description": "Assist clients with wealth management, retirement planning, and investment strategies.",
        "company": "Sarawak Wealth Management",
        "required_skills": "Finance, Wealth Management, Investment, Communication",
        "experience_required": 3,
        "location": "Kuching, Sarawak"
    },
    {
        "title": "Logistics Coordinator",
        "description": "Manage shipping and receiving operations, ensuring timely delivery of goods.",
        "company": "Sabah Port Authority",
        "required_skills": "Logistics, Supply Chain, Coordination, MS Excel",
        "experience_required": 2,
        "location": "Kota Kinabalu, Sabah"
    },
    {
        "title": "Civil Engineer",
        "description": "Supervise local infrastructure projects including road expansion and bridge maintenance.",
        "company": "Kedah Construction Group",
        "required_skills": "AutoCAD, Civil Engineering, Project Management",
        "experience_required": 4,
        "location": "Alor Setar, Kedah"
    },
    {
        "title": "Hotel Operations Manager",
        "description": "Oversee daily hotel operations to guarantee an excellent experience for tourists.",
        "company": "Langkawi Resort Retreat",
        "required_skills": "Hospitality, Operations Management, Customer Service",
        "experience_required": 5,
        "location": "Langkawi, Kedah"
    },
    {
        "title": "Retail Branch Manager",
        "description": "Lead retail sales teams, manage inventory, and drive store profitability.",
        "company": "East Coast Retailers",
        "required_skills": "Retail Management, Sales, Leadership",
        "experience_required": 3,
        "location": "Kuala Terengganu, Terengganu"
    },
    {
        "title": "Medical Officer",
        "description": "Examine, diagnose, and treat patients in a rural clinic setting.",
        "company": "Kelantan Rural Health",
        "required_skills": "Medical Diagnosis, Healthcare, Patient Care",
        "experience_required": 1,
        "location": "Kota Bharu, Kelantan"
    },
    {
        "title": "Accountant",
        "description": "Handle tax filings, corporate accounts, and monthly financial reporting.",
        "company": "Perlis Financial Services",
        "required_skills": "Accounting, Tax, ACCA, Excel",
        "experience_required": 2,
        "location": "Kangar, Perlis"
    },
    {
        "title": "Mechanical Engineer",
        "description": "Maintain and optimize manufacturing equipment for the timber industry.",
        "company": "Sarawak Timber Processing",
        "required_skills": "Mechanical Engineering, Maintenance, CAD",
        "experience_required": 4,
        "location": "Sibu, Sarawak"
    },
    {
        "title": "Tour Guide",
        "description": "Lead eco-tours and provide historical insights to international tourists.",
        "company": "Melaka Heritage Tours",
        "required_skills": "Tourism, Communication, History, Multilingual",
        "experience_required": 1,
        "location": "Melaka"
    },
    {
        "title": "Marine Biologist",
        "description": "Conduct research on coral reef conservation and marine ecosystems.",
        "company": "Sabah Marine Conservation",
        "required_skills": "Marine Biology, Research, Diving, Data Collection",
        "experience_required": 3,
        "location": "Semporna, Sabah"
    },
    {
        "title": "Supply Chain Analyst",
        "description": "Analyze procurement data to reduce costs in agricultural logistics.",
        "company": "Kedah Agri-Logistics",
        "required_skills": "Supply Chain, Data Analysis, SQL",
        "experience_required": 2,
        "location": "Sungai Petani, Kedah"
    },
    {
        "title": "HR Manager",
        "description": "Manage recruitment, employee relations, and payroll for offshore operations.",
        "company": "Labuan Offshore Services",
        "required_skills": "Human Resources, Recruitment, Payroll, Labour Law",
        "experience_required": 5,
        "location": "Labuan"
    },
    {
        "title": "Pharmacist",
        "description": "Dispense medications and provide consultations to retail customers.",
        "company": "Kelantan Community Pharmacy",
        "required_skills": "Pharmacy, Healthcare, Customer Service",
        "experience_required": 1,
        "location": "Kota Bharu, Kelantan"
    },
    {
        "title": "Petroleum Engineer",
        "description": "Optimize drilling operations and ensure safety compliance on offshore rigs.",
        "company": "Terengganu O&G",
        "required_skills": "Petroleum Engineering, Safety, Drilling",
        "experience_required": 4,
        "location": "Kemaman, Terengganu"
    },
    {
        "title": "Sales Executive",
        "description": "Drive regional sales for automotive parts and build B2B relationships.",
        "company": "Perlis Auto Parts",
        "required_skills": "Sales, B2B, Negotiation, Communication",
        "experience_required": 2,
        "location": "Kangar, Perlis"
    },
    {
        "title": "Agricultural Scientist",
        "description": "Develop new fertilizers and pest control methods for local farmers.",
        "company": "Sarawak Agri-Research",
        "required_skills": "Agriculture, Science, Research, Biology",
        "experience_required": 3,
        "location": "Bintulu, Sarawak"
    },
    {
        "title": "Bank Teller",
        "description": "Handle day-to-day banking transactions and assist customers with inquiries.",
        "company": "Melaka Islamic Bank",
        "required_skills": "Banking, Customer Service, Cash Handling",
        "experience_required": 1,
        "location": "Melaka"
    },
    {
        "title": "Wildlife Conservation Officer",
        "description": "Monitor endangered species and enforce wildlife protection laws.",
        "company": "Sabah Wildlife Dept",
        "required_skills": "Conservation, Biology, Field Work",
        "experience_required": 3,
        "location": "Sandakan, Sabah"
    },
    {
        "title": "Compliance Officer",
        "description": "Ensure financial activities comply with offshore financial center regulations.",
        "company": "Labuan Financial Authority",
        "required_skills": "Compliance, Law, Finance, Auditing",
        "experience_required": 4,
        "location": "Labuan"
    }
]

# Update jobs.json
file_path = 'jobs.json'
try:
    with open(file_path, 'r') as f:
        existing_jobs = json.load(f)
except Exception:
    existing_jobs = []

existing_titles_companies = set((j['title'], j['company']) for j in existing_jobs)

added_count = 0
for job in new_jobs:
    if (job['title'], job['company']) not in existing_titles_companies:
        existing_jobs.append(job)
        added_count += 1

with open(file_path, 'w') as f:
    json.dump(existing_jobs, f, indent=4)
print(f"Added {added_count} non-tech jobs to jobs.json.")

# Attempt to update MongoDB
try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    client.server_info()
    db = client['job_recommendation_db']
    jobs_col = db['jobs']
    
    db_jobs = list(jobs_col.find({}, {"title": 1, "company": 1}))
    db_titles_companies = set((j['title'], j['company']) for j in db_jobs)
    
    db_added_count = 0
    for job in new_jobs:
        if (job['title'], job['company']) not in db_titles_companies:
            jobs_col.insert_one(job.copy())
            db_added_count += 1
            
    print(f"Added {db_added_count} non-tech jobs to MongoDB.")
except Exception as e:
    print(f"MongoDB not updated (or not running): {e}")


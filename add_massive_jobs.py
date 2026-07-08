import json
from pymongo import MongoClient

new_jobs = [
    # Johor
    {"title": "Factory Supervisor", "description": "Supervise manufacturing processes and ensure production targets are met.", "company": "Johor Manufacturing Hub", "required_skills": "Manufacturing, Leadership, Quality Control", "experience_required": 4, "location": "Johor Bahru, Johor"},
    {"title": "Customs Clerk", "description": "Handle cross-border logistics and import/export documentation.", "company": "JB Cross Border Logistics", "required_skills": "Logistics, Documentation, Customs", "experience_required": 1, "location": "Iskandar Puteri, Johor"},
    {"title": "Biomedical Engineer", "description": "Maintain and repair medical equipment in regional hospitals.", "company": "Southern Medical Solutions", "required_skills": "Biomedical Engineering, Maintenance", "experience_required": 3, "location": "Batu Pahat, Johor"},
    {"title": "Retail Store Assistant", "description": "Provide excellent customer service and manage retail stock.", "company": "Johor Premium Outlets", "required_skills": "Retail, Customer Service, Sales", "experience_required": 1, "location": "Kulai, Johor"},
    {"title": "Real Estate Agent", "description": "Sell and rent residential properties in the rapidly growing Iskandar region.", "company": "JB Properties", "required_skills": "Real Estate, Sales, Negotiation", "experience_required": 2, "location": "Johor Bahru, Johor"},

    # Pahang
    {"title": "Forestry Manager", "description": "Manage sustainable logging and reforestation efforts.", "company": "Pahang Timber Resources", "required_skills": "Forestry, Conservation, Management", "experience_required": 5, "location": "Kuantan, Pahang"},
    {"title": "Port Operations Executive", "description": "Coordinate ship loading and unloading schedules at the deepwater port.", "company": "Kuantan Port Authority", "required_skills": "Port Operations, Logistics, Coordination", "experience_required": 3, "location": "Kuantan, Pahang"},
    {"title": "Plantation Supervisor", "description": "Oversee daily operations of oil palm plantations and manage estate workers.", "company": "Pahang Agri Group", "required_skills": "Agriculture, Plantation Management", "experience_required": 3, "location": "Jerantut, Pahang"},
    {"title": "Chemical Process Technician", "description": "Monitor chemical processing lines in the Gebeng industrial zone.", "company": "Gebeng Petrochemicals", "required_skills": "Chemical Engineering, Safety, Monitoring", "experience_required": 2, "location": "Gebeng, Pahang"},
    {"title": "Resort Hospitality Manager", "description": "Manage operations for a luxury eco-resort in the highlands.", "company": "Cameron Highlands Resort", "required_skills": "Hospitality Management, Customer Service", "experience_required": 4, "location": "Cameron Highlands, Pahang"},

    # Perak
    {"title": "Quality Assurance Inspector", "description": "Inspect electronic components for defects before shipping.", "company": "Ipoh Electronics", "required_skills": "QA, Inspection, Attention to Detail", "experience_required": 2, "location": "Ipoh, Perak"},
    {"title": "History Teacher", "description": "Teach history to secondary school students with a focus on local heritage.", "company": "Perak Heritage School", "required_skills": "Teaching, History, Education", "experience_required": 2, "location": "Taiping, Perak"},
    {"title": "Automotive Mechanic", "description": "Diagnose and repair vehicles for a major automotive service center.", "company": "Perak Auto Services", "required_skills": "Automotive Repair, Diagnostics", "experience_required": 3, "location": "Ipoh, Perak"},
    {"title": "Data Entry Clerk", "description": "Enter administrative data into the central state government database.", "company": "Perak State Dept", "required_skills": "Data Entry, Typing, Administration", "experience_required": 1, "location": "Ipoh, Perak"},
    {"title": "Marine Logistics Officer", "description": "Handle shipping logistics at the Lumut port facility.", "company": "Lumut Maritime", "required_skills": "Logistics, Maritime, Supply Chain", "experience_required": 3, "location": "Lumut, Perak"},

    # Negeri Sembilan
    {"title": "Semiconductor Engineer", "description": "Design and optimize semiconductor manufacturing processes.", "company": "Seremban Semi", "required_skills": "Engineering, Semiconductors, Process Optimization", "experience_required": 4, "location": "Seremban, Negeri Sembilan"},
    {"title": "Production Operator", "description": "Operate heavy machinery in a fast-paced manufacturing plant.", "company": "Nilai Manufacturing", "required_skills": "Machine Operation, Safety, Production", "experience_required": 1, "location": "Nilai, Negeri Sembilan"},
    {"title": "Clinic Receptionist", "description": "Manage patient appointments and front-desk administrative duties.", "company": "Seremban Specialist Clinic", "required_skills": "Administration, Customer Service, Scheduling", "experience_required": 1, "location": "Seremban, Negeri Sembilan"},
    {"title": "Sales Representative", "description": "Drive regional sales for FMCG products.", "company": "Negeri FMCG Distributors", "required_skills": "Sales, B2B, Negotiation", "experience_required": 2, "location": "Port Dickson, Negeri Sembilan"},
    {"title": "Safety Officer", "description": "Ensure workplace safety regulations are met at construction sites.", "company": "NS Builders", "required_skills": "OSHA, Safety, Construction", "experience_required": 3, "location": "Seremban, Negeri Sembilan"},

    # Putrajaya
    {"title": "Public Policy Analyst", "description": "Analyze and draft public policies for government ministries.", "company": "Ministry of Finance", "required_skills": "Policy Analysis, Government, Research", "experience_required": 4, "location": "Putrajaya"},
    {"title": "Cybersecurity Consultant", "description": "Provide security audits and consulting for federal IT infrastructure.", "company": "GovTech Malaysia", "required_skills": "Cybersecurity, Auditing, Network Security", "experience_required": 5, "location": "Putrajaya"},
    {"title": "Legal Advisor", "description": "Provide legal counsel for government contracts and regulatory compliance.", "company": "Attorney General's Chambers", "required_skills": "Law, Contracts, Compliance", "experience_required": 4, "location": "Putrajaya"},
    {"title": "Urban Planning Executive", "description": "Assist in the sustainable urban development of the federal territory.", "company": "Putrajaya Corporation", "required_skills": "Urban Planning, Sustainability, GIS", "experience_required": 3, "location": "Putrajaya"},
    {"title": "Administrative Coordinator", "description": "Coordinate inter-departmental meetings and official correspondence.", "company": "Prime Minister's Dept", "required_skills": "Administration, Coordination, Communication", "experience_required": 2, "location": "Putrajaya"},

    # Sabah
    {"title": "Agronomist", "description": "Provide expert advice on soil management and crop production.", "company": "Sabah Agriculture Dept", "required_skills": "Agronomy, Soil Science, Agriculture", "experience_required": 3, "location": "Kota Kinabalu, Sabah"},
    {"title": "Scuba Diving Instructor", "description": "Lead diving expeditions and certify new divers.", "company": "Semporna Dive Center", "required_skills": "PADI Certification, Diving, Customer Service", "experience_required": 2, "location": "Semporna, Sabah"},
    {"title": "Electrical Technician", "description": "Maintain power grids and electrical infrastructure in rural areas.", "company": "Sabah Electricity", "required_skills": "Electrical Engineering, Maintenance", "experience_required": 2, "location": "Tawau, Sabah"},
    {"title": "Content Creator", "description": "Produce engaging video content to promote local tourism.", "company": "Sabah Tourism Board", "required_skills": "Video Editing, Social Media, Content Creation", "experience_required": 1, "location": "Kota Kinabalu, Sabah"},
    {"title": "Operations Executive", "description": "Oversee logistics and transport schedules for palm oil distribution.", "company": "Sandakan Palm Oil Logistics", "required_skills": "Logistics, Operations, Scheduling", "experience_required": 3, "location": "Sandakan, Sabah"},

    # Sarawak
    {"title": "Hydroelectric Engineer", "description": "Manage operations and maintenance of hydroelectric dam turbines.", "company": "Sarawak Energy", "required_skills": "Electrical Engineering, Hydroelectric, Maintenance", "experience_required": 5, "location": "Kuching, Sarawak"},
    {"title": "Civil Drafter", "description": "Create detailed CAD drawings for the Pan Borneo Highway project.", "company": "Borneo Highway Contractors", "required_skills": "AutoCAD, Drafting, Civil Engineering", "experience_required": 2, "location": "Bintulu, Sarawak"},
    {"title": "Community Nurse", "description": "Provide essential healthcare services to remote communities.", "company": "Sarawak Rural Health", "required_skills": "Nursing, Patient Care, First Aid", "experience_required": 2, "location": "Miri, Sarawak"},
    {"title": "IT Systems Analyst", "description": "Implement and upgrade IT systems for local government branches.", "company": "Kuching Tech Gov", "required_skills": "IT Analysis, Systems Implementation", "experience_required": 3, "location": "Kuching, Sarawak"},
    {"title": "Supply Chain Coordinator", "description": "Coordinate the supply of equipment for offshore oil rigs.", "company": "Miri Offshore Supply", "required_skills": "Supply Chain, Logistics, Coordination", "experience_required": 3, "location": "Miri, Sarawak"},

    # Melaka
    {"title": "Heritage Site Restorer", "description": "Restore and maintain historical buildings and artifacts.", "company": "Melaka Museums", "required_skills": "Architecture, Restoration, History", "experience_required": 4, "location": "Melaka"},
    {"title": "Manufacturing Engineer", "description": "Optimize assembly lines for automotive parts manufacturing.", "company": "Melaka Auto Parts", "required_skills": "Manufacturing, Engineering, Optimization", "experience_required": 3, "location": "Alor Gajah, Melaka"},
    {"title": "Customer Success Manager", "description": "Ensure client satisfaction and retention for a local SaaS startup.", "company": "Melaka Tech Innovators", "required_skills": "Customer Success, Communication, SaaS", "experience_required": 3, "location": "Melaka"},
    {"title": "Cafe Manager", "description": "Run daily operations of a popular boutique cafe in the tourist district.", "company": "Jonker Street Roasters", "required_skills": "F&B Management, Customer Service", "experience_required": 2, "location": "Melaka"},
    {"title": "Logistics Planner", "description": "Plan optimal delivery routes for a regional courier service.", "company": "Melaka Express Delivery", "required_skills": "Logistics, Route Planning", "experience_required": 2, "location": "Melaka"},

    # Labuan
    {"title": "Tax Consultant", "description": "Advise international corporations on offshore tax compliance.", "company": "Labuan Financial Services", "required_skills": "Tax, Finance, Compliance", "experience_required": 4, "location": "Labuan"},
    {"title": "Marine Surveyor", "description": "Inspect and certify ships arriving at the Labuan port.", "company": "Labuan Maritime Surveys", "required_skills": "Marine Engineering, Surveying, Safety", "experience_required": 5, "location": "Labuan"},

    # Kelantan
    {"title": "Islamic Finance Executive", "description": "Process and approve Shariah-compliant financing applications.", "company": "Kelantan Islamic Bank", "required_skills": "Islamic Finance, Banking", "experience_required": 2, "location": "Kota Bharu, Kelantan"},
    {"title": "Textile Designer", "description": "Design modern batik patterns for the fashion industry.", "company": "Kelantan Batik Arts", "required_skills": "Design, Textiles, Creativity", "experience_required": 2, "location": "Kota Bharu, Kelantan"},

    # Terengganu
    {"title": "Marine Engineer", "description": "Provide technical support for coastal patrol vessels.", "company": "Terengganu Shipyards", "required_skills": "Marine Engineering, Maintenance", "experience_required": 3, "location": "Kuala Terengganu, Terengganu"},
    {"title": "Petrochemical Plant Operator", "description": "Monitor control panels in an oil and gas processing facility.", "company": "Terengganu O&G Processing", "required_skills": "Plant Operation, Safety, Monitoring", "experience_required": 2, "location": "Kemaman, Terengganu"},
]

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

# Also update jobs_data.json to keep them fully mirrored
with open('jobs_data.json', 'w') as f:
    json.dump(existing_jobs, f, indent=4)

print(f"Added {added_count} massive jobs to JSON files.")

# Update MongoDB (alumni_database)
try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    db = client.get_database('alumni_database')
    jobs_col = db['jobs']
    
    db_jobs = list(jobs_col.find({}, {"title": 1, "company": 1}))
    db_titles_companies = set((j['title'], j['company']) for j in db_jobs)
    
    db_added_count = 0
    for job in new_jobs:
        if (job['title'], job['company']) not in db_titles_companies:
            jobs_col.insert_one(job.copy())
            db_added_count += 1
            
    print(f"Added {db_added_count} massive jobs to alumni_database MongoDB.")
except Exception as e:
    print(f"MongoDB not updated: {e}")


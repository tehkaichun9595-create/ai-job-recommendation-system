# AI-based Job Recommendation System

## Online Source Code Repository
The latest source code for this project is available on GitHub (link valid for >1 year):
**GitHub Repository Link:** [https://github.com/tehkaichun9595-create/ai-job-recommendation-system](https://github.com/tehkaichun9595-create/ai-job-recommendation-system)

---

## Tools and Prerequisites

To execute the source code, you will need the following tools and libraries installed on your machine.

### Required Software Tools:
1. **Python (Version 3.9 - 3.11)**
   - Download Link: [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. **MongoDB Community Server (Version 6.0+)**
   - Download Link: [https://www.mongodb.com/try/download/community](https://www.mongodb.com/try/download/community)
   - Ensure MongoDB is running on `mongodb://localhost:27017/`
3. **Ollama (For running Local Large Language Models)**
   - Download Link: [https://ollama.com/download](https://ollama.com/download)
   - Required Model: `qwen3:8b` (Run `ollama pull qwen3:8b` in terminal after installation)
4. **Git**
   - Download Link: [https://git-scm.com/downloads](https://git-scm.com/downloads)

### Required Python Libraries:
All required libraries are listed in the `requirements.txt` file. Key libraries include:
- `Flask` (Web framework)
- `pymongo` (MongoDB driver)
- `sentence-transformers` (For skill embeddings and semantic matching)
- `PyMuPDF (fitz)` (For resume PDF parsing)
- `pytesseract` (For OCR fallback)

---

## Execution Instructions

Follow these steps to run the system on your local machine:

### 1. Download the Source Code
Open your terminal or command prompt and run:
```bash
git clone https://github.com/tehkaichun9595-create/ai-job-recommendation-system.git
cd ai-job-recommendation-system
```

### 2. Set Up Virtual Environment
Create and activate an isolated Python environment to install dependencies:
```bash
# For macOS/Linux
python3 -m venv venv_stable
source venv_stable/bin/activate

# For Windows
python -m venv venv_stable
venv_stable\Scripts\activate
```

### 3. Install Dependencies
Install all required Python libraries via pip:
```bash
pip install -r requirements.txt
```

### 4. Configuration
Create a `config.py` file in the root directory (you can copy from `config.example.py` if available) and add your API keys:
```python
# config.py
MONGO_URI = "mongodb://localhost:27017/"
JOOBLE_API_KEY = "your_jooble_api_key_here"
```

### 5. Start the Application
Run the Flask server:
```bash
python app.py
```
The system will now be running at **http://127.0.0.1:5000**

---

## Dataset Instructions

This project utilizes both external APIs and datasets for training/benchmarking.

### Public Dataset (Resumes)
We use a public Resume dataset for testing the parser and evaluating the LLM skill extraction.
- **Dataset Source:** Kaggle Resume Dataset (or equivalent public dataset).
- **Included in Code:** A sampled version of this dataset is already provided directly in the repository at `datasets/resume_dataset_1200.csv` for immediate execution without manual downloads.
- **How to use:** The system scripts (`import_csv_dataset.py`) automatically read from this local CSV file to populate test profiles.

### Live Data (Jobs)
- **Job Listings:** The system does not rely on a static job dataset. Instead, it pulls live job postings dynamically using the **Jooble API**. 
- **Database population:** To fetch the latest jobs into your local MongoDB, you can use the system's interface or run the scheduled background fetching tool.

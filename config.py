# config.py
import os

# --- 1. MongoDB Configuration ---
# Your MongoDB connection string for production use
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')

# --- 2. Email Configuration (Gmail with App Password) ---
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'tehkaichun9595@gmail.com'
MAIL_PASSWORD = 'vldg zmjk kpvb ifth'
MAIL_DEFAULT_SENDER = 'tehkaichun9595@gmail.com'

# --- 3. Jooble Job API Configuration (Malaysia Only) ---
# Get your free API key at: https://jooble.org/api/about
# System designed specifically for the Malaysian job market
JOOBLE_API_KEY = 'b9ac4e11-5721-4071-ba6f-58c8896d3280'
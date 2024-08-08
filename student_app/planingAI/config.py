# config.py
import os

# Database configuration
DB_PATH = './database.db'

# Log files
LOG_DIR = './logs/'
TRACE_LOG = os.path.join(LOG_DIR, 'trace.log')
ERROR_LOG = os.path.join(LOG_DIR, 'error.log')

# User credentials and other configurations
SMTP_SERVER = 'smtp.example.com'
SMTP_PORT = 587
EMAIL_USER = 'example@example.com'
EMAIL_PASSWORD = 'password'

# Feedback query
FEEDBACK_RECIPIENTS_QUERY = """
    SELECT userId 
    FROM authentication 
    WHERE notification = 1
"""

# Rating threshold
RATING_THRESHOLD = 0.5

# Image directory path
IMAGE_PATH = './images/'

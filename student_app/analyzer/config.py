# config.py
import os

# Get the base directory of the current file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Paths for database and logs
DB_PATH = os.path.join(BASE_DIR, '..', 'server', 'database.db')
MODEL_PATH = os.path.join(BASE_DIR, 'decision_tree_model.pkl')  # Path to save the trained decision tree model
LOGS_DIR = os.path.join(BASE_DIR, '..', 'logs')

# Log file paths
TRACE_LOG = os.path.join(LOGS_DIR, 'trace.log')
ERROR_LOG = os.path.join(LOGS_DIR, 'error.log')

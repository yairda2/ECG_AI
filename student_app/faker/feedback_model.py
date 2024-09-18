# directory_structure.py
# יש ליצור פידבק לא חייב דינאמי, הפידבק ירשם לשדה FEADBACK בטבלת USERS.
# לאחר רישום הפידבק יש להריץ את המודל ולראות שהוא משתפר או יורד בביצועים לאחר מכן.#
import os


# Define directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_DIR = os.path.join(BASE_DIR, 'profiles')
GRAPH_DIR = os.path.join(BASE_DIR, 'graphs')
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'server', 'database.db')  # Path to the SQLite database file

# Create directories if they don't exist
os.makedirs(PROFILE_DIR, exist_ok=True)
os.makedirs(GRAPH_DIR, exist_ok=True)

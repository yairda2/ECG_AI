# Description: This script generates feedback for users based on their performance.
import os
import sqlite3
from config import DB_PATH, TRACE_LOG, ERROR_LOG
import logging
import datetime

# Setup logging
logging.basicConfig(filename=TRACE_LOG, level=logging.INFO)

# Function to log trace messages
def log_trace(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"{timestamp} - TRACE: {message}")

# Function to log error messages
def log_error(message):
    with open(ERROR_LOG, 'a') as f:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp} - ERROR: {message}\n")

# Function to generate feedback
def generate_user_feedback(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT score FROM userScores WHERE userID = ?", (user_id,))
        scores = cursor.fetchall()

        # Generate feedback based on scores
        feedback = "Your performance has been evaluated as follows:\n"
        for score in scores:
            feedback += f"Score: {score[0]}\n"

        conn.close()
        log_trace(f"Feedback generated for user {user_id}.")
        return feedback
    except Exception as e:
        log_error(f"Error in generate_user_feedback: {str(e)}")
        raise

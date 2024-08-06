# generate_feedback.py
import sqlite3
import logging
import datetime
import smtplib
from email.mime.text import MIMEText
from config import DB_PATH, TRACE_LOG, ERROR_LOG, FEEDBACK_RECIPIENTS_QUERY, SMTP_SERVER, SMTP_PORT, EMAIL_USER, EMAIL_PASSWORD

# Ensure log files exist
if not os.path.exists(TRACE_LOG):
    open(TRACE_LOG, 'w').close()

if not os.path.exists(ERROR_LOG):
    open(ERROR_LOG, 'w').close()

# Setup logging
logging.basicConfig(filename=TRACE_LOG, level=logging.INFO)

def log_error(error_message):
    """Log error messages to the error log file with timestamp."""
    with open(ERROR_LOG, 'a') as error_log:
        error_log.write(f"{datetime.datetime.now()}: {error_message}\n")

def generate_user_feedback():
    """Generate and send feedback to users based on their performance."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(FEEDBACK_RECIPIENTS_QUERY)
        user_ids = cursor.fetchall()

        for user_id_tuple in user_ids:
            user_id = user_id_tuple[0]
            feedback = get_feedback_for_user(user_id)
            send_feedback(user_id, feedback)
        
        conn.close()
        logging.info(f"{datetime.datetime.now()}: Feedback generated and sent to users.")
    
    except Exception as e:
        log_error(f"Failed to generate feedback: {str(e)}")

def get_feedback_for_user(user_id):
    """Retrieve feedback data for a specific user from the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        query = """
        SELECT examAnswers.photoName, examAnswers.classificationSetDes, imageClassification.rate
        FROM examAnswers
        JOIN imageClassification ON examAnswers.photoName = imageClassification.photoName
        WHERE examAnswers.userId = ?
        """
        
        cursor.execute(query, (user_id,))
        results = cursor.fetchall()
        
        strengths = []
        weaknesses = []
        
        for row in results:
            photo_name, user_classification, rate = row
            if user_classification == 'LOW RISK':
                strengths.append((photo_name, rate))
            else:
                weaknesses.append((photo_name, rate))
        
        conn.close()
        return create_feedback_message(strengths, weaknesses)
    
    except Exception as e:
        log_error(f"Failed to retrieve feedback for user {user_id}: {str(e)}")
        return ""

def create_feedback_message(strengths, weaknesses):
    """Create a feedback message based on strengths and weaknesses."""
    message = "Dear User,\\n\\nHere is your performance feedback:\\n\\n"
    
    if strengths:
        message += "Strengths:\\n"
        for item in strengths:
            message += f"- {item[0]} with a rating of {item[1]}\\n"
    
    if weaknesses:
        message += "\\nAreas for Improvement:\\n"
        for item in weaknesses:
            message += f"- {item[0]} with a rating of {item[1]}\\n"
    
    message += "\\nKeep up the good work and continue to improve!\\n\\nBest regards,\\nECG Analysis Team"
    return message

def send_feedback(user_id, message):
    """Send feedback to the user."""
    try:
        msg = MIMEText(message)
        msg['Subject'] = 'Your Performance Feedback'
        msg['From'] = EMAIL_USER
        msg['To'] = f"user_{user_id}@example.com"  # Replace with actual user email retrieval logic

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, [msg['To']], msg.as_string())
        
        logging.info(f"{datetime.datetime.now()}: Feedback sent to user {user_id}.")
    
    except Exception as e:
        log_error(f"Failed to send feedback to user {user_id}: {str(e)}")

if __name__ == "__main__":
    generate_user_feedback()

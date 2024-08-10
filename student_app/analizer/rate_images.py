# rate_images.py
import sqlite3
import logging
import datetime
from config import DB_PATH, TRACE_LOG, ERROR_LOG, RATING_THRESHOLD

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

def update_image_ratings():
    """Update the ratings of images based on user performance metrics."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        query = """
        SELECT photoName, 
               AVG(rate) AS avg_rate
        FROM imageClassification
        JOIN examAnswers ON imageClassification.photoName = examAnswers.photoName
        GROUP BY photoName
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        for row in results:
            photo_name, avg_rate = row
            new_rate = avg_rate * RATING_THRESHOLD  # Example calculation
            update_query = "UPDATE imageClassification SET rate = ? WHERE photoName = ?"
            cursor.execute(update_query, (new_rate, photo_name))
        
        conn.commit()
        conn.close()
        logging.info(f"{datetime.datetime.now()}: Image ratings updated successfully.")
    
    except Exception as e:
        log_error(f"Failed to update image ratings: {str(e)}")

if __name__ == "__main__":
    update_image_ratings()

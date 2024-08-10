# process_images.py
import os
import cv2  # Assuming OpenCV is used for image processing
import sqlite3
import logging
import datetime
from config import DB_PATH, IMAGE_PATH, TRACE_LOG, ERROR_LOG

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

def process_new_images():
    """Process new images and update their ratings in the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        for image_file in os.listdir(IMAGE_PATH):
            if image_file.endswith(".jpg") or image_file.endswith(".png"):
                image_path = os.path.join(IMAGE_PATH, image_file)
                image = cv2.imread(image_path)
                # Example image processing to calculate rating
                rating = calculate_image_rating(image)
                
                insert_query = "INSERT INTO imageClassification (photoName, rate) VALUES (?, ?)"
                cursor.execute(insert_query, (image_file, rating))
        
        conn.commit()
        conn.close()
        logging.info(f"{datetime.datetime.now()}: New images processed and rated successfully.")
    
    except Exception as e:
        log_error(f"Failed to process new images: {str(e)}")

def calculate_image_rating(image):
    """Calculate the rating of an image based on its features."""
    # Example: simple average intensity as a rating
    return image.mean()

if __name__ == "__main__":
    process_new_images()

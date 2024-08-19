# Description: This script processes new images before they are classified.
import os
from PIL import Image
from config import TRACE_LOG, ERROR_LOG
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

# Function to process an image
def process_image(image_path):
    try:
        image = Image.open(image_path)
        # Perform some processing on the image if needed
        processed_image_path = image_path.replace('raw_images', 'processed_images')
        image.save(processed_image_path)
        log_trace(f"Image {image_path} processed successfully.")
        return processed_image_path
    except Exception as e:
        log_error(f"Error in process_image: {str(e)}")
        raise

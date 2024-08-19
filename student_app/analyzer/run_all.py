# Description: This script orchestrates the overall process of training/updating the model and rating images.
from rate_images import update_image_ratings
from train_and_update_model import train_or_update_model
from config import TRACE_LOG, ERROR_LOG
import datetime
import logging

# Setup logging
logging.basicConfig(filename=TRACE_LOG, level=logging.INFO)

# Function to log error messages
def log_error(message):
    with open(ERROR_LOG, 'a') as f:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp} - ERROR: {message}\n")

def main():
    try:
        # Step 1: Train or update the model
        train_or_update_model()

        # Step 2: Rate images using the updated model
        update_image_ratings()
    except Exception as e:
        log_error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main()

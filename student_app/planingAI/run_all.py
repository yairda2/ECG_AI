# run_all.py
import logging
import datetime
import os
from rate_images import update_image_ratings
from process_images import process_new_images
from generate_feedback import generate_user_feedback
from config import TRACE_LOG, ERROR_LOG

# Ensure log files exist
if not os.path.exists(os.path.dirname(TRACE_LOG)):
    os.makedirs(os.path.dirname(TRACE_LOG))

if not os.path.exists(os.path.dirname(ERROR_LOG)):
    os.makedirs(os.path.dirname(ERROR_LOG))

if not os.path.isfile(TRACE_LOG):
    open(TRACE_LOG, 'w').close()

if not os.path.isfile(ERROR_LOG):
    open(ERROR_LOG, 'w').close()

# Setup logging
logging.basicConfig(filename=TRACE_LOG, level=logging.INFO)

def log_error(error_message):
    """Log error messages to the error log file with timestamp."""
    with open(ERROR_LOG, 'a') as error_log:
        error_log.write(f"{datetime.datetime.now()}: {error_message}\n")

def main():
    try:
        logging.info(f"{datetime.datetime.now()}: Starting the full system run.")

        # Step 1: Update image ratings
        update_image_ratings()
        
        # Step 2: Process new images
        process_new_images()
        
        # Step 3: Generate user feedback
        generate_user_feedback()

        logging.info(f"{datetime.datetime.now()}: Full system run completed successfully.")
    
    except Exception as e:
        log_error(f"System run failed: {str(e)}")

if __name__ == "__main__":
    main()

import schedule
import time
from train_model import update_model_with_new_data, update_image_ratings
from image_analysis import process_new_images, update_model_with_new_images
from feedback import generate_feedback

def job():
    update_model_with_new_data()
    update_image_ratings()
    update_model_with_new_images()
    process_new_images()
    generate_feedback('example-user-id')  # כאן אפשר להשתמש בפונקציה שתעדכן פידבק לכל המשתמשים

schedule.every().day.at("00:00").do(job)

while True:
    schedule.run_pending()
    time.sleep(1)

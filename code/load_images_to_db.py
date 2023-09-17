# Build upload image to mongodb.
# each image has valid/invalid label.
# and to invalid images we add the reason for the invalidity up to ten labels.
# Authors: Yair Davidof, Elyasaf Sinvani.

# region imports
import datetime
import os
import webbrowser
from flask import Flask, request, render_template, redirect, url_for, flash
from pymongo import MongoClient
from werkzeug.utils import secure_filename
# endregion imports

# region global variables
current_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(current_dir, 'log.txt')

# endregion global variables

# region functions

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MongoDB connection
# Replace the connection string with your MongoDB Atlas connection string
mongo_uri = "mongodb+srv://yairda:yairda2@eeg.tfghyuo.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(mongo_uri)
db = client.your_database  # Replace 'your-database' with your actual database name
collection = db.images  # Replace 'images' with your collection name

# Define the upload route
@app.route('/', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        image = request.files['image']
        validity = request.form['validity']

        reasons = []
        for i in range(1, 11):
            reason = request.form.get(f'reason{i}')
            if reason:
                reasons.append(reason)

        if image:
            filename = secure_filename(image.filename)
            image.save(os.path.join('uploads', filename))

            # Store the data in MongoDB
            data = {
                'filename': filename,
                'validity': validity,
                'reasons': reasons
            }
            collection.insert_one(data)

            flash('Image uploaded successfully!', 'success')
            return redirect(url_for('upload_image'))

    images = collection.find()
    return render_template('upload.html', images=images)

if __name__ == '__main__':
    os.makedirs("uploads", exist_ok=True)
    webbrowser.open('http://127.0.0.1:5000')  # Open the default web browser
    app.run(debug=True)

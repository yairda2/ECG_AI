# Build upload image to mongodb.
# each image has valid/invalid label.
# and to invalid images we add the reason for the invalidity up to ten labels.
# Authors: Yair Davidof,  Elyasaf Sinvani.

# region imports
import os
import sys
import argparse
import logging
import json
import pymongo
import datetime

from pymongo.errors import ConnectionFailure
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from flask import Flask, request, render_template, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import FileField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, InputRequired
from pymongo import MongoClient
from werkzeug.utils import secure_filename

# endregion imports

# region global variables
current_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(current_dir, 'log.txt')

# endregion global variables

# region functions
def connect_db():
    """
    connect to mongodb.
    :return:
    """
    uri = "mongodb+srv://yairda:yairda2@eeg.tfghyuo.mongodb.net/?retryWrites=true&w=majority"

    # Create a new client and connect to the server
    client = MongoClient(uri, server_api=ServerApi('1'))

    # Send a ping to confirm a successful connection
    try:
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)


def report_to_log(message):
    """
    report to txt file.
    :param message:
    :return:
    """
    with open(log_file, 'a') as f:
        f.write(f"{datetime.time} {message}")

def upload_images_to_db():
    app = Flask(_name_)
    app.secret_key = 'your_secret_key'

    # MongoDB connection
    client = MongoClient('mongodb://localhost:27017/')  # Update with your MongoDB connection string
    db = client['image_labels']
    collection = db['images']

    # Define a form for image upload
    class ImageForm(FlaskForm):
        image = FileField('Image', validators=[InputRequired()])
        label = SelectField('Label', choices=[('legal', 'Legal'), ('invalid', 'Invalid')], validators=[DataRequired()])
        comment = StringField('Comment')
        submit = SubmitField('Upload')

    # Define the upload route
    @app.route('/', methods=['GET', 'POST'])
    def upload_image():
        form = ImageForm()

        if form.validate_on_submit():
            image = form.image.data
            label = form.label.data
            comment = form.comment.data

            if image:
                filename = secure_filename(image.filename)
                image.save(os.path.join('uploads', filename))

                # Store the data in MongoDB
                data = {
                    'filename': filename,
                    'label': label,
                    'comment': comment,
                }
                collection.insert_one(data)

                flash('Image uploaded successfully!', 'success')
                return redirect(url_for('upload_image'))

        return render_template('upload.html', form=form)

    if _name_ == '_main_':
        app.run(debug=True)

# endregion functions


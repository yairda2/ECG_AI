#1223
#5656
import os
from flask import Flask, request, render_template, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import FileField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, InputRequired
from pymongo import MongoClient
from werkzeug.utils import secure_filename

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

#stop 
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
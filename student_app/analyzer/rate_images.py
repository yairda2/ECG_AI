import os
import pickle
import logging
import datetime
import sqlite3
from config import DB_PATH, MODEL_PATH, TRACE_LOG, ERROR_LOG
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder
import numpy as np

# Setup logging
logging.basicConfig(filename=TRACE_LOG, level=logging.INFO)

def log_trace(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"{timestamp} - TRACE: {message}")

def log_error(message):
    with open(ERROR_LOG, 'a') as f:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp} - ERROR: {message}\n")

def load_model():
    """Load the decision tree model from the saved file."""
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, 'rb') as model_file:
            model = pickle.load(model_file)
        log_trace("Decision tree model loaded successfully.")
        return model
    else:
        log_trace("No existing model found. A new model will be trained.")
        return DecisionTreeClassifier()

def save_model(model):
    """Save the decision tree model to a file."""
    with open(MODEL_PATH, 'wb') as model_file:
        pickle.dump(model, model_file)
    log_trace("Decision tree model saved successfully.")

def train_or_update_model():
    """Train or update the decision tree model using data from the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Fetch the training data
        cursor.execute("""
            SELECT photoName, classificationSet, classificationSubSet, answerSubmitTime, 
                   totalTrainTime, academicInstitution, rate 
            FROM imageClassification
            JOIN users ON imageClassification.imageId = users.id
            WHERE rate IS NOT NULL
        """)
        data = cursor.fetchall()

        if not data:
            log_trace("No training data available in the database.")
            return

        # Prepare the dataset
        features = []
        labels = []
        for photoName, classificationSet, classificationSubSet, answerSubmitTime, totalTrainTime, academicInstitution, rate in data:
            features.append([classificationSet, classificationSubSet, answerSubmitTime, totalTrainTime, academicInstitution])
            labels.append(rate)

        # Encode categorical features into numerical values
        label_encoder = LabelEncoder()
        encoded_features = [label_encoder.fit_transform(feature) for feature in zip(*features)]
        X = np.array(encoded_features).T
        y = np.array(labels)

        # Train the decision tree model
        model = load_model()
        model.fit(X, y)
        save_model(model)

        log_trace("Model trained and updated successfully.")
    except Exception as e:
        log_error(f"Error in train_or_update_model: {str(e)}")
        raise
    finally:
        conn.close()

def rate_image(photo_name, classification_set, classification_subset, answer_submit_time, total_train_time, academic_institution):
    """Rate an image based on its classification set and subset using the trained decision tree model."""
    try:
        model = load_model()
        label_encoder = LabelEncoder()
        encoded_features = label_encoder.fit_transform([classification_set, classification_subset, answer_submit_time, total_train_time, academic_institution])
        difficulty_score = model.predict([encoded_features])

        log_trace(f"Image {photo_name} rated with difficulty score {difficulty_score[0]}")
        return difficulty_score[0]
    except Exception as e:
        log_error(f"Error in rate_image: {str(e)}")
        raise

def update_image_ratings():
    """Update the ratings of all images in the database based on the trained model."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Fetch all images that need to be rated
        cursor.execute("""
            SELECT photoName, classificationSet, classificationSubSet, answerSubmitTime, 
                   totalTrainTime, academicInstitution 
            FROM imageClassification
            JOIN users ON imageClassification.imageId = users.id
            WHERE rate IS NULL
        """)
        images = cursor.fetchall()

        for photo_name, classification_set, classification_subset, answer_submit_time, total_train_time, academic_institution in images:
            # Rate each image
            difficulty_score = rate_image(photo_name, classification_set, classification_subset, answer_submit_time, total_train_time, academic_institution)
            cursor.execute("UPDATE imageClassification SET rate = ? WHERE photoName = ?", (difficulty_score, photo_name))

        conn.commit()
        log_trace("Image ratings updated successfully.")
    except Exception as e:
        log_error(f"Error in update_image_ratings: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    train_or_update_model()
    update_image_ratings()

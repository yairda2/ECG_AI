# Authors: Yair Davidof, Elyasaf sivani
# Date: 06/07/2024
# Description: This script is responsible for training or updating the decision tree model using data from the database.
import os
import pickle
import logging
import datetime
import sqlite3
from config import DB_PATH, MODEL_PATH, TRACE_LOG, ERROR_LOG, BASE_DIR
from sklearn.tree import DecisionTreeClassifier, export_graphviz
from sklearn.preprocessing import LabelEncoder
import numpy as np
import graphviz

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
            SELECT imageClassification.photoName, imageClassification.classificationSet, 
                   imageClassification.classificationSubSet, answers.answerSubmitTime, 
                   users.totalTrainTime, users.academicInstitution, imageClassification.rate 
            FROM imageClassification
            JOIN answers ON imageClassification.photoName = answers.photoName
            JOIN users ON answers.userId = users.id
            WHERE imageClassification.rate IS NOT NULL
        """)
        data = cursor.fetchall()

        if not data:
            log_trace("No training data available in the database.")
            return

        # Prepare the dataset
        features = []
        labels = []
        for _, classificationSet, classificationSubSet, answerSubmitTime, totalTrainTime, academicInstitution, rate in data:
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

        # Visualize and save the decision tree
        dot_data = export_graphviz(model, out_file=None,
                                   feature_names=['ClassificationSetSrc', 'ClassificationSubSetSrc', 'AnswerSubmitTime', 'TotalTrainTime', 'AcademicInstitution'],
                                   class_names=[str(i) for i in set(y)],
                                   filled=True, rounded=True, special_characters=True)
        graph = graphviz.Source(dot_data)
        graph_path = os.path.join(BASE_DIR, 'decision_tree_visualization')
        os.makedirs(graph_path, exist_ok=True)
        graph.render(os.path.join(graph_path, f'decision_tree_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.png'))

        # Log feature importances (weights)
        feature_importances = model.feature_importances_
        for feature_name, importance in zip(['ClassificationSetSrc', 'ClassificationSubSetSrc', 'AnswerSubmitTime', 'TotalTrainTime', 'AcademicInstitution'], feature_importances):
            log_trace(f"Feature '{feature_name}' has importance: {importance}")

        log_trace("Model trained, updated, and decision tree saved successfully.")
    except Exception as e:
        log_error(f"Error in train_or_update_model: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    train_or_update_model()

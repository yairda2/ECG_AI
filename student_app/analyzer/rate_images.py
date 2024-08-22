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
            loaded_data = pickle.load(model_file)
            if isinstance(loaded_data, tuple) and len(loaded_data) == 2:
                model, feature_importances = loaded_data
            else:
                model = loaded_data
                feature_importances = None
        log_trace("Decision tree model loaded successfully.")
        return model, feature_importances
    else:
        log_trace("No existing model found. A new model will be trained.")
        return DecisionTreeClassifier(), None

def save_model(model, feature_importances):
    """Save the decision tree model and its feature importances to a file."""
    with open(MODEL_PATH, 'wb') as model_file:
        pickle.dump((model, feature_importances), model_file)
    log_trace("Decision tree model and feature importances saved successfully.")

def train_or_update_model():
    """Train or update the decision tree model using data from the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Fetch the training data
        cursor.execute("""
            SELECT users.age, users.gender, users.avgDegree, users.totalTrainTime, 
                   users.totalExams, users.totalEntries, users.academicInstitution, 
                   answers.answerSubmitTime, answers.helpActivated, 
                   imageClassification.rate, answers.classificationSetDes, answers.classificationSubSetDes, 
                   answers.classificationSetSrc, answers.classificationSubSetSrc, answers.photoName
            FROM users
            JOIN answers ON users.id = answers.userId
            JOIN imageClassification ON answers.photoName = imageClassification.photoName
            WHERE imageClassification.rate IS NOT NULL
        """)
        data = cursor.fetchall()

        if not data:
            log_trace("No training data available in the database.")
            return

        # Prepare the dataset
        features = []
        labels = []
        for (age, gender, avgDegree, totalTrainTime, totalExams, totalEntries, academicInstitution,
             answerSubmitTime, helpActivated, rate, classificationSetDes, classificationSubSetDes,
             classificationSetSrc, classificationSubSetSrc, photoName) in data:
            features.append([age, gender, avgDegree, totalTrainTime, totalExams, totalEntries,
                             academicInstitution, answerSubmitTime, helpActivated,
                             classificationSetSrc, classificationSubSetSrc])
            labels.append(rate)

        # Encode categorical features into numerical values
        label_encoder = LabelEncoder()
        encoded_features = [label_encoder.fit_transform(feature) for feature in zip(*features)]
        X = np.array(encoded_features).T
        y = np.array(labels)

        # Train the decision tree model
        model, previous_feature_importances = load_model()
        model.fit(X, y)
        save_model(model, model.feature_importances_)

        # Log feature importances (weights)
        feature_importances = model.feature_importances_
        for feature_name, importance in zip(['age', 'gender', 'avgDegree', 'totalTrainTime', 'totalExams', 'totalEntries',
                                             'academicInstitution', 'answerSubmitTime', 'helpActivated',
                                             'classificationSetSrc', 'classificationSubSetSrc'], feature_importances):
            log_trace(f"Feature '{feature_name}' has importance: {importance}")

        # Compare current feature importances with the previous ones
        if previous_feature_importances is not None:
            if not np.array_equal(previous_feature_importances, feature_importances):
                log_trace("Feature importances have changed since the last model update.")
            else:
                log_trace("Feature importances remain the same as the last model update.")

        # Visualize and save the decision tree
        dot_data = export_graphviz(model, out_file=None,
                                   feature_names=['age', 'gender', 'avgDegree', 'totalTrainTime', 'totalExams', 'totalEntries',
                                                  'academicInstitution', 'answerSubmitTime', 'helpActivated',
                                                  'classificationSetSrc', 'classificationSubSetSrc'],
                                   class_names=[str(i) for i in set(y)],
                                   filled=True, rounded=True, special_characters=True)
        graph = graphviz.Source(dot_data)
        graph_path = os.path.join(BASE_DIR, 'decision_tree_visualization')
        os.makedirs(graph_path, exist_ok=True)
        graph.render(os.path.join(graph_path, f'decision_tree_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.png'))

        log_trace("Model trained, updated, and decision tree saved successfully.")
    except Exception as e:
        log_error(f"Error in train_or_update_model: {str(e)}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    train_or_update_model()

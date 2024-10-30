import os
import pickle
import logging
import datetime
import sqlite3
from config import DB_PATH, MODEL_PATH, TRACE_LOG, ERROR_LOG, BASE_DIR
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import numpy as np
import matplotlib.pyplot as plt

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
    """Load the random forest model from the saved file."""
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, 'rb') as model_file:
            loaded_data = pickle.load(model_file)
            if isinstance(loaded_data, tuple) and len(loaded_data) == 2:
                model, feature_importances = loaded_data
            else:
                model = loaded_data
                feature_importances = None
        log_trace("Random forest model loaded successfully.")
        return model, feature_importances
    else:
        log_trace("No existing model found. A new model will be trained.")
        return RandomForestClassifier(n_estimators=100, random_state=42), None

def save_model(model, feature_importances):
    """Save the random forest model and its feature importances to a file."""
    with open(MODEL_PATH, 'wb') as model_file:
        pickle.dump((model, feature_importances), model_file)
    log_trace("Random forest model and feature importances saved successfully.")

def plot_feature_importances(feature_names, importances):
    """Plot and save a graph of feature importances."""
    indices = np.argsort(importances)
    plt.figure(figsize=(10, 6))
    plt.title("Feature Importances")
    plt.barh(range(len(indices)), importances[indices], align='center')
    plt.yticks(range(len(indices)), [feature_names[i] for i in indices])
    plt.xlabel("Relative Importance")
    plt.tight_layout()

    # Save the plot
    graph_path = os.path.join(BASE_DIR, 'graphs')
    os.makedirs(graph_path, exist_ok=True)
    plt.savefig(
        os.path.join(graph_path, f'feature_importances_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.png'))
    plt.close()
    log_trace("Feature importances graph saved.")

def plot_training_metrics(metric_values, metric_name):
    """Plot and save a graph of training metrics like accuracy."""
    plt.figure(figsize=(10, 6))
    plt.plot(metric_values, marker='o')
    plt.title(f"{metric_name} Over Time")
    plt.xlabel("Training Session")
    plt.ylabel(metric_name)
    plt.tight_layout()

    # Save the plot
    graph_path = os.path.join(BASE_DIR, 'graphs')
    os.makedirs(graph_path, exist_ok=True)
    plt.savefig(
        os.path.join(graph_path, f'{metric_name.lower()}_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.png'))
    plt.close()
    log_trace(f"{metric_name} graph saved.")

def train_or_update_model():
    """Train or update the random forest model using data from the database."""
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
        x = np.array(encoded_features).T
        y = np.array(labels)

        # Train the random forest model
        model, previous_feature_importances = load_model()
        model.fit(x, y)
        save_model(model, model.feature_importances_)

        # Log feature importances (weights) and plot them
        feature_importances = model.feature_importances_
        feature_names = ['age', 'gender', 'avgDegree', 'totalTrainTime', 'totalExams', 'totalEntries',
                         'academicInstitution', 'answerSubmitTime', 'helpActivated',
                         'classificationSetSrc', 'classificationSubSetSrc']
        plot_feature_importances(feature_names, feature_importances)

        for feature_name, importance in zip(feature_names, feature_importances):
            log_trace(f"Feature '{feature_name}' has importance: {importance}")

        # Compare current feature importances with the previous ones
        if previous_feature_importances is not None:
            if not np.array_equal(previous_feature_importances, feature_importances):
                log_trace("Feature importances have changed since the last model update.")
            else:
                log_trace("Feature importances remain the same as the last model update.")

        log_trace("Model trained and updated successfully.")
    except Exception as e:
        log_error(f"Error in train_or_update_model: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    train_or_update_model()

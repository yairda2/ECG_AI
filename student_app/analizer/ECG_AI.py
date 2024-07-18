import os
import json
import sqlite3
import numpy as np
import tensorflow as tf
from transformers import TFAutoModel, AutoTokenizer


# Path: analizer/ECG_AI.py
db_path = os.path.join(os.path.dirname(__file__), '..', 'server', 'database.db')
# Load the pre-trained BERT model and tokenizer
model = TFAutoModel.from_pretrained('bert-base-uncased')
tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')

def rate_images():
    """
    Function to rate images based on their classification set and subset.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT photoName, classificationSet, classificationSubSet FROM imageClassification")
    images = cursor.fetchall()

    for image in images:
        photoName, classificationSet, classificationSubSet = image
        text = f"{classificationSet} {classificationSubSet}"
        inputs = tokenizer(text, return_tensors='tf')
        outputs = model(**inputs)
        rating = np.mean(outputs.last_hidden_state.numpy())

        cursor.execute("UPDATE imageClassification SET rate = ? WHERE photoName = ?", (rating, photoName))

    conn.commit()
    conn.close()

def learn_from_data():
    """
    Function to learn from user answers and update image ratings.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM answers")
    answers = cursor.fetchall()

    # Example learning: calculate average rating for each classification
    ratings = {}
    for answer in answers:
        classificationSetDes = answer[6]
        rate = answer[8]
        if classificationSetDes not in ratings:
            ratings[classificationSetDes] = []
        ratings[classificationSetDes].append(rate)

    for classification, rates in ratings.items():
        avg_rate = np.mean(rates)
        cursor.execute("UPDATE imageClassification SET rate = ? WHERE classificationSet = ?", (avg_rate, classification))

    conn.commit()
    conn.close()

# Run the functions daily
if __name__ == "__main__":
    rate_images()
    learn_from_data()

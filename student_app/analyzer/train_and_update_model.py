# Description: This script trains a new model or updates an existing one based on new data.
import os
import torch
from transformers import ViTForImageClassification, ViTFeatureExtractor, Trainer, TrainingArguments
from PIL import Image
import logging
from config import MODEL_PATH, TRACE_LOG, ERROR_LOG, DB_PATH
import sqlite3
import datetime

# Setup logging
logging.basicConfig(filename=TRACE_LOG, level=logging.INFO)

# Function to log trace messages
def log_trace(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"{timestamp} - TRACE: {message}")

# Function to log error messages
def log_error(message):
    with open(ERROR_LOG, 'a') as f:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp} - ERROR: {message}\n")

# Function to train or update the model
def train_or_update_model():
    try:
        # Load data from the database for training
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT photoName, classification FROM imageClassification WHERE classification IS NOT NULL")
        data = cursor.fetchall()
        conn.close()

        # Prepare the dataset
        images = []
        labels = []
        for photoName, classification in data:
            image_path = os.path.join(SERVER_DIR, 'public', 'img', 'bankPhotos', photoName)
            image = Image.open(image_path)
            images.append(image)
            labels.append(classification)

        # Define the model and training arguments
        model = ViTForImageClassification.from_pretrained('google/vit-base-patch16-224', num_labels=len(set(labels)))
        feature_extractor = ViTFeatureExtractor.from_pretrained('google/vit-base-patch16-224')

        training_args = TrainingArguments(
            output_dir=MODEL_PATH,
            per_device_train_batch_size=16,
            evaluation_strategy="steps",
            num_train_epochs=3,
            save_steps=10,
            save_total_limit=2,
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=images,
            eval_dataset=labels,
            tokenizer=feature_extractor,
        )

        # Train the model
        trainer.train()
        model.save_pretrained(MODEL_PATH)

        log_trace("Model trained and updated successfully.")
    except Exception as e:
        log_error(f"Error in train_or_update_model: {str(e)}")
        raise

from transformers import GPT2LMHeadModel, GPT2Tokenizer
import sqlite3
from config import DB_PATH, TRACE_LOG, ERROR_LOG
import logging
import datetime

# Setup logging
logging.basicConfig(filename=TRACE_LOG, level=logging.INFO)

def log_trace(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"{timestamp} - TRACE: {message}")

def log_error(message):
    with open(ERROR_LOG, 'a') as f:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp} - ERROR: {message}\n")

# Load GPT model
tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
model = GPT2LMHeadModel.from_pretrained('gpt2')

def generate_feedback(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT photoName, classificationSetDes, rate
            FROM examAnswers
            JOIN imageClassification ON examAnswers.photoName = imageClassification.photoName
            WHERE examAnswers.userId = ?
        """, (user_id,))
        results = cursor.fetchall()

        strengths = []
        weaknesses = []
        
        for row in results:
            photo_name, user_classification, rate = row
            if user_classification == 'LOW RISK':
                strengths.append((photo_name, rate))
            else:
                weaknesses.append((photo_name, rate))

        prompt = "Based on your recent performance, here is your feedback:\n\n"
        prompt += "Strengths:\n" + "\n".join([f"- {item[0]} (Rating: {item[1]})" for item in strengths]) + "\n\n"
        prompt += "Areas for Improvement:\n" + "\n".join([f"- {item[0]} (Rating: {item[1]})" for item in weaknesses])

        inputs = tokenizer.encode(prompt, return_tensors="pt")
        outputs = model.generate(inputs, max_length=150, num_return_sequences=1)

        feedback = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        conn.close()
        log_trace(f"Generated feedback for user {user_id}.")
        return feedback
    except Exception as e:
        log_error(f"Error in generate_feedback: {str(e)}")
        raise

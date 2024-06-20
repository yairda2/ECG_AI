# Analaizer: ECG
#Author: Yair Davidof
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, learning_curve
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix
import joblib
import numpy as np
from transformers import pipeline

# Connect to the SQLite database
db_path = 'database.db'
conn = sqlite3.connect(db_path)

# Load data from the database
def load_data(table_name):
    query = f"SELECT * FROM {table_name}"
    return pd.read_sql_query(query, conn)

# Load user and answers data
users_df = load_data('users')
answers_df = load_data('answers')

# Merging users data with answers data on user ID
merged_data = pd.merge(users_df, answers_df, left_on='id', right_on='userId')

# Feature selection and preprocessing as needed
features = merged_data[['age', 'avgDegree', 'totalAnswers', 'answerTime']]
labels = merged_data['classificationDes']

# Split data into training and test sets
X_train, X_test, y_train, y_test = train_test_split(features, labels, test_size=0.2, random_state=42)

# Train a RandomForest Classifier
model = RandomForestClassifier(n_estimators=100, random_state=42)
train_sizes, train_scores, test_scores = learning_curve(model, X_train, y_train, cv=5, scoring='accuracy', n_jobs=-1, train_sizes=np.linspace(0.01, 1.0, 50))

# Plot learning curve
plt.figure(figsize=(10, 6))
plt.plot(train_sizes, np.mean(train_scores, axis=1), 'o-', color="r", label="Training score")
plt.plot(train_sizes, np.mean(test_scores, axis=1), 'o-', color="g", label="Cross-validation score")
plt.title("Learning Curve")
plt.xlabel("Training Set Size")
plt.ylabel("Accuracy Score")
plt.legend(loc="best")
plt.show()

# Predict on the test set
predictions = model.predict(X_test)
accuracy = accuracy_score(y_test, predictions)

# Generate additional plots (Placeholder for actual metrics)
for i in range(5):
    plt.figure()
    plt.plot(np.random.randn(100).cumsum(), label=f'Graph {i+1}')
    plt.title(f'Additional Plot {i+1}')
    plt.legend()
    plt.show()

# Initialize the text generation pipeline with GPT-2
generator = pipeline('text-generation', model='gpt-2')

# Generate feedback based on the model's performance
def generate_feedback(accuracy, conf_matrix):
    input_prompt = f"The model has achieved an accuracy of {accuracy:.2%}. The confusion matrix is {conf_matrix}. Please provide detailed feedback on the model's performance and recommendations for improvement."
    feedback = generator(input_prompt, max_length=150, num_return_sequences=1)
    return feedback[0]['generated_text']

# Use the function to generate feedback
conf_matrix = confusion_matrix(y_test, predictions)
model_feedback = generate_feedback(accuracy, conf_matrix)

# Print and save the feedback
print(model_feedback)
with open('feedback_and_recommendations.txt', 'w') as file:
    file.write(model_feedback)

# Save the trained model
joblib.dump(model, 'ecg_model.pkl')

# Close the database connection
conn.close()

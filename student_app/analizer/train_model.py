import sqlite3
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib

def train_model():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT users.userId, users.totalTrainTime, users.totalAnswers, users.totalExams, imageClassification.rate
        FROM users
        JOIN examAnswers ON users.userId = examAnswers.userId
        JOIN imageClassification ON examAnswers.photoName = imageClassification.photoName
    ''')
    data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['userId', 'totalTrainTime', 'totalAnswers', 'totalExams', 'rate'])

    X = df[['totalTrainTime', 'totalAnswers', 'totalExams']]
    y = df['rate']

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)

    joblib.dump(model, 'rate_model.pkl')

    conn.close()

def update_model_with_new_data():
    model = joblib.load('rate_model.pkl')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT users.userId, users.totalTrainTime, users.totalAnswers, users.totalExams, imageClassification.rate
        FROM users
        JOIN examAnswers ON users.userId = examAnswers.userId
        JOIN imageClassification ON examAnswers.photoName = imageClassification.photoName
        WHERE examAnswers.date > DATE('now', '-1 day')
    ''')
    data = cursor.fetchall()

    df = pd.DataFrame(data, columns=['userId', 'totalTrainTime', 'totalAnswers', 'totalExams', 'rate'])

    if not df.empty:
        X_new = df[['totalTrainTime', 'totalAnswers', 'totalExams']]
        y_new = df['rate']

        model.fit(X_new, y_new)

        joblib.dump(model, 'rate_model.pkl')

    conn.close()

def update_image_ratings():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('SELECT userId, totalTrainTime, totalAnswers, totalExams FROM users')
    user_data = cursor.fetchall()

    model = joblib.load('rate_model.pkl')

    for user in user_data:
        userId, totalTrainTime, totalAnswers, totalExams = user
        predicted_rate = model.predict([[totalTrainTime, totalAnswers, totalExams]])[0]
        
        cursor.execute('''
            UPDATE imageClassification
            SET rate = rate + ?
            WHERE photoName IN (
                SELECT photoName
                FROM examAnswers
                WHERE userId = ?
            )
        ''', (predicted_rate, userId))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    train_model()
    update_image_ratings()
    update_model_with_new_data()

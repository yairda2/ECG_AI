import sqlite3
import smtplib
from email.mime.text import MIMEText

def generate_feedback(userId):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT totalTrainTime, totalAnswers, totalExams, avgDegree, userRate
        FROM users WHERE userId = ?
    ''', (userId,))
    user_data = cursor.fetchone()

    totalTrainTime, totalAnswers, totalExams, avgDegree, userRate = user_data

    feedback = f"""
    Dear User,
    
    Here is your training feedback:
    
    Total Training Time: {totalTrainTime} seconds
    Total Answers: {totalAnswers}
    Total Exams: {totalExams}
    Average Degree: {avgDegree}
    User Rate: {userRate}
    
    Keep up the good work!
    
    Best regards,
    The ECG Team
    """

    cursor.execute('SELECT email FROM authentication WHERE userId = ?', (userId,))
    user_email = cursor.fetchone()[0]

    send_email(user_email, feedback)

    conn.close()

def send_email(to_email, message):
    from_email = 'your-email@example.com'
    password = 'your-email-password'

    msg = MIMEText(message)
    msg['Subject'] = 'Your Training Feedback'
    msg['From'] = from_email
    msg['To'] = to_email

    with smtplib.SMTP_SSL('smtp.example.com', 465) as server:
        server.login(from_email, password)
        server.sendmail(from_email, to_email, msg.as_string())

if __name__ == "__main__":
    userId = 'example-user-id'
    generate_feedback(userId)

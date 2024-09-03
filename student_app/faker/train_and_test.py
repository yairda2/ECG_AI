import sqlite3
import random
from datetime import datetime
from create_profiles import DB_PATH
from uuid import uuid4  # Import the uuid module to use uuid4

# צריך להוסיף ריצה בלולאה של כל פרופיל מתקיית faker/profiles
# ולהפעיל את הפונקציות train_profile ו- test_profile על כל פרופיל
# כל פרופיל יקבל סט תמונות רנדומלי וישלים אימון ובדיקה עליהן
# כל פעם ישמרו התוצאות במסד הנתונים
# חשוב! יש להוסיף מודל עיבוד תמונה שמשתמש בפרמטרים של כל פרופיל לצורך עיבוד התמונה, אדם חכם הרבה זמן עיבוד אדם יהיר פחות פיצ'רים
# כל פעם יש להכניס את התוצאות למסד הנתונים
# יש לשים לב שכל השורות במסד הנתונים נכנסות כמו שצריך.
# יש להתחקות אחרי בקשות הAPI של מהערכת.

# Connect to the SQLite database
db = sqlite3.connect(DB_PATH)


def train_profile(profile_id, cursor):
    """
    אימון פרופיל באמצעות סיווג תמונות ושמירת תוצאות האימון.

    Parameters:
    - profile_id: מזהה הפרופיל
    - cursor: מחוון למסד הנתונים
    """
    cursor.execute("SELECT photoName FROM imageClassification ORDER BY RANDOM() LIMIT 1")
    image = cursor.fetchone()[0]
    classification_des = random.choice(['LOW RISK', 'HIGH RISK/STEMI'])

    start_time = datetime.now().isoformat()  # Convert datetime to string to avoid warnings
    answer_time = random.randint(10, 100)  # זמן התגובה
    help_activated = random.choice([True, False])
    help_time_activated = random.randint(0, 10) if help_activated else 0

    cursor.execute('''INSERT INTO answers (userId, date, photoName, classificationSetSrc, classificationSubSetSrc,
                      classificationSetDes, classificationSubSetDes, answerSubmitTime, helpActivated, helpTimeActivated)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                   (profile_id, start_time, image, None, None, classification_des, None, answer_time,
                    help_activated, help_time_activated))

    cursor.execute("UPDATE users SET totalTrainTime = totalTrainTime + ?, totalAnswers = totalAnswers + 1 WHERE id = ?",
                   (answer_time, profile_id))


def test_profile(profile_id, cursor):
    """
    בדיקת פרופיל על ידי סיווג תמונות ושמירת תוצאות המבחן.

    Parameters:
    - profile_id: מזהה הפרופיל
    - cursor: מחוון למסד הנתונים
    """
    exam_id = str(uuid4())  # Create a unique exam ID using uuid4
    start_time = datetime.now().isoformat()  # Convert datetime to string to avoid warnings
    total_questions = 10  # מספר השאלות במבחן
    correct_answers = 0

    for i in range(total_questions):
        cursor.execute("SELECT photoName FROM imageClassification ORDER BY RANDOM() LIMIT 1")
        image = cursor.fetchone()[0]
        classification_des = random.choice(['LOW RISK', 'HIGH RISK/STEMI'])

        answer_time = random.randint(10, 100)  # זמן התגובה

        cursor.execute('''INSERT INTO examAnswers (examId, userId, date, answerNumber, photoName, classificationSetSrc, 
                          classificationSubSetSrc, classificationSetDes, answerSubmitTime)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (exam_id, profile_id, start_time, i + 1, image, None, None, classification_des, answer_time))

        # Update correct answers count
        if random.choice([True, False]):
            correct_answers += 1

    score = (correct_answers / total_questions) * 100

    cursor.execute('''INSERT INTO exam (examId, userId, date, severalQuestions, score, totalExamTime, type)
                      VALUES (?, ?, ?, ?, ?, ?, ?)''',
                   (exam_id, profile_id, start_time, total_questions, score, None, 'full'))

    cursor.execute("UPDATE users SET totalExams = totalExams + 1, avgExamTime = (avgExamTime + ?)/2 WHERE id = ?",
                   (score, profile_id))


def run_training_and_testing():
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users")
    profiles = cursor.fetchall()

    for profile in profiles:
        profile_id = profile[0]
        train_profile(profile_id, cursor)
        test_profile(profile_id, cursor)

    db.commit()
    cursor.close()


if __name__ == "__main__":
    run_training_and_testing()
    db.close()
    print("Training and testing completed successfully.")

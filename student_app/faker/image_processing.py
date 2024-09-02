import sqlite3
from directory_structure import DB_PATH
# Connect to the SQLite database
db = sqlite3.connect(DB_PATH)


def update_profile_based_on_feedback(cursor):
    """
    עדכון פרופילים לפי הפידבק שהם קיבלו.

    Parameters:
    - cursor: מחוון למסד הנתונים
    """
    cursor.execute("SELECT id, feedback FROM users")
    profiles = cursor.fetchall()

    for profile in profiles:
        profile_id, feedback = profile

        # לדוגמה: שינוי רמת המוטיבציה בהתאם לפידבק
        if "focus on accuracy" in feedback:
            cursor.execute("UPDATE users SET motivation = motivation + 1 WHERE id = ?", (profile_id,))

        # להוסיף לוגיקות נוספות לשיפור הפרופיל בהתאם לפידבק

    db.commit()


if __name__ == "__main__":
    cursor = db.cursor()
    update_profile_based_on_feedback(cursor)
    cursor.close()
    db.close()
    print("Profiles updated based on feedback.")

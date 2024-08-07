import cv2
import numpy as np
import sqlite3
from tensorflow.keras.models import load_model, save_model
from tensorflow.keras.preprocessing.image import ImageDataGenerator

def analyze_image(image_path):
    model = load_model('image_analysis_model.h5')

    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    image = cv2.resize(image, (128, 128))
    image = image.reshape(1, 128, 128, 1) / 255.0

    rating = model.predict(image)[0][0]

    return rating

def update_model_with_new_images():
    model = load_model('image_analysis_model.h5')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('SELECT photoName, classificationSet FROM imageClassification WHERE rate IS NULL')
    new_images = cursor.fetchall()

    if new_images:
        images = []
        labels = []

        for image in new_images:
            photoName, classificationSet = image
            image_path = f'path/to/images/{photoName}'

            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            img = cv2.resize(img, (128, 128))
            img = img.reshape(128, 128, 1) / 255.0

            images.append(img)
            labels.append(classificationSet)

        label_dict = {'LOW RISK': 0, 'HIGH RISK': 1, 'STEMI': 2}
        labels = np.array([label_dict[label] for label in labels])

        images = np.array(images)

        model.fit(images, labels, epochs=5)

        save_model(model, 'image_analysis_model.h5')

    conn.close()

def process_new_images():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('SELECT photoName FROM imageClassification WHERE rate IS NULL')
    new_images = cursor.fetchall()

    for image in new_images:
        photoName = image[0]
        image_path = f'path/to/images/{photoName}'

        rating = analyze_image(image_path)

        cursor.execute('UPDATE imageClassification SET rate = ? WHERE photoName = ?', (rating, photoName))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    process_new_images()
    update_model_with_new_images()

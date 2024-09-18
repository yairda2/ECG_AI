import tensorflow as tf
import numpy as np
from tensorflow.keras.preprocessing import image

# פונקציה לניתוח תמונה בודדת
def analyze_image(image_path, model_path):
    # טעינת המודל המאומן
    model = tf.keras.models.load_model(model_path)
    
    # טעינת התמונה
    img = image.load_img(image_path, target_size=(224, 224))
    img_array = image.img_to_array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)  # הוספת ממד נוסף

    # ביצוע תחזית
    prediction = model.predict(img_array)
    
    # מציאת הסיווג הסופי
    predicted_class = np.argmax(prediction)
    print(f"Predicted class for image: {predicted_class}")
    
    return predicted_class

# דוגמה לשימוש בפונקציה
image_path = 'path_to_image.jpg'
model_path = 'saved_model/cnn_ecg_model.h5'
analyze_image(image_path, model_path)

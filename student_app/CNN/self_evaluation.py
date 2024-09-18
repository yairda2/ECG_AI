import tensorflow as tf

# הגדרת נתיבים
model_path = 'saved_model/cnn_ecg_model.h5'
train_dir = 'callsifi_images'  # נתיב לתמונות המסווגות

# טעינת המודל
model = tf.keras.models.load_model(model_path)

# מחולל נתונים לולידציה
data_gen = tf.keras.preprocessing.image.ImageDataGenerator(rescale=1./255, validation_split=0.2)
validation_generator = data_gen.flow_from_directory(
    train_dir, target_size=(224, 224), batch_size=32, class_mode='categorical', subset='validation'
)

# הערכת המודל על סט הנתונים הקיימים
test_loss, test_accuracy = model.evaluate(validation_generator)
print(f'Test Accuracy: {test_accuracy * 100:.2f}%')
print(f'Test Loss: {test_loss:.4f}')

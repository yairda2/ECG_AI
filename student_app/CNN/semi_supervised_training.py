import os
import shutil
import torch
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from ultralytics import YOLO  # Import YOLOv8
import yaml

# Define directories and paths
train_dir = 'callsifi_images'  # Path for labeled images
unlabeled_dir = 'unlabeled_images'  # Path for unlabeled images
labeled_dir = 'labeled_images'  # Path for saving classified images
model_save_path = 'saved_model/yolov8_ecg_model.pt'  # Path for saving YOLOv8 model
graphs_dir = 'saved_graphs'  # Path to save accuracy/loss graphs

# Create directories if not exist
os.makedirs(graphs_dir, exist_ok=True)
os.makedirs(labeled_dir, exist_ok=True)

# Load YOLOv8 model
device = 'cuda' if torch.cuda.is_available() else 'cpu'  # Check if GPU is available
model = YOLO('yolov8n.pt')  # Load pre-trained YOLOv8 model (choose small or large depending on needs)

# Define image size and transformations (YOLOv8 uses 640x640 by default)
img_size = 640

# Function to classify and copy unlabeled images
# Function to classify and copy unlabeled images
def classify_unlabeled_images(model, unlabeled_dir, labeled_dir):
    # Load and classify images
    for root, dirs, files in os.walk(unlabeled_dir):
        for file in files:
            if file.endswith('.jpg') or file.endswith('.png'):
                img_path = os.path.join(root, file)

                # Perform prediction with YOLOv8
                results = model.predict(source=img_path, imgsz=img_size)

                # Process predictions
                for result in results:
                    for bbox in result.boxes:
                        cls = bbox.cls.item()  # Get class
                        conf = bbox.conf.item()  # Get confidence
                        label = model.names[int(cls)]  # Get class name

                        print(f'Class: {label}, Confidence: {conf:.2f}, File: {file}')

                        # Define destination directory based on class name
                        destination_dir = os.path.join(labeled_dir, label)
                        os.makedirs(destination_dir, exist_ok=True)

                        # Copy file to the corresponding folder
                        shutil.copy(img_path, os.path.join(destination_dir, file))
                        print(f"Image {file} copied to {destination_dir}")

# Classify the unlabeled images
classify_unlabeled_images(model, unlabeled_dir, labeled_dir)

# Train/Validation split for the dataset
def prepare_dataset(labeled_dir):
    all_images = []
    all_labels = []

    for class_dir in os.listdir(labeled_dir):
        class_path = os.path.join(labeled_dir, class_dir)
        if os.path.isdir(class_path):
            for image_file in os.listdir(class_path):
                all_images.append(os.path.join(class_path, image_file))
                all_labels.append(class_dir)  # Label is the class folder name

    return train_test_split(all_images, all_labels, test_size=0.2, random_state=42)

train_images, val_images, train_labels, val_labels = prepare_dataset(labeled_dir)

# YOLOv8 Training
def train_yolov8(model, train_images, val_images):
    # Prepare YAML configuration for training
    data_config = {
        'train': train_images,
        'val': val_images,
        'nc': len(model.names),  # Number of classes
        'names': model.names  # Class names
    }

    # Save the data config as YAML
    with open('data_config.yaml', 'w') as f:
        yaml.dump(data_config, f)

    # Train YOLOv8
    model.train(data='data_config.yaml', imgsz=img_size, epochs=10, batch=16, device=device)

# Train the model
train_yolov8(model, train_images, val_images)

# Plot and save training graphs
def plot_training_results():
    # Assume 'results.txt' contains logs for training (YOLOv8 saves detailed logs)
    with open('results.txt', 'r') as f:
        lines = f.readlines()

    epochs = list(range(1, len(lines) + 1))
    accuracy = [float(line.split()[1]) for line in lines]
    val_accuracy = [float(line.split()[2]) for line in lines]
    loss = [float(line.split()[3]) for line in lines]
    val_loss = [float(line.split()[4]) for line in lines]

    # Plot accuracy graph
    plt.plot(epochs, accuracy, label='Training Accuracy')
    plt.plot(epochs, val_accuracy, label='Validation Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.legend(loc='lower right')
    plt.title('YOLOv8 Model Accuracy Over Time')
    plt.savefig(os.path.join(graphs_dir, 'yolov8_accuracy_graph.png'))
    plt.close()

    # Plot loss graph
    plt.plot(epochs, loss, label='Training Loss')
    plt.plot(epochs, val_loss, label='Validation Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend(loc='upper right')
    plt.title('YOLOv8 Model Loss Over Time')
    plt.savefig(os.path.join(graphs_dir, 'yolov8_loss_graph.png'))
    plt.close()

# Plot and save the training results
plot_training_results()

# Save the final trained model
model.save(model_save_path)
print(f'Model saved to {model_save_path}')

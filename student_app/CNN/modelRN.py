import os
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader, random_split
from PIL import Image
import matplotlib.pyplot as plt
from torchcam.methods import SmoothGradCAMpp
from torchcam.utils import overlay_mask
import numpy as np
import json
import sys

# הגדרת נתיבים
data_dir = 'callsifi_images'  # נתיב לתמונות המסווגות
unlabeled_dir = 'unlabeled_images'  # נתיב לתמונות הלא מסווגות
model_save_path = 'ecg_classifier_model.pth'  # נתיב לשמירת המודל המאומן
class_names = ['Avrste', 'DeWinters', 'Hyperacute', 'LossOfBalance', 'TInversion', 'Wellens', 'LOW RISK', 'Anterior',
               'Inferior', 'Lateral', 'Septal']

# בדיקה אם יש GPU זמין
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'Device in use: {device}')

# טרנספורמציות על הנתונים
data_transforms = {
    'train': transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.3, contrast=0.3,
                               saturation=0.3, hue=0.2),
        transforms.RandomAffine(degrees=0, shear=10, scale=(0.8, 1.2)),
        transforms.RandomPerspective(distortion_scale=0.2, p=0.5),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ]),
    'val': transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ]),
}


# מחלקה מותאמת לטעינת תמונות מתיקיות ותיקיות משנה
class CustomImageFolder(datasets.ImageFolder):
    def __init__(self, root, transform=None):
        super(CustomImageFolder, self).__init__(root, transform)

    def is_valid_file(self, path):
        return path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'))


# פונקציה לאימון המודל
def train_model(model, criterion, optimizer, num_epochs=10):
    best_acc = 0.0
    best_model_wts = model.state_dict()

    for epoch in range(num_epochs):
        print(f'Epoch {epoch + 1}/{num_epochs}')
        print('-' * 10)

        # שלב אימון
        model.train()
        running_loss = 0.0
        running_corrects = 0

        for inputs, labels in train_loader:
            inputs = inputs.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            loss = criterion(outputs, labels)

            loss.backward()
            optimizer.step()

            running_loss += loss.item() * inputs.size(0)
            running_corrects += torch.sum(preds == labels.data)

        epoch_loss = running_loss / len(train_dataset)
        epoch_acc = running_corrects.double() / len(train_dataset)

        print(f'Train Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}')

        # שלב ולידציה
        model.eval()
        running_loss = 0.0
        running_corrects = 0

        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs = inputs.to(device)
                labels = labels.to(device)

                outputs = model(inputs)
                _, preds = torch.max(outputs, 1)
                loss = criterion(outputs, labels)

                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)

        epoch_loss = running_loss / len(val_dataset)
        epoch_acc = running_corrects.double() / len(val_dataset)

        print(f'Val Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}')

        # שמירת המודל הטוב ביותר
        if epoch_acc > best_acc:
            best_acc = epoch_acc
            best_model_wts = model.state_dict().copy()

    print(f'Best Validation Accuracy: {best_acc:.4f}')

    # טעינת משקלי המודל הטוב ביותר
    model.load_state_dict(best_model_wts)

    return model


# שלב נוסף לאימון על תמונות הלא מסווגות (ללמוד לזהות סריקות אק"ג)
def train_on_unlabeled_ecg(model, unlabeled_loader, optimizer, criterion, num_epochs=5):
    model.train()
    for epoch in range(num_epochs):
        running_loss = 0.0
        for inputs, _ in unlabeled_loader:  # אין תוויות בשלב זה
            inputs = inputs.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            # שימוש במטרה דמיונית (הנחה שכל התמונות הן אק"ג)
            loss = criterion(outputs, torch.ones(outputs.size(0)).long().to(device))
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * inputs.size(0)
        print(f'Epoch [{epoch + 1}/{num_epochs}], Unlabeled Loss: {running_loss / len(unlabeled_loader.dataset):.4f}')
    return model


# טעינת מודל לאימון או סיווג
def load_model():
    model = models.resnet18(pretrained=False)
    num_ftrs = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(0.5),
        nn.Linear(num_ftrs, len(class_names))
    )
    if os.path.exists(model_save_path):
        model.load_state_dict(torch.load(model_save_path, map_location=device))
        print("Model loaded from saved state.")
    model = model.to(device)
    return model


# פונקציה לסיווג תמונה
def classify_image(image_path):
    model = load_model()

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    image = Image.open(image_path).convert('RGB')
    input_tensor = transform(image).unsqueeze(0).to(device)

    model.eval()
    with torch.no_grad():
        outputs = model(input_tensor)
        probabilities = nn.functional.softmax(outputs, dim=1)
        confidence, preds = torch.max(probabilities, 1)
        predicted_class = class_names[preds[0].item()]
        confidence_percent = confidence[0].item() * 100

    # Creating Grad-CAM
    cam_extractor = SmoothGradCAMpp(model, target_layer='layer4')
    _ = model(input_tensor)
    cams = cam_extractor(class_idx=preds[0].item(), scores=outputs)
    activation_map = cams[0].cpu().numpy()

    if len(activation_map.shape) == 3:
        activation_map = np.mean(activation_map, axis=0)

    activation_map = (activation_map - activation_map.min()) / (activation_map.max() - activation_map.min())
    result = overlay_mask(image, Image.fromarray(np.uint8(activation_map * 255), mode='L'), alpha=0.5)

    # Save the Grad-CAM and the color bar separately
    graph_path = image_path.replace('uploads', 'graphs').replace('.jpg', '_graph.png')
    heatmap_path = image_path.replace('uploads', 'graphs').replace('.jpg', '_heatmap.png')

    # Create and save the Grad-CAM image (increase figure size to make it larger)
    plt.figure(figsize=(16, 12))  # Adjust the size here (increased for larger output)
    plt.imshow(result)
    plt.axis('off')  # No labels or title on the image
    plt.savefig(graph_path)

    # Save the color bar (legend) separately (increase the size of the legend if needed)
    plt.figure(figsize=(6, 1))
    plt.imshow(np.linspace(0, 1, 256).reshape(1, 256), cmap='jet', aspect='auto')
    plt.gca().set_yticks([])  # Remove y-axis ticks
    plt.gca().set_xticks([0, 128, 255])  # Only three points: Low, Medium, High
    plt.gca().set_xticklabels(['Low', 'Medium', 'High'])
    plt.title("Heatmap Legend", fontsize=8)
    plt.savefig(heatmap_path)

    # Return classification details and paths to the images
    return {
        'classification': predicted_class,
        'confidence': f'{confidence_percent:.2f}%',
        'graphUrl': graph_path
    }


# פונקציית הרצה ראשית
if __name__ == '__main__':
    if len(sys.argv) >= 2:
        # אם סופקה תמונה, נסווג אותה
        image_path = sys.argv[1]
        result = classify_image(image_path)
        print(json.dumps(result))
    else:
        # אם לא סופקה תמונה, נאמן את המודל
        print("No image provided. Starting model training...")

        # בדיקה אם התיקייה callsifi_images קיימת
        if not os.path.exists(data_dir):
            raise FileNotFoundError(f"The directory {data_dir} does not exist.")

        # אימון המודל
        full_dataset = CustomImageFolder(root=data_dir, transform=data_transforms['train'])
        total_size = len(full_dataset)
        train_size = int(0.7 * total_size)
        val_size = int(0.15 * total_size)
        test_size = total_size - train_size - val_size
        train_dataset, val_dataset, test_dataset = random_split(full_dataset, [train_size, val_size, test_size])

        train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False)

        model = train_model(model, criterion, optimizer, num_epochs=20)

        # שמירת המודל לאחר האימון
        torch.save(model.state_dict(), model_save_path)
        print(f'Model saved at {model_save_path}')

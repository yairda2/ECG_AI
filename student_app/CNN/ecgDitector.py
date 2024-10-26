import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader
from tkinter import Tk, filedialog, Label, Button
from PIL import Image, ImageTk
import os
# פונקציות לאימון ולבדיקה

# הגדרות נתונים וטרנספורמציות
data_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# פונקציית אימון מודל
def train_model(model, train_loader, val_loader, criterion, optimizer, num_epochs=20):
    for epoch in range(num_epochs):
        print(f'Epoch {epoch+1}/{num_epochs}')
        model.train()
        running_loss = 0.0
        corrects = 0

        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * inputs.size(0)
            _, preds = torch.max(outputs, 1)
            corrects += torch.sum(preds == labels.data)

        print(f'Train Loss: {running_loss/len(train_loader.dataset):.4f} Acc: {corrects.double()/len(train_loader.dataset):.4f}')

    return model

# פונקציה לבדיקת תמונה אם היא סריקת אק"ג
def classify_image(model, image_path):
    model.eval()
    image = Image.open(image_path).convert('RGB')
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    input_tensor = transform(image).unsqueeze(0)
    input_tensor = input_tensor.to(device)

    with torch.no_grad():
        output = model(input_tensor)
        _, preds = torch.max(output, 1)
        return preds.item()  # מחזיר 0 או 1 (0 עבור "לא ECG", 1 עבור "ECG")

# פונקציה לפתיחת חלון לבדיקת תמונה
def open_image_window(model):
    root = Tk()
    root.title("ECG Image Classifier")

    def upload_image():
        file_path = filedialog.askopenfilename()
        if file_path:
            img = Image.open(file_path)
            img.thumbnail((300, 300))
            img_tk = ImageTk.PhotoImage(img)

            label_img.config(image=img_tk)
            label_img.image = img_tk

            # סיווג התמונה
            result = classify_image(model, file_path)
            label_result.config(text="ECG" if result == 1 else "Not ECG")

    label_img = Label(root)
    label_img.pack()

    label_result = Label(root, text="Upload an image to classify")
    label_result.pack()

    upload_button = Button(root, text="Upload Image", command=upload_image)
    upload_button.pack()

    root.mainloop()

# קוד ראשי להרצת המודל
if __name__ == '__main__':
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # יצירת מודל ResNet מאומן מראש
    model = models.resnet18(pretrained=True)
    num_ftrs = model.fc.in_features
    model.fc = nn.Linear(num_ftrs, 2)  # סיווג לשתי קטגוריות: ECG או לא ECG
    model = model.to(device)

    # קריטריון ואופטימיזציה
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    # טוענים את הנתונים
    data_dir = 'path_to_your_data'
    train_dataset = datasets.ImageFolder(root=os.path.join(data_dir, 'train'), transform=data_transforms)
    val_dataset = datasets.ImageFolder(root=os.path.join(data_dir, 'val'), transform=data_transforms)
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

    # אימון המודל
    model = train_model(model, train_loader, val_loader, criterion, optimizer, num_epochs=20)

    # שמירת המודל המאומן
    torch.save(model.state_dict(), 'ecg_classifier_model.pth')

    # פתיחת חלון לבדיקת תמונות
    open_image_window(model)

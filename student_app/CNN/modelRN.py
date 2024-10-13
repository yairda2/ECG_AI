# CNN/modelRN.py

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

def main():
    # בדיקה אם יש GPU זמין
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'Device in use: {device}')

    # הגדרת נתיבים
    data_dir = 'callsifi_images'  # נתיב לתמונות המסווגות
    unlabeled_dir = 'unlabeled_images'  # נתיב לתמונות הלא מסווגות
    model_save_path = 'ecg_classifier_model.pth'  # נתיב לשמירת המודל המאומן

    # רשימת שמות הקטגוריות
    class_names = ['Avrste', 'DeWinters', 'Hyperacute', 'LossOfBalance',
                   'TInversion', 'Wellens', 'LOW RISK', 'Anterior', 'Inferior', 'Lateral', 'Septal']

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
            self.samples = self.make_dataset(
                self.root,
                self.class_to_idx,
                extensions=self.extensions,
                is_valid_file=self.is_valid_file,
                allow_empty=False
            )
            self.imgs = self.samples  # תאימות לאחור

        def make_dataset(self, directory, class_to_idx, extensions=None, is_valid_file=None, allow_empty=False):
            images = []
            directory = os.path.expanduser(directory)

            for target in sorted(os.listdir(directory)):
                d = os.path.join(directory, target)
                if not os.path.isdir(d):
                    continue

                for root_, _, fnames in sorted(os.walk(d)):
                    for fname in sorted(fnames):
                        path = os.path.join(root_, fname)
                        if is_valid_file is not None:
                            if not is_valid_file(path):
                                continue
                        else:
                            if not datasets.folder.has_file_allowed_extension(path, extensions):
                                continue

                        item = (path, class_to_idx[target])
                        images.append(item)

            if len(images) == 0 and not allow_empty:
                msg = f"Found 0 files in subfolders of: {directory}\n"
                if extensions is not None:
                    msg += f"Supported extensions are: {','.join(extensions)}"
                raise RuntimeError(msg)

            return images

        def is_valid_file(self, path):
            return path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'))

    # טעינת הנתונים עם המחלקה המותאמת
    full_dataset = CustomImageFolder(root=data_dir, transform=data_transforms['train'])

    # חלוקה לסט אימון, ולידציה ומבחן
    total_size = len(full_dataset)
    train_size = int(0.7 * total_size)
    val_size = int(0.15 * total_size)
    test_size = total_size - train_size - val_size
    train_dataset, val_dataset, test_dataset = random_split(full_dataset, [train_size, val_size, test_size])

    # עדכון הטרנספורמציה לסט הולידציה וסט מבחן
    val_dataset.dataset.transform = data_transforms['val']
    test_dataset.dataset.transform = data_transforms['val']

    # יצירת DataLoader
    batch_size = 16
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    # טעינת מודל ResNet18 עם Dropout ו-L2 Regularization
    from torchvision.models import resnet18, ResNet18_Weights
    model = resnet18(weights=ResNet18_Weights.DEFAULT)

    # התאמת השכבה הסופית והוספת Dropout
    num_ftrs = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(0.5),  # Dropout של 50%
        nn.Linear(num_ftrs, len(class_names))
    )

    model = model.to(device)

    # פונקציית הפסד עם רגולריזציה (L2 Regularization)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)  # weight_decay = L2 Regularization

    # אימון המודל
    num_epochs = 20

    # רשימות לאיסוף נתונים לגרפים
    train_losses = []
    val_losses = []
    train_accuracies = []
    val_accuracies = []

    def train_model(model, criterion, optimizer, num_epochs=10):
        best_acc = 0.0
        best_model_wts = model.state_dict()

        for epoch in range(num_epochs):
            print(f'Epoch {epoch+1}/{num_epochs}')
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

            train_losses.append(epoch_loss)
            train_accuracies.append(epoch_acc.item())

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

            val_losses.append(epoch_loss)
            val_accuracies.append(epoch_acc.item())

            print(f'Val Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}')

            # שמירת המודל הטוב ביותר
            if epoch_acc > best_acc:
                best_acc = epoch_acc
                best_model_wts = model.state_dict().copy()

        print(f'Best Validation Accuracy: {best_acc:.4f}')

        # טעינת משקלי המודל הטוב ביותר
        model.load_state_dict(best_model_wts)

        return model

    # אימון המודל
    model = train_model(model, criterion, optimizer, num_epochs=num_epochs)

    # שמירת המודל
    torch.save(model.state_dict(), model_save_path)
    print(f'Model saved at {model_save_path}')

    # יצירת גרפים של הפסד ודיוק
    epochs = range(1, num_epochs + 1)

    plt.figure(figsize=(12, 5))

    # גרף הפסד
    plt.subplot(1, 2, 1)
    plt.plot(epochs, train_losses, label='Train Loss')
    plt.plot(epochs, val_losses, label='Validation Loss')
    plt.title('Loss over Epochs')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()

    # גרף דיוק
    plt.subplot(1, 2, 2)
    plt.plot(epochs, train_accuracies, label='Train Accuracy')
    plt.plot(epochs, val_accuracies, label='Validation Accuracy')
    plt.title('Accuracy over Epochs')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.legend()

    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    main()

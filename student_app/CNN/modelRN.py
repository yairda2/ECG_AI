import os
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader, random_split
from PIL import Image
import matplotlib.pyplot as plt
import seaborn as sns
from torchcam.methods import SmoothGradCAMpp
from torchcam.utils import overlay_mask

def main():
    # בדיקה אם יש GPU
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'מכשיר בשימוש: {device}')

    # הגדרת נתיבים
    data_dir = 'callsifi_images'  # נתיב לתמונות המסווגות
    unlabeled_dir = 'unlabeled_images'  # נתיב לתמונות הלא מסווגות
    model_save_path = 'ecg_classifier_model.pth'  # נתיב לשמירת המודל המאומן

    # רשימת שמות הקטגוריות
    class_names = ['Avrste', 'DeWinters', 'Hyperacute', 'LossOfBalance',
                   'TInversion', 'Wellens', 'LOW RISK', 'STEMI']

    # טרנספורמציות על הנתונים
    data_transforms = {
        'train': transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            transforms.ColorJitter(brightness=0.2, contrast=0.2,
                                   saturation=0.2, hue=0.2),
            transforms.ToTensor(),
        ]),
        'val': transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
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

    # טעינת מודל ResNet18 עם המשקלים המעודכנים
    from torchvision.models import resnet18, ResNet18_Weights
    model = resnet18(weights=ResNet18_Weights.DEFAULT)

    # התאמת השכבה הסופית
    num_ftrs = model.fc.in_features
    model.fc = nn.Linear(num_ftrs, len(class_names))

    model = model.to(device)

    # פונקציית הפסד ואופטימייזר
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    # אימון המודל
    num_epochs = 20

    # רשימות לאיסוף נתונים לגרפים
    train_losses = []
    val_losses = []
    train_accuracies = []
    val_accuracies = []

    def train_model(model, criterion, optimizer, num_epochs=10):
        best_acc = 0.0

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

        # טעינת המודל הטוב ביותר
        model.load_state_dict(best_model_wts)

        return model

    # אימון המודל
    model = train_model(model, criterion, optimizer, num_epochs=num_epochs)

    # שמירת המודל
    torch.save(model.state_dict(), model_save_path)
    print(f'מודל נשמר ב-{model_save_path}')

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

    # פונקציה לסיווג תמונה חדשה עם Grad-CAM
    def classify_image_with_explanation(model, image_path):
        model.eval()
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
        ])

        image = Image.open(image_path).convert('RGB')
        input_tensor = transform(image).unsqueeze(0).to(device)

        # יצירת Grad-CAM לפני ה-forward pass
        cam_extractor = SmoothGradCAMpp(model, target_layer='layer4')

        # ביצוע forward pass
        outputs = model(input_tensor)
        probabilities = nn.functional.softmax(outputs, dim=1)
        confidence, preds = torch.max(probabilities, 1)
        predicted_class = class_names[preds[0].item()]
        confidence_percent = confidence[0].item() * 100
        print(f'קובץ: {os.path.basename(image_path)}, סווג כ: {predicted_class} ({confidence_percent:.2f}%)')

        # יצירת CAM
        cams = cam_extractor(class_idx=preds[0].item(), scores=outputs)

        # קבלת המפה של השכבה האחרונה
        activation_map = cams[0].cpu()

        # חפיפה של המפה על התמונה המקורית
        result = overlay_mask(image, Image.fromarray(activation_map.numpy(), mode='F'), alpha=0.5)

        # הצגת התמונה עם ההסבר
        plt.figure(figsize=(8, 8))
        plt.imshow(result)
        plt.title(f'{predicted_class} ({confidence_percent:.2f}%)')
        plt.axis('off')
        plt.show()

        # הסבר על ההחלטה
        explanation = f"התמונה סווגה כ-{predicted_class} עם ביטחון של {confidence_percent:.2f}%"
        return predicted_class, confidence_percent, explanation

    # סיווג התמונות הלא מסווגות עם הסברים
    for root, _, files in os.walk(unlabeled_dir):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                img_path = os.path.join(root, file)
                predicted_class, confidence, explanation = classify_image_with_explanation(model, img_path)
                # ניתן להעביר את התמונה לתיקייה לפי הסיווג או לבצע פעולה אחרת

    # בדיקת המודל על סט המבחן
    def evaluate_model(model, test_loader):
        model.eval()
        running_corrects = 0

        with torch.no_grad():
            for inputs, labels in test_loader:
                inputs = inputs.to(device)
                labels = labels.to(device)

                outputs = model(inputs)
                _, preds = torch.max(outputs, 1)

                running_corrects += torch.sum(preds == labels.data)

        test_acc = running_corrects.double() / len(test_dataset)
        print(f'Test Accuracy: {test_acc:.4f}')

    evaluate_model(model, test_loader)

if __name__ == '__main__':
    main()

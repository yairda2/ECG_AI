import os
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import transforms, models
from torch.utils.data import DataLoader, random_split
from PIL import Image
import matplotlib.pyplot as plt
from torchcam.methods import SmoothGradCAMpp
from torchcam.utils import overlay_mask
import numpy as np
import json
import sys
from torchvision.datasets import DatasetFolder, ImageFolder
from torchvision.datasets.folder import default_loader
from torchvision.models import ResNet18_Weights
from torch.utils.data import Dataset

# Path definitions
data_dir = 'callsifi_images'  # path to classified images
unlabeled_dir = 'unlabeled_images'  # path to unclassified images
model_save_path = 'ecg_classifier_model.pth'  # path to trained model
class_names = ['Avrste', 'DeWinters', 'Hyperacute', 'LossOfBalance', 'TInversion', 'Wellens', 'LOW RISK', 'Anterior',
               'Inferior', 'Lateral', 'Septal']

# Check for GPU availability
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'Device in use: {device}')

# Define data transformations
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

# Classification feature definitions
classification_features = {
    "Avrste": {"t_wave_negative": True, "st_changes": True},
    "DeWinters": {"t_wave_high": True, "st_depression": True},
    "Hyperacute": {"t_wave_wide": True, "st_elevation": True},
    "LossOfBalance": {"extreme_st_changes": True},
    "TInversion": {"t_wave_inversion": True},
    "Wellens": {"t_wave_negative": True, "specific_leads": ["V2", "V3"]},
    "LOW RISK": {"minimal_changes": True},
    "Anterior": {"st_elevation": True, "leads": ["V1", "V2", "V3", "V4"]},
    "Inferior": {"st_elevation": True, "leads": ["II", "III", "aVF"]},
    "Lateral": {"st_elevation": True, "leads": ["I", "aVL", "V5", "V6"]},
    "Septal": {"st_elevation": True, "leads": ["V1", "V2"]}
}

# Function to ensure the GRAPH directory exists
def ensure_graph_dir():
    graph_dir = 'GRAPH'
    if not os.path.exists(graph_dir):
        os.makedirs(graph_dir)
        print(f"DEBUG: Created directory {graph_dir} for saving graphs.")
    return graph_dir

# Custom dataset for unlabeled images
class UnlabeledDataset(Dataset):
    def __init__(self, root, transform=None):
        self.root = root
        self.transform = transform
        self.samples = [os.path.join(root, f) for f in os.listdir(root) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'))]

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        path = self.samples[index]
        sample = default_loader(path)
        if self.transform is not None:
            sample = self.transform(sample)
        return sample, -1  # Return -1 as a placeholder label for unlabeled data

# Custom loss function with feature-based penalty
def custom_loss(outputs, labels, features):
    base_loss = nn.CrossEntropyLoss()(outputs, labels)
    penalty = 0.0

    if features is None or len(features) != len(labels):
        print("\033[91mDEBUG: Features list is missing or length mismatch. Returning base loss only.\033[0m")
        return base_loss

    for i, label in enumerate(labels):
        class_name = class_names[label.item()]
        required_features = classification_features.get(class_name, {})

        print(f"DEBUG: Required features for {class_name}: {required_features}")
        print(f"DEBUG: Provided features: {features[i]}")

        # Feature check for required features
        for feature_name in required_features:
            if required_features.get(feature_name) and not features[i].get(feature_name):
                print(f"DEBUG: Missing feature '{feature_name}'")
                penalty += 0.5

    print(f"DEBUG: Computed custom loss - Base: {base_loss.item():.4f}, Penalty: {penalty:.4f}")
    return base_loss + penalty

# Extract ECG-specific features (dummy example function)
def extract_features(image):
    # Replace with actual feature extraction logic
    features = {
        "t_wave_high": True,  # Dummy values
        "st_depression": True
    }

    # Debugging output to check feature extraction
    print(f"DEBUG: Extracted features: {features}")
    return features


# Train on unlabeled ECG images to learn general patterns
def train_on_unlabeled_ecg(model, unlabeled_loader, optimizer, criterion, num_epochs=50, max_images=10000):
    model.train()
    print("DEBUG: Starting training on unlabeled data.")
    loss_history = []  # To store loss values for plotting
    print_interval = 5  # Print progress every 5 batches

    # Early stopping variables
    consecutive_low_loss_epochs = 0  # Count epochs with low loss
    low_loss_threshold = 0.1  # Loss threshold to trigger early stopping
    low_loss_epochs_to_stop = 3  # Number of consecutive low-loss epochs to stop training

    for epoch in range(num_epochs):
        running_loss = 0.0
        image_count = 0
        batch_low_loss_count = 0  # Track low-loss batches within the epoch
        print(f"\nDEBUG: Starting Epoch [{epoch + 1}/{num_epochs}]")

        # Iterate through unlabeled data
        for batch_idx, (inputs, _) in enumerate(unlabeled_loader):
            if image_count >= max_images:
                print(f"DEBUG: Reached maximum of {max_images} images for this epoch.")
                break

            inputs = inputs.to(device)
            optimizer.zero_grad()

            # Forward pass
            outputs = model(inputs)
            # Compute loss
            loss = criterion(outputs, torch.ones(outputs.size(0)).long().to(device))
            # Backward pass and optimization
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * inputs.size(0)
            image_count += inputs.size(0)

            # Check if this batch loss is below threshold
            if loss.item() < low_loss_threshold:
                batch_low_loss_count += 1

            # Add debug output for every print interval
            if (batch_idx + 1) % print_interval == 0 or (batch_idx + 1) == len(unlabeled_loader):
                print(f"DEBUG: Epoch [{epoch + 1}/{num_epochs}], Batch [{batch_idx + 1}/{len(unlabeled_loader)}], "
                      f"Loss: {loss.item():.4f}, Accumulated Loss: {running_loss / image_count:.4f}")

        # Average loss per epoch
        epoch_loss = running_loss / min(image_count, max_images)
        loss_history.append(epoch_loss)
        print(f'Epoch [{epoch + 1}/{num_epochs}], Unlabeled Loss: {epoch_loss:.4f}')
        print("DEBUG: End of Epoch.")

        # Check if the number of low-loss batches exceeds 80% of the epoch’s batches
        if batch_low_loss_count >= 0.8 * len(unlabeled_loader):
            consecutive_low_loss_epochs += 1
            print(f"DEBUG: Low-loss batches detected. Consecutive low-loss epochs: {consecutive_low_loss_epochs}")
            if consecutive_low_loss_epochs >= low_loss_epochs_to_stop:
                print(f"DEBUG: Loss has been below {low_loss_threshold} for {low_loss_epochs_to_stop} consecutive epochs. Stopping early.")
                break
        else:
            consecutive_low_loss_epochs = 0  # Reset if loss goes above threshold for significant batches

    print("DEBUG: Training on unlabeled data complete.")

    # Plotting the loss history
    graph_dir = ensure_graph_dir()

    plt.figure(figsize=(10, 5))
    plt.plot(range(1, len(loss_history) + 1), loss_history, marker='o', color='b', label='Unlabeled Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.title('Training Loss on Unlabeled Data Over Epochs')
    plt.legend()
    plt.grid()

    # Save the plot
    loss_plot_path = os.path.join(graph_dir, 'unlabeled_loss_plot.png')
    plt.savefig(loss_plot_path)
    print(f"Loss plot saved at {loss_plot_path}")

    return model

def train_model(model, optimizer, num_epochs=20):
    best_acc = 0.0
    best_model_wts = model.state_dict()
    train_loss_history = []
    val_loss_history = []
    print_interval = 10  # Adjust this value as needed

    for epoch in range(num_epochs):
        print(f'\nEpoch {epoch + 1}/{num_epochs}')
        print('-' * 10)

        # Training phase
        model.train()
        running_loss = 0.0
        running_corrects = 0

        for batch_idx, (inputs, labels) in enumerate(train_loader):
            inputs = inputs.to(device)
            labels = labels.to(device)

            # Generate features for the current batch
            features = [extract_features(img) for img in inputs.cpu()]

            # Define custom criterion based on features
            criterion = lambda outputs, labels: custom_loss(outputs, labels, features)

            optimizer.zero_grad()
            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            loss = criterion(outputs, labels)

            loss.backward()
            optimizer.step()

            running_loss += loss.item() * inputs.size(0)
            running_corrects += torch.sum(preds == labels.data)

            # Add debug output here
            if (batch_idx + 1) % print_interval == 0 or (batch_idx + 1) == len(train_loader):
                accumulated_loss = running_loss / ((batch_idx + 1) * inputs.size(0))
                print(f"DEBUG: Epoch [{epoch + 1}/{num_epochs}], Batch [{batch_idx + 1}/{len(train_loader)}], Loss: {loss.item():.4f}, Accumulated Loss: {accumulated_loss:.4f}")

        epoch_loss = running_loss / len(train_dataset)
        train_loss_history.append(epoch_loss)
        epoch_acc = running_corrects.double() / len(train_dataset)

        print(f'Train Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}')

        # Validation phase
        model.eval()
        val_running_loss = 0.0
        running_corrects = 0

        with torch.no_grad():
            for batch_idx, (inputs, labels) in enumerate(val_loader):
                inputs = inputs.to(device)
                labels = labels.to(device)

                features = [extract_features(img) for img in inputs.cpu()]
                criterion = lambda outputs, labels: custom_loss(outputs, labels, features)

                outputs = model(inputs)
                _, preds = torch.max(outputs, 1)
                loss = criterion(outputs, labels)

                val_running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)

                # Add debug output here
                if (batch_idx + 1) % print_interval == 0 or (batch_idx + 1) == len(val_loader):
                    print(f"DEBUG: Validation Epoch [{epoch + 1}/{num_epochs}], Batch [{batch_idx + 1}/{len(val_loader)}], Loss: {loss.item():.4f}")

        epoch_val_loss = val_running_loss / len(val_dataset)
        val_loss_history.append(epoch_val_loss)
        epoch_acc = running_corrects.double() / len(val_dataset)

        print(f'Val Loss: {epoch_val_loss:.4f} Acc: {epoch_acc:.4f}')

        # Save best model
        if epoch_acc > best_acc:
            best_acc = epoch_acc
            best_model_wts = model.state_dict().copy()
            print(f"DEBUG: New best model with accuracy {best_acc:.4f} found, saving weights")

    print(f'\nBest Validation Accuracy: {best_acc:.4f}')
    model.load_state_dict(best_model_wts)

    # Save training and validation loss graphs
    graph_dir = ensure_graph_dir()

    plt.figure(figsize=(10, 5))
    plt.plot(range(1, len(train_loss_history) + 1), train_loss_history, marker='o', color='b', label='Training Loss')
    plt.plot(range(1, len(val_loss_history) + 1), val_loss_history, marker='o', color='r', label='Validation Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.title('Training and Validation Loss Over Epochs')
    plt.legend()
    plt.grid()

    # Save the plot
    loss_plot_path = os.path.join(graph_dir, 'labeled_loss_plot.png')
    plt.savefig(loss_plot_path)
    print(f"Loss plot saved at {loss_plot_path}")

    return model

# Load model
def load_model():
    print("DEBUG: Loading model...")
    model = models.resnet18(weights=ResNet18_Weights.DEFAULT)
    num_ftrs = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(0.5),
        nn.Linear(num_ftrs, len(class_names))
    )
    if os.path.exists(model_save_path):
        model.load_state_dict(torch.load(model_save_path, map_location=device, weights_only=True))
        print("DEBUG: Model loaded from saved state.")
    model = model.to(device)
    print("DEBUG: Model is ready.")
    return model

# Classify image and return results
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

    # Creating Grad-CAM with layer2
    cam_extractor = SmoothGradCAMpp(model, target_layer='layer4')
    _ = model(input_tensor)
    cams = cam_extractor(class_idx=preds[0].item(), scores=outputs)
    activation_map = cams[0].cpu().numpy()

    if len(activation_map.shape) == 3:
        activation_map = np.mean(activation_map, axis=0)

    # Normalize and threshold the heatmap
    activation_map = (activation_map - activation_map.min()) / (activation_map.max() - activation_map.min())
    activation_map = np.where(activation_map > 0.5, activation_map, 0)

    result = overlay_mask(image, Image.fromarray(np.uint8(activation_map * 255), mode='L'), alpha=0.7)

    # Save Grad-CAM and color bar images
    graph_path = image_path.replace('uploads', 'graphs').replace('.jpg', '_graph.png')
    heatmap_path = image_path.replace('uploads', 'graphs').replace('.jpg', '_heatmap.png')

    # Save Grad-CAM image
    plt.figure(figsize=(16, 12))
    plt.imshow(result)
    plt.axis('off')
    plt.savefig(graph_path, bbox_inches='tight')

    # Save heatmap legend
    plt.figure(figsize=(6, 1))
    plt.imshow(np.linspace(0, 1, 256).reshape(1, 256), cmap='jet', aspect='auto')
    plt.gca().set_yticks([])
    plt.gca().set_xticks([0, 128, 255])
    plt.gca().set_xticklabels(['Low', 'Medium', 'High'])
    plt.title("Heatmap Legend", fontsize=8)
    plt.savefig(heatmap_path)

    # Return classification details
    return {
        'classification': predicted_class,
        'confidence': f'{confidence_percent:.2f}%',
        'graphUrl': graph_path
    }

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        image_path = sys.argv[1]
        print("DEBUG: Image path provided, running classification.")
        result = classify_image(image_path)
        print("DEBUG: Classification complete. Result:")
        print(json.dumps(result))
    else:
        print("No image provided. Starting model training...")

        # Check if labeled images directory exists
        if not os.path.exists(data_dir):
            raise FileNotFoundError(f"DEBUG: The directory {data_dir} does not exist.")
        print("DEBUG: Labeled data directory found.")

        # Check if unlabeled images directory exists
        if not os.path.exists(unlabeled_dir):
            raise FileNotFoundError(f"DEBUG: The directory {unlabeled_dir} does not exist.")
        print("DEBUG: Unlabeled data directory found.")

        # Load unlabeled dataset
        print("DEBUG: Loading unlabeled dataset...")
        unlabeled_dataset = UnlabeledDataset(root=unlabeled_dir, transform=data_transforms['train'])
        unlabeled_loader = DataLoader(unlabeled_dataset, batch_size=16, shuffle=True)
        print(f"DEBUG: Unlabeled dataset loaded with {len(unlabeled_dataset)} samples.")

        # Load the model
        model = load_model()
        optimizer = optim.Adam(model.parameters(), lr=0.001)
        criterion = nn.CrossEntropyLoss()

        # Train on unlabeled ECG images
        print("DEBUG: Starting training on unlabeled ECG data...")
        model = train_on_unlabeled_ecg(model, unlabeled_loader, optimizer, criterion, num_epochs=20, max_images=100)
        print("DEBUG: Finished training on unlabeled data.")

        # Prepare labeled data for training
        print("DEBUG: Loading labeled dataset for main training...")
        full_dataset = ImageFolder(root=data_dir, transform=data_transforms['train'])
        train_size = int(0.7 * len(full_dataset))
        val_size = int(0.15 * len(full_dataset))
        test_size = len(full_dataset) - train_size - val_size
        train_dataset, val_dataset, test_dataset = random_split(full_dataset, [train_size, val_size, test_size])

        print(f"DEBUG: Labeled dataset split - Train size: {train_size}, Validation size: {val_size}, Test size: {test_size}")

        train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False)

        # Start training on labeled data
        print("DEBUG: Starting main training with labeled data...")
        model = train_model(model=model, optimizer=optimizer, num_epochs=20)
        print("DEBUG: Training complete.")

        # Save the trained model
        torch.save(model.state_dict(), model_save_path)
        print(f"DEBUG: Model saved at {model_save_path}")

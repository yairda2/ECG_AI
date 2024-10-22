from torchvision.models import resnet18, ResNet18_Weights
import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import json
import matplotlib.pyplot as plt
from torchcam.methods import SmoothGradCAMpp
from torchcam.utils import overlay_mask
import numpy as np
import os
import sys

# Define the model path
current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir,'..','CNN', 'ecg_classifier_model.pth')
# Define class names
class_names = ['Avrste', 'DeWinters', 'Hyperacute', 'LossOfBalance', 'TInversion', 'Wellens', 'LOW RISK', 'Anterior', 'Inferior', 'Lateral', 'Septal']

def load_model():
    # Define the model structure
    model = resnet18(weights=ResNet18_Weights.DEFAULT)
    num_ftrs = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(0.5),
        nn.Linear(num_ftrs, len(class_names))
    )
    # Load state dict
    model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu'), weights_only=True))
    model.eval()
    return model

def classify_image(image_path):
    # Load the model
    model = load_model()

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
    ])

    # Open the image and apply transformations
    image = Image.open(image_path).convert('RGB')
    input_tensor = transform(image).unsqueeze(0)

    # Initialize Grad-CAM for explanation
    cam_extractor = SmoothGradCAMpp(model, target_layer='layer4')

    # Forward pass through the model
    outputs = model(input_tensor)
    probabilities = nn.functional.softmax(outputs, dim=1)
    confidence, preds = torch.max(probabilities, 1)
    predicted_class = class_names[preds[0].item()]
    confidence_percent = confidence[0].item() * 100

    # Create the Grad-CAM heatmap
    cams = cam_extractor(class_idx=preds[0].item(), scores=outputs)
    activation_map = cams[0].cpu().numpy()

    # Ensure the activation map is 2D
    if len(activation_map.shape) == 3:
        activation_map = np.mean(activation_map, axis=0)

    # Normalize the heatmap
    activation_map = (activation_map - activation_map.min()) / (activation_map.max() - activation_map.min())

    # Overlay heatmap on the original image
    result = overlay_mask(image, Image.fromarray(np.uint8(activation_map * 255), mode='L'), alpha=0.5)

    # Save the result as a graph
    graph_path = image_path.replace('uploads', 'graphs').replace('.jpg', '_graph.png')
    plt.figure(figsize=(10, 8))  # שינוי גודל התמונה

    plt.subplot(1, 2, 1)  # הוספת subplot עבור התמונה עם מפת החום
    plt.imshow(result)
    plt.title(f'{predicted_class} ({confidence_percent:.2f}%)')
    plt.axis('off')

    # הוספת מקרא ויזואלי בצד
    plt.subplot(1, 2, 2)  # הוספת subplot עבור המקרא
    plt.imshow(np.linspace(0, 1, 100).reshape(1, 100), cmap='jet', aspect='auto')
    plt.gca().set_yticks([])
    plt.gca().set_xticks([0, 50, 100])
    plt.gca().set_xticklabels(['Low', 'Medium', 'High'])
    plt.title("Heatmap Legend")

    plt.tight_layout()
    plt.savefig(graph_path)

    # Return the classification and graph URL
    return {
        'classification': predicted_class,
        'confidence': f'{confidence_percent:.2f}%',
        'graphUrl': graph_path
    }

if __name__ == '__main__':
    # Debug print
    print(sys.argv)
    # Check if an image path was provided as an argument
    if len(sys.argv) < 2:
        print("Please provide an image path as an argument.")
        sys.exit(1)
    # Classify the image


    image_path = sys.argv[1]


    result = classify_image(image_path)
    print(json.dumps(result))

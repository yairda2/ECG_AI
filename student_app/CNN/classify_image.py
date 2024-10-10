# CNN/classify_image.py

import sys
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
from torchvision.models import resnet18  # Ensure this import is present

# Load class names from modelRN.py
class_names = ['Avrste', 'DeWinters', 'Hyperacute', 'LossOfBalance', 'TInversion', 'Wellens', 'LOW RISK', 'Anterior', 'Inferior', 'Lateral', 'Septal']

print(f"Current working directory: {os.getcwd()}")

# Create the same model architecture as in modelRN.py
def load_model():
    model = resnet18(weights=None)  # Don't load pretrained weights here
    num_ftrs = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(0.5),
        nn.Linear(num_ftrs, len(class_names))
    )
    return model

# Path: CNN/classify_image.py
current_dir = os.path.dirname(os.path.abspath(__file__))
path_model = os.path.join(current_dir, 'ecg_classifier_model.pth')

# Load the model and weights
model = load_model()
model.load_state_dict(torch.load(path_model, map_location=torch.device('cpu')))
model.eval()


def classify_image(image_path):
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

    # Ensure the activation map is 2D (if it's 3D, take the mean across channels)
    if len(activation_map.shape) == 3:
        activation_map = np.mean(activation_map, axis=0)

    # Normalize the heatmap
    activation_map = (activation_map - activation_map.min()) / (activation_map.max() - activation_map.min())

    # Overlay heatmap on the original image
    result = overlay_mask(image, Image.fromarray(np.uint8(activation_map * 255), mode='L'), alpha=0.5)

    # Save the result as a graph
    graph_path = image_path.replace('uploads', 'graphs').replace('.jpg', '_graph.png')
    plt.imshow(result)
    plt.title(f'{predicted_class} ({confidence_percent:.2f}%)')
    plt.axis('off')
    plt.savefig(graph_path)

    # Return the classification and graph URL
    return {
        'classification': predicted_class,
        'confidence': f'{confidence_percent:.2f}%',
        'graphUrl': graph_path
    }

if __name__ == '__main__':
    image_path = sys.argv[1]
    result = classify_image(image_path)
    print(json.dumps(result))

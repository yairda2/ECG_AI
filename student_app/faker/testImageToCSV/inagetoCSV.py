import cv2
import numpy as np
import pandas as pd


def detect_ecg_parameters(image_path):
    # Load the ECG image
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    if image is None:
        print(f"Error: Unable to open image {image_path}")
        return None

    # Apply a filter to enhance waves and remove noise
    blurred_image = cv2.GaussianBlur(image, (5, 5), 0)

    # Detect edges in the image
    edges = cv2.Canny(blurred_image, 50, 150)

    # Detect lines using Hough Transform
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=50, maxLineGap=10)

    parameters = {
        'P_wave_count': 0,
        'QRS_complex_count': 0,
        'T_wave_count': 0,
        'PR_interval': 0,  # מרווח בין גל P ל-QRS
        'QT_interval': 0,  # מרווח בין גל Q ל-T
        'ST_segment': 0,  # גובה ST segment
        'Heart_rate': 0,  # קצב לב (בממוצע)
        'RR_interval': 0,  # מרווח בין גלי R רצופים
        # Additional parameters can be added here
    }

    # Process and identify parameters
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # Example checks for P, QRS, T waves, intervals, etc.
            if abs(x2 - x1) > 50:  # Example check for QRS complex
                parameters['QRS_complex_count'] += 1
            if abs(y2 - y1) > 30:  # Example check for T wave
                parameters['T_wave_count'] += 1
            # Example for detecting intervals (this would need to be expanded)
            # For instance, identifying the start and end points of P, QRS, and T waves
            # Then calculating the intervals between them (e.g., PR, QT, RR)

    # Example calculation of derived parameters:
    if parameters['QRS_complex_count'] > 0 and parameters['RR_interval'] > 0:
        parameters['Heart_rate'] = 60 / parameters['RR_interval']  # Simplified calculation

    return parameters


def save_parameters_to_csv(parameters, csv_path):
    df = pd.DataFrame([parameters])
    df.to_csv(csv_path, index=False)


def process_ecg_image(image_path, csv_path):
    parameters = detect_ecg_parameters(image_path)
    if parameters:
        save_parameters_to_csv(parameters, csv_path)
        print(f"Parameters saved to {csv_path}")
    else:
        print("No parameters detected.")


image_path = r"C:\Users\yair\Documents\GitHub\EEG_AI_firsst_collect\student_app\public\img\graded\LOW RISK\0744_patient.jpg"

# Example usage
process_ecg_image(f'{image_path}', 'output_parameters.csv')
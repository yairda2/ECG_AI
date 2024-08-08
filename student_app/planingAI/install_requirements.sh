#!/bin/bash

# Update package list
sudo apt-get update

# Install pip and necessary system packages
sudo apt-get install -y python3-pip python3-venv

# Install virtualenv
pip3 install virtualenv

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install required Python libraries
pip install opencv-python-headless smtplib logging

# Deactivate the virtual environment
deactivate

echo "Installation completed successfully."

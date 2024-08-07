@echo off

REM Check if Python is installed
python --version
IF %ERRORLEVEL% NEQ 0 (
    echo Python is not installed. Please install Python and try again.
    exit /b 1
)

REM Install pip
python -m ensurepip --upgrade

REM Install virtualenv
pip install virtualenv

REM Create a virtual environment
virtualenv venv

REM Activate the virtual environment
call venv\Scripts\activate

REM Install required Python libraries
pip install sqlite3 opencv-python-headless smtplib logging

REM Deactivate the virtual environment
call venv\Scripts\deactivate

echo Installation completed successfully.
pause

#!/bin/bash

# Ensure Python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python3 is not installed. Please install Python3 first."
    exit 1
fi

# Ensure python3-venv is installed
if ! dpkg -s python3-venv &>/dev/null; then
    echo "Installing python3-venv..."
    sudo apt update && sudo apt install -y python3-venv
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Ensure pip is up to date
pip install --upgrade pip

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install --no-cache-dir -r requirements.txt
fi

# Kill any existing Python processes running server.py
pkill -f "python3 server.py"

# Wait a moment for the port to be freed
sleep 1

# Start the server in the background
nohup python server.py &> server.log &

# Deactivate virtual environment
deactivate

# Exit successfully
exit 0

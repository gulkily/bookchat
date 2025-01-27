#!/bin/bash

# Check if pip3 is installed
if ! command -v pip3 &> /dev/null; then
    echo "pip3 is not installed. Please install Python3 and pip3 first."
    exit 1
fi

# Get list of installed packages
installed_packages=$(pip3 freeze)
missing_deps=false

while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip empty lines and comments
    [[ -z "$line" || "$line" =~ ^#.*$ ]] && continue
    
    # Remove any version specifiers and whitespace
    required_package=$(echo "$line" | sed 's/[<>=~].*//' | tr -d '[:space:]')
    
    # Check if package is in installed packages
    if ! echo "$installed_packages" | grep -qi "^${required_package}=="; then
        echo "Missing dependency: $required_package"
        missing_deps=true
    fi
done < requirements.txt

if [ "$missing_deps" = true ]; then
    echo "Installing missing dependencies..."
    pip3 install -r requirements.txt
else
    echo "All dependencies already installed, skipping..."
fi

# Kill any existing Python processes running server.py
pkill -f "python3 server.py"

# Wait a moment for the port to be freed
sleep 1

# Start the server in the background
python3 server.py &

# Exit successfully
exit 0
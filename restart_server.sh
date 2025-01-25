#!/bin/bash

# Check if pip3 is installed
if ! command -v pip3 &> /dev/null; then
    echo "pip3 is not installed. Please install Python3 and pip3 first."
    exit 1
fi

# Function to extract module name from requirement line
# Handles both simple (requests==2.31.0) and complex (python-dotenv==1.0.0) package names
get_module_name() {
    local req=$1
    # Get everything before == or >= or <= or ~=
    local module=$(echo "$req" | sed 's/[=<>~].*//')
    # Convert - to _ for import compatibility
    echo "${module//-/_}"
}

# Check if any dependencies are missing
missing_deps=false
while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip empty lines and comments
    [[ -z "$line" || "$line" =~ ^#.*$ ]] && continue
    
    module=$(get_module_name "$line")
    if ! python3 -c "import $module" &> /dev/null; then
        echo "Missing dependency: $module"
        missing_deps=true
        break
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
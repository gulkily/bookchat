#!/bin/bash

# Function to cleanup on exit
cleanup() {
    echo "Cleaning up..."
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null
    fi
    rm -f server_output.txt
    exit
}

# Set up trap for cleanup
trap cleanup EXIT INT TERM

# Start the Python server and capture its output
echo "Starting Python server..."
python3 server.py 2>server_output.txt &
SERVER_PID=$!

# Wait for the server to output the port (with timeout)
TIMEOUT=30
COUNTER=0
while [ $COUNTER -lt $TIMEOUT ]; do
    if grep -q "export SERVER_PORT=" server_output.txt; then
        break
    fi
    sleep 1
    let COUNTER=COUNTER+1
done

if [ $COUNTER -eq $TIMEOUT ]; then
    echo "Error: Server did not start within ${TIMEOUT} seconds"
    exit 1
fi

# Get the port from the server output and export it
export $(grep "export SERVER_PORT=" server_output.txt)

if [ -z "$SERVER_PORT" ]; then
    echo "Error: Could not get server port"
    exit 1
fi

echo "Server started on port $SERVER_PORT"

# Wait a bit for the server to be fully ready
sleep 2

# Run the tests
echo "Running E2E tests..."
npm run test:e2e
TEST_EXIT_CODE=$?

# Exit with the test exit code
exit $TEST_EXIT_CODE

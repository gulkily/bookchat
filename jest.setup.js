// Import functions to test
const fs = require('fs');
const path = require('path');

// Read and evaluate main.js
const mainJsPath = path.join(__dirname, 'static', 'js', 'main.js');
const mainJsContent = fs.readFileSync(mainJsPath, 'utf8');

// Make functions available globally for tests
global.formatTimestamp = eval(`(function() {
    ${mainJsContent}
    return formatTimestamp;
})()`);

global.sendMessage = eval(`(function() {
    ${mainJsContent}
    return sendMessage;
})()`);

// Setup DOM elements that might be needed
document.body.innerHTML = `
    <div id="messages-container"></div>
    <div id="messages"></div>
`;

// Mock fetch globally
global.fetch = jest.fn();

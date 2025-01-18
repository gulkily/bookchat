// Import required modules
const fs = require('fs');
const path = require('path');

// Set up DOM environment
document.body.innerHTML = `
    <div id="messages">
        <div id="messages-container"></div>
    </div>
`;

// Read main.js content
const mainJsContent = fs.readFileSync(path.join(__dirname, '..', 'static', 'js', 'main.js'), 'utf8');

// Create a function wrapper to execute main.js in the global scope
const functionWrapper = `
  ${mainJsContent}
`;

// Execute the wrapped code and store exported functions
const exportedFunctions = {};
(function() {
  eval(functionWrapper);
  exportedFunctions.sendMessage = sendMessage;
  exportedFunctions.createMessageElement = createMessageElement;
  exportedFunctions.loadMessages = loadMessages;
})();

describe('Message Functions', () => {
  test('createMessageElement should return an HTMLElement', () => {
    const message = {
      content: 'Test message',
      author: 'testuser',
      timestamp: new Date().toISOString()
    };
    const element = exportedFunctions.createMessageElement(message);
    expect(element).toBeDefined();
    expect(element.nodeType).toBe(1); // 1 represents an Element node
  });

  // Add more test cases as needed
});

// Export the functions for use in tests
module.exports = exportedFunctions;

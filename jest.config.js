module.exports = {
    testEnvironment: 'jsdom',
    moduleDirectories: ['node_modules'],
    testMatch: [
        '**/static/js/**/*.test.js',
        '**/tests/**/*.test.js',
        '!**/__tests__/**/*.test.js'  // Exclude Playwright tests
    ],
    setupFilesAfterEnv: ['./jest.setup.js'],
    transform: {
        '^.+\\.js$': 'babel-jest'
    }
};

# Testing Guide for BookChat

This guide outlines the testing requirements and best practices when adding new features to BookChat.

## Testing Layers

### 1. Unit Tests (`/tests/*.py`)
Unit tests should verify the behavior of individual components in isolation. For each new feature, include tests for:

- **Input Validation**
  - Valid inputs within expected ranges
  - Edge cases at boundaries
  - Invalid inputs
  - Empty or null values
  - Malformed data

- **Business Logic**
  - Core functionality works as expected
  - All branches of conditional logic
  - Error handling and exceptions
  - State changes
  - Return values

- **Integration Points**
  - Interface contracts are maintained
  - Dependencies are properly mocked
  - Async operations complete correctly

### 2. End-to-End Tests (`/__tests__/*.js`)
E2E tests should verify the complete user journey. For each feature, include tests for:

- **UI Components**
  - Elements are rendered correctly
  - Interactive elements respond to user actions
  - Visual feedback (loading states, error states)
  - Accessibility concerns

- **Data Flow**
  - Client-server communication
  - Data persistence
  - State updates reflect in UI
  - Real-time updates (if applicable)

- **Error Handling**
  - User-facing error messages
  - Recovery from error states
  - Network failure scenarios
  - Rate limiting behavior

### 3. Integration Tests (`/tests/test_server_integration.py`)
Integration tests should verify component interactions. Include tests for:

- **API Endpoints**
  - Request/response formats
  - Status codes
  - Headers and authentication
  - Rate limiting
  - Payload validation

- **Storage Layer**
  - Data persistence
  - Data retrieval
  - Concurrent operations
  - Transaction handling

## Test Structure Best Practices

1. **Arrange-Act-Assert Pattern**
   ```python
   def test_feature():
       # Arrange: Set up test data and conditions
       test_data = setup_test_data()
       
       # Act: Perform the action being tested
       result = perform_action(test_data)
       
       # Assert: Verify the results
       assert result.status == expected_status
   ```

2. **Test Isolation**
   - Each test should be independent
   - Clean up test data after each test
   - Don't rely on test execution order
   - Use fixtures for common setup

3. **Naming Conventions**
   ```python
   def test_when_[condition]_then_[expected_result]():
       # Example: test_when_message_too_long_then_raises_error()
   ```

## Example Test Cases

Here's an example of comprehensive test coverage for a message length validation feature:

```python
# Unit Tests
async def test_message_length_validation():
    # Test exact limit
    assert await create_message("a" * 2000) is not None
    
    # Test exceeding limit
    with pytest.raises(ValueError):
        await create_message("a" * 2001)
    
    # Test well under limit
    assert await create_message("Hello") is not None

# E2E Tests
test('validates message length in UI', async () => {
    // Test counter display
    await type_message("Hello");
    expect(counter).toShow("1995 characters remaining");
    
    // Test limit enforcement
    await type_message("a".repeat(2001));
    expect(alert).toContain("cannot exceed 2000 characters");
});
```

## Testing Tools

1. **Python Testing**
   - pytest for unit and integration tests
   - pytest-asyncio for async tests
   - pytest-cov for coverage reports

2. **JavaScript Testing**
   - Jest for test running and assertions
   - Playwright for browser automation
   - Mock Service Worker for API mocking

## When to Add Tests

Add tests when:
1. Creating a new feature
2. Fixing a bug (add regression test)
3. Refactoring existing code
4. Adding new API endpoints
5. Modifying UI components

## Running Tests

```bash
# Run Python tests
pytest tests/ -v

# Run specific test file
pytest tests/test_message_handler.py -v

# Run E2E tests
npm test

# Run specific E2E test file
npm test __tests__/e2e.test.js
```

## Coverage Requirements

- Aim for minimum 80% code coverage
- 100% coverage for critical paths
- All error conditions must be tested
- All UI states must have corresponding tests

Remember: Tests are not just for catching bugs, but also serve as documentation and examples for other developers.

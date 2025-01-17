# BookChat Testing Checklist

Last updated: 2025-01-17T11:54:39-05:00

## Message Display & Sending
### Basic Message Functionality
- [ ] Messages can be sent using the input form
- [ ] Messages appear in the chat window immediately after sending
- [ ] Long messages display correctly without breaking the layout
- [ ] Empty messages cannot be sent (form validation)
- [ ] Messages respect the 2000 character limit

### Message Timestamps
- [ ] Each message shows a timestamp
- [ ] Timestamps are displayed in a consistent format
- [ ] Timestamps accurately reflect the message creation time
- [ ] Timestamps are correctly ordered

### Message Ordering
- [ ] Messages are displayed in chronological order (oldest to newest)
- [ ] New messages appear at the bottom of the chat
- [ ] Message order is preserved after page refresh
- [ ] No duplicate messages appear

### UI/UX Elements
- [ ] Character counter updates correctly (0/2000)
- [ ] Send button is enabled/disabled appropriately
- [ ] Chat window scrolls to bottom on new messages
- [ ] Shift+Enter creates new lines in the input

### Username Features
- [ ] Username is displayed with each message
- [ ] Username changes are reflected in new messages
- [ ] Username persists across page refreshes
- [ ] Username validation works (3-20 chars, alphanumeric + underscore)

### Message Loading
- [ ] Previous messages load when opening the chat
- [ ] Messages load in a reasonable time
- [ ] Error states are handled gracefully
- [ ] Loading states are shown when appropriate

### Technical Verification
- [ ] Messages are properly stored and retrieved from the server
- [ ] Message verification status is correctly displayed
- [ ] No console errors during normal operation
- [ ] Websocket/polling connection remains stable

## Notes
- Add any testing notes or issues found here
- Document any edge cases discovered during testing
- Track any bugs that need to be addressed

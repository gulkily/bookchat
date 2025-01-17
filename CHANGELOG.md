# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Flexible message file format with headers anywhere in file
- Support for Git-based storage with version control
- Basic chat functionality with real-time updates

### Changed
- Standardized on 'author' field throughout codebase
- Simplified storage layer to use direct initialization
- Improved message validation and error handling

### Removed
- Removed archive manager functionality
- Removed storage factory pattern
- Simplified project structure

## [0.1.0] - 2025-01-17

### Added
- Initial release
- Basic messaging functionality
- File-based storage
- Simple web interface

## [1.0.0] - 2025-01-14
### Added
- Advanced multi-backend storage system with Git support
- Comprehensive logging system with multiple log levels and separate log files
- Git integration with fork management capabilities
- Message verification system with environment variable configuration
- Key management system for enhanced security
- Template rendering using Jinja2
- Automatic port finding and browser opening capabilities
- Archive management system for message history

### Changed
- Enhanced logging format with detailed debugging information
- Improved error handling and reporting
- Updated Git synchronization mechanism

### Security
- Implemented message verification system
- Added secure key management
- Environment-based configuration system

## [0.9.0] - 2025-01-13
### Added
- Initial implementation of git_manager.py with core functionality
- Basic server implementation with HTTP request handling
- Storage factory pattern for flexible backend support
- Basic testing infrastructure

### Changed
- Refactored storage system to support multiple backends
- Updated server configuration handling

### Fixed
- Various bug fixes in Git synchronization
- Improved error handling in storage systems

## [0.8.0] - 2025-01-09
### Added
- Initial project setup
- Basic package structure
- Core server functionality
- Initial storage system implementation

[Unreleased]: https://github.com/yourusername/bookchat/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/yourusername/bookchat/compare/v0.9.0...v1.0.0
[0.9.0]: https://github.com/yourusername/bookchat/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/yourusername/bookchat/releases/tag/v0.8.0
[0.1.0]: https://github.com/yourusername/bookchat/releases/tag/v0.1.0

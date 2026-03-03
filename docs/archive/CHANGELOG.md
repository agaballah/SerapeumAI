# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-12-04

### 🚀 New Features
- **Project Management**: Create, load, and manage multiple projects.
- **Document Ingestion**: Support for PDF, Images, DXF, and Office files.
- **Vision Processing**: Integrated Qwen2-VL for analyzing technical drawings.
- **Compliance Engine**: Automated checking against SBC, IBC, and NFPA standards.
- **Chat Interface**: Context-aware chat with citation support.
- **Graph View**: Visual exploration of document relationships.

### 🐛 Bug Fixes
- Fixed critical issue where PDF text extraction returned empty results on Windows.
- Fixed Vision Worker not auto-triggering after ingestion.
- Fixed crashes in Chat Panel when LLM service is unavailable.
- Fixed empty Standards Database by adding a seeding script.
- Fixed various UI responsiveness issues.

### 🛡️ Security
- Removed all GPL-licensed dependencies to ensure commercial compliance.
- Added input validation to all file operations.
- Implemented local-only processing to ensure data privacy.

### 📚 Documentation
- Added comprehensive User Manual.
- Added Troubleshooting Guide and FAQ.
- Added System Requirements documentation.

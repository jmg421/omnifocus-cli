# Changelog

All notable changes to the OmniFocus CLI project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-XX - Production Release

### 🎉 Major Features

#### Core CLI Framework
- **Complete package restructuring** for standalone distribution
- **Self-contained dependencies** - no external file dependencies
- **Production-ready packaging** with comprehensive setup.py and pyproject.toml
- **Professional documentation** with comprehensive README and API reference

#### OmniFocus Integration
- **Authoritative AppleScript integration** with real-time data sync
- **Fresh export guarantee** - always work with up-to-date OmniFocus data
- **Schema validation** using Pydantic models for data integrity
- **Unified AppleScript runner** with experimental v2 path for enhanced reliability

#### AI-Powered Features
- **OpenAI GPT-4 integration** for intelligent task prioritization
- **Anthropic Claude integration** for advanced decision-making
- **Smart inbox cleanup** with AI-driven project suggestions
- **Context-aware task delegation** with auto-generated emails
- **Natural language processing** for complex task descriptions

#### Apple Ecosystem Integration
- **EventKit calendar integration** - native macOS calendar access without timeouts
- **icalBuddy support** for advanced calendar querying and conflict detection
- **AppleScript calendar bridge** for seamless Apple Calendar integration
- **iMessage integration** for extracting action items from conversations

#### Advanced Workflow Features
- **SQLite integration** for local database with advanced querying
- **Batch operations** for efficient multi-task management
- **Smart scheduling** with calendar-aware conflict detection
- **Evernote sync** for bidirectional task-note synchronization (legacy)
- **Comprehensive error handling** with graceful failure modes

### 🔧 Technical Improvements

#### Package Structure
- **Modular architecture** with clear separation of concerns
- **Proper relative imports** throughout the codebase
- **Comprehensive test suite** with unit and integration tests
- **Type hints** and mypy compliance for better code quality
- **Professional packaging** with setuptools and modern pyproject.toml

#### Dependencies Management
- **Consolidated requirements.txt** with all necessary dependencies
- **Apple-specific dependencies** (pyobjc-framework-EventKit, appscript)
- **AI service libraries** (openai, anthropic) with proper version constraints
- **Development dependencies** separate from production requirements

#### Documentation & Quality
- **Comprehensive README** with badges, examples, and architecture overview
- **API documentation** with detailed command reference
- **Contributing guidelines** and development setup instructions
- **MIT license** for open-source distribution
- **Changelog** following Keep a Changelog format

### 📊 Command Reference

#### Core Commands
- `ofcli add` - Create new tasks or projects with AI-enhanced parsing
- `ofcli list` - Display tasks and projects with rich formatting
- `ofcli complete` - Mark tasks as completed with batch support
- `ofcli search` - Search across all data with fuzzy matching
- `ofcli delete` - Remove tasks or projects with safety checks

#### AI Commands
- `ofcli prioritize` - AI-powered task prioritization with context awareness
- `ofcli cleanup` - Intelligent inbox organization with confidence scoring
- `ofcli audit` - Task categorization and cleanup suggestions
- `ofcli delegate` - AI-assisted task delegation with email generation

#### Calendar Commands
- `ofcli calendar-conflicts` - Check for scheduling conflicts using EventKit
- `ofcli calendar-verify` - Test calendar integration and permissions
- `ofcli add-calendar-event` - Create new calendar events with OmniFocus sync

#### Utility Commands
- `ofcli diagnostics` - Comprehensive system health check
- `ofcli archive-completed` - Archive old completed tasks with date filtering
- `ofcli scan-messages` - Extract action items from iMessage conversations
- `ofcli next` - Get next actions report with context

### 🛠 Breaking Changes

#### Import Structure
- **BREAKING**: All imports now use relative paths within the package
- **BREAKING**: External `ofcli_utils.py` merged into `utils.config`
- **BREAKING**: Package structure follows standard Python conventions

#### Dependencies
- **BREAKING**: Removed AWS-specific dependencies (boto3, matplotlib)
- **BREAKING**: Removed MonarchMoney integration (custom package)
- **BREAKING**: Evernote integration marked as legacy (still functional)

#### File Paths
- **BREAKING**: No more hardcoded relative paths to parent directories
- **BREAKING**: Data directory is now within the package structure
- **BREAKING**: Export cache location standardized

### 🔒 Security Improvements
- **Environment file separation** with `.ofcli.env` for user configuration
- **API key validation** with helpful error messages
- **Cryptography support** for sensitive data handling
- **Secure AppleScript execution** with input validation

### 🧪 Testing & Quality Assurance
- **Comprehensive test suite** covering CLI, imports, and core functionality
- **Import validation tests** ensuring all refactored imports work correctly
- **Mocked external dependencies** for reliable testing
- **pytest configuration** with coverage reporting
- **Code quality tools** (black, flake8, mypy) with configuration

### 📦 Distribution Ready
- **PyPI-ready packaging** with proper metadata and classifiers
- **Entry point configuration** for `ofcli` command installation
- **Development extras** for optional development dependencies
- **Documentation extras** for enhanced documentation building
- **Professional versioning** following semantic versioning

### 🎯 Performance Optimizations
- **Reduced startup time** through optimized imports
- **Cached export validation** to avoid redundant operations
- **Efficient data structures** using pandas and numpy
- **Memory optimization** for large task lists

### 🐛 Bug Fixes
- **Fixed import errors** from package restructuring
- **Resolved circular dependencies** in module imports
- **Corrected path references** that pointed outside the package
- **Fixed calendar timeout issues** with EventKit integration
- **Improved error handling** for missing dependencies

### 📚 Documentation
- **Professional README** with comprehensive feature overview
- **Installation guide** with multiple installation options
- **Quick start guide** with practical examples
- **Command reference** with detailed parameter descriptions
- **Architecture documentation** explaining design principles
- **Contributing guide** for developers
- **License and acknowledgments** for open-source compliance

---

## Future Releases

### Planned for v1.1.0
- Enhanced AI model support (GPT-4 Turbo, Claude 3)
- Additional calendar integrations (Google Calendar, Outlook)
- Plugin system for custom automations
- Web interface for remote access
- Enhanced reporting and analytics

### Planned for v1.2.0
- Team collaboration features
- Cloud sync capabilities
- Mobile companion app integration
- Advanced workflow automation
- Enterprise features and SSO support

---

**Note**: This changelog follows the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format and [Semantic Versioning](https://semver.org/spec/v2.0.0.html) principles. 
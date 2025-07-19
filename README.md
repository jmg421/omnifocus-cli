# OFCLI - OmniFocus Command Line Interface

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/jmg421/omnifocus-cli)
[![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://github.com/jmg421/omnifocus-cli)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://github.com/jmg421/omnifocus-cli)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/jmg421/omnifocus-cli/blob/main/LICENSE)

A powerful, AI-enhanced command-line interface for OmniFocus with comprehensive Apple ecosystem integration. Transform your productivity workflow with intelligent task management, calendar integration, and seamless automation.

**Built by the founder of [nodes.bio](https://nodes.bio) and shared with the OmniFocus community.**

## 🚀 Key Features

### Core Task Management
- **Authoritative AppleScript Integration**: Direct, real-time communication with OmniFocus
- **AI-Powered Task Prioritization**: Leverage OpenAI GPT-4 and Anthropic Claude for intelligent task ordering
- **Intelligent Task Categorization**: Automated inbox cleanup with AI-driven project suggestions
- **Batch Operations**: Efficiently manage multiple tasks and projects simultaneously

### Apple Ecosystem Integration
- **EventKit Calendar Integration**: Native macOS calendar access without AppleScript timeouts
- **icalBuddy Support**: Advanced calendar querying and conflict detection
- **AppleScript Calendar Bridge**: Seamless integration with Apple Calendar events
- **Messages Integration**: Extract action items from iMessage conversations

### Advanced Workflow Features
- **Fresh Export Guarantee**: Always work with up-to-date OmniFocus data via automatic JSON exports
- **Schema Validation**: Pydantic-based data validation ensures data integrity
- **SQLite Integration**: Local database for advanced querying and reporting
- **Evernote Sync**: Bidirectional task-note synchronization for context switching

### AI-Enhanced Capabilities
- **Natural Language Processing**: Parse and understand complex task descriptions
- **Context-Aware Delegation**: AI-generated delegation emails and task assignments
- **Smart Scheduling**: Calendar-aware task scheduling with conflict detection
- **Intelligent Cleanup**: Automated inbox organization with confidence scoring

## 📋 Requirements

- **macOS 10.15+** (OmniFocus requirement)
- **Python 3.9+**
- **OmniFocus 3 for Mac**
- **API Keys**: OpenAI and/or Anthropic for AI features

## 🛠 Installation

### Quick Install (Recommended)
```bash
pip install ofcli
```

### From Source
```bash
git clone https://github.com/jmg421/omnifocus-cli.git
cd omnifocus-cli
pip install -e .
```

### Development Installation
```bash
git clone https://github.com/jmg421/omnifocus-cli.git
cd omnifocus-cli
pip install -e ".[dev]"
```

## ⚙️ Configuration

### 1. API Keys Setup
Create a `.ofcli.env` file in your home directory:

```bash
# AI Services (at least one required)
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# Optional: Export behavior
OF_EXPORT_MAX_AGE=1800  # Maximum age of exports in seconds
```

### 2. Initial Setup
```bash
# Verify installation
ofcli --help

# Test OmniFocus connection
ofcli diagnostics

# Perform initial data sync
ofcli list-live-projects
```

## 🎯 Quick Start Guide

### Basic Task Management
```bash
# Add a new task
ofcli add --title "Review quarterly reports" --project "Work" --due "next Friday"

# List tasks in a project
ofcli list --project "Work" --json

# Complete a task
ofcli complete TASK_ID

# Search across all tasks
ofcli search "quarterly"
```

### AI-Enhanced Operations
```bash
# AI-powered task prioritization
ofcli prioritize --project "Work" --limit 10

# Intelligent inbox cleanup
ofcli cleanup

# Smart task auditing
ofcli audit --project "Personal"
```

### Calendar Integration
```bash
# Check calendar conflicts
ofcli calendar-conflicts --date "2024-01-15"

# Add calendar event
ofcli add-calendar-event --title "Team Meeting" --start "2024-01-15 14:00"

# Verify calendar integration
ofcli calendar-verify
```

### Advanced Workflows
```bash
# Archive completed tasks
ofcli archive-completed --before "2024-01-01"

# Delegate tasks with AI-generated emails
ofcli delegate TASK_ID --to "colleague@company.com"

# Extract action items from messages
ofcli scan-messages --days 7
```

## 📊 Command Reference

### Core Commands
| Command | Description |
|---------|-------------|
| `add` | Create new tasks or projects |
| `list` | Display tasks and projects |
| `complete` | Mark tasks as completed |
| `search` | Search across all data |
| `delete` | Remove tasks or projects |

### AI Commands
| Command | Description |
|---------|-------------|
| `prioritize` | AI-powered task prioritization |
| `cleanup` | Intelligent inbox organization |
| `audit` | Task categorization and cleanup suggestions |
| `delegate` | AI-assisted task delegation |

### Calendar Commands
| Command | Description |
|---------|-------------|
| `calendar-conflicts` | Check for scheduling conflicts |
| `calendar-verify` | Test calendar integration |
| `add-calendar-event` | Create new calendar events |

### Utility Commands
| Command | Description |
|---------|-------------|
| `diagnostics` | System health check |
| `archive-completed` | Archive old completed tasks |
| `scan-messages` | Extract action items from iMessage |
| `next` | Get next actions report |

## 🏗 Architecture

OFCLI follows a modular architecture designed for reliability and extensibility:

```
ofcli/
├── commands/           # CLI command implementations
├── omnifocus_api/      # OmniFocus integration layer
├── ai_integration/     # AI service integrations
├── utils/              # Shared utilities and helpers
├── plugins/            # OmniFocus automation plugins
└── tests/             # Comprehensive test suite
```

### Key Design Principles
- **Single Source of Truth**: Always sync with authoritative OmniFocus data
- **Fail-Safe Operations**: Comprehensive error handling and data validation
- **Apple-First**: Native integration with Apple ecosystem technologies
- **AI-Enhanced**: Intelligent automation without replacing human judgment

## 🔧 Advanced Configuration

### Custom Export Behavior
```bash
# Force fresh export on every command
export OF_RUNNER_V2=1

# Use alternative export location
export OF_EXPORT_PATH="/custom/path"
```

### Calendar Integration Setup
```bash
# Test EventKit permissions
ofcli calendar-verify

# Configure calendar preferences
ofcli config set-calendar "Work Calendar"
```

### Plugin Development
OFCLI supports custom OmniFocus plugins written in OmniJS:

```javascript
// plugins/custom_automation.omnijs
(() => {
    const action = new PlugIn.Action("Custom Action", (selection) => {
        // Your automation logic here
    });
    return action;
})();
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_commands.py
pytest tests/test_ai_integration.py

# Run with coverage
pytest --cov=ofcli
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
```bash
git clone https://github.com/jmg421/omnifocus-cli.git
cd omnifocus-cli
pip install -e ".[dev]"
pre-commit install
```

## 💭 The Story Behind OFCLI

As the founder of [nodes.bio](https://nodes.bio), I wear every hat in the company - CEO, CTO, CFO, you name it. Context switching between strategic thinking and operational execution was killing my productivity.

I'd been living in OmniFocus for years, but I needed something more. I needed AI to help me prioritize the chaos, calendar integration to reality-check my time, and automation to reduce the cognitive load of task management.

So I built OFCLI for myself. It became the backbone of how I run my startup - combining OmniFocus as my trusted system with AI intelligence and Apple ecosystem integration.

**This tool literally runs my life and my company.** I'm sharing it because the OmniFocus community gave me the foundation for effective time management, and this is my way of giving back.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/jmg421/omnifocus-cli/issues)
- **Documentation**: [Full Documentation](https://github.com/jmg421/omnifocus-cli#readme)
- **Discussions**: [GitHub Discussions](https://github.com/jmg421/omnifocus-cli/discussions)

## 🎉 Acknowledgments

- OmniFocus team for creating an incredible productivity application
- Apple for the robust AppleScript and EventKit frameworks
- OpenAI and Anthropic for advancing AI accessibility
- The Python community for excellent tooling and libraries

---

**Built with ❤️ by a solo founder who lives and breathes OmniFocus**

# OFCLI - OmniFocus Command Line Interface

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/jmg421/omnifocus-cli)
[![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://github.com/jmg421/omnifocus-cli)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://github.com/jmg421/omnifocus-cli)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/jmg421/omnifocus-cli/blob/main/LICENSE)

A powerful command-line interface for OmniFocus that respects your trusted system while adding automation and Apple ecosystem integration. Built by a solo founder who lives in OmniFocus daily.

**Built by a solo founder and shared with the OmniFocus community.**

## 🎯 The Killer Feature: Single Source of Truth

**OFCLI never changes your OmniFocus data without your explicit command.** It pulls fresh exports, processes them, and presents information - but OmniFocus remains your authoritative system. No sync conflicts, no data corruption, no surprises.

This is the CLI that respects your trusted system.

## 🚀 Core Features (Battle-Tested)

### ✅ **Authoritative OmniFocus Integration**
- **Fresh Export Guarantee**: Always pulls latest data from OmniFocus via AppleScript
- **Real-time Communication**: Direct AppleScript integration for commands
- **Schema Validation**: Pydantic models ensure data integrity
- **No Data Conflicts**: OmniFocus remains your single source of truth

### ✅ **Apple Ecosystem Integration** 
- **AppleScript Calendar Bridge**: Seamless integration with Apple Calendar events
- **EventKit Calendar Access**: Native macOS calendar integration without timeouts
- **Native macOS Integration**: Built specifically for the Apple ecosystem

### ✅ **Productivity Features**
- **Batch Operations**: Efficiently manage multiple tasks and projects
- **Advanced Search**: Fast, flexible search across all your data
- **Local SQLite Cache**: Enhanced querying while respecting OmniFocus as source
- **Rich CLI Output**: Beautiful, readable formatting for terminal workflows

### 🧪 **Experimental Features** (Use with Caution)
- **AI Task Analysis**: Early-stage OpenAI/Anthropic integration for task insights
- **Calendar Conflict Detection**: Experimental scheduling awareness
- **Inbox Cleanup Suggestions**: AI-powered project categorization (early beta)

## 📋 Requirements

- **macOS 10.15+** (OmniFocus requirement)
- **Python 3.9+**
- **OmniFocus 3 for Mac**
- **API Keys**: OpenAI and/or Anthropic (optional, for experimental AI features)

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

### 1. Basic Setup (Required)
```bash
# Verify installation
ofcli --help

# Test OmniFocus connection
ofcli diagnostics

# List your projects (core functionality)
ofcli list-live-projects
```

### 2. AI Features Setup (Optional)
Create a `.ofcli.env` file in your home directory for experimental AI features:

```bash
# AI Services (optional - only needed for experimental features)
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

## 🎯 Quick Start Guide

### Core Task Management (Reliable)
```bash
# Add a new task
ofcli add --title "Review quarterly reports" --project "Work" --due "next Friday"

# List tasks in a project
ofcli list --project "Work" --json

# Complete a task
ofcli complete TASK_ID

# Search across all tasks
ofcli search "quarterly"

# Archive completed tasks
ofcli archive-completed --before "2024-01-01"
```

### System Health & Diagnostics
```bash
# Check everything is working
ofcli diagnostics

# Verify OmniFocus connection
ofcli list-live-projects

# Get system status
ofcli next
```

### Experimental AI Features (Beta)
```bash
# AI task analysis (requires API keys)
ofcli prioritize --project "Work" --limit 10

# Inbox cleanup suggestions
ofcli cleanup

# Task categorization audit
ofcli audit --project "Personal"
```

## 📊 Command Reference

### Core Commands (Stable)
| Command | Description | Status |
|---------|-------------|--------|
| `add` | Create new tasks or projects | ✅ Stable |
| `list` | Display tasks and projects | ✅ Stable |
| `complete` | Mark tasks as completed | ✅ Stable |
| `search` | Search across all data | ✅ Stable |
| `delete` | Remove tasks or projects | ✅ Stable |
| `archive-completed` | Archive old completed tasks | ✅ Stable |

### Experimental Commands (Beta)
| Command | Description | Status |
|---------|-------------|--------|
| `prioritize` | AI-powered task analysis | 🧪 Experimental |
| `cleanup` | Inbox organization suggestions | 🧪 Experimental |
| `audit` | Task categorization analysis | 🧪 Experimental |

### System Commands
| Command | Description | Status |
|---------|-------------|--------|
| `diagnostics` | System health check | ✅ Stable |
| `next` | Get next actions report | ✅ Stable |

## 🏗 Architecture

OFCLI follows a clear principle: **OmniFocus is the source of truth.**

```
ofcli/
├── commands/           # CLI command implementations
├── omnifocus_api/      # OmniFocus AppleScript integration
├── ai_integration/     # Experimental AI features (optional)
├── utils/              # Data loading and validation
└── tests/             # Comprehensive test suite
```

### Design Principles
1. **OmniFocus as Single Source of Truth**: Never compete with your trusted system
2. **Apple Ecosystem First**: Built for macOS, AppleScript, and Apple Calendar
3. **Fail-Safe Operations**: Comprehensive error handling and validation
4. **Experimental vs Stable**: Clear distinction between reliable and beta features

## 🔧 Advanced Configuration

### OmniFocus Export Behavior
```bash
# Force fresh export on every command
export OF_RUNNER_V2=1

# Control export freshness (seconds)
export OF_EXPORT_MAX_AGE=1800
```

### Calendar Integration
```bash
# Test calendar integration
ofcli calendar-verify

# Check for scheduling conflicts
ofcli calendar-conflicts --date "2024-01-15"
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_commands.py
pytest tests/test_imports.py

# Run with coverage
pytest --cov=ofcli
```

## 🤝 Contributing

We welcome contributions! Focus areas:

1. **Core OmniFocus Integration**: Improving AppleScript reliability
2. **Apple Ecosystem Features**: Calendar, Shortcuts, etc.
3. **Test Coverage**: Ensuring reliability
4. **Documentation**: Usage examples and guides

### Development Setup
```bash
git clone https://github.com/jmg421/omnifocus-cli.git
cd omnifocus-cli
pip install -e ".[dev]"
pre-commit install
```

## 💭 The Story Behind OFCLI

As a solo founder, I wear every hat in the company - CEO, CTO, CFO, you name it. Context switching between strategic thinking and operational execution was killing my productivity.

I'd been living in OmniFocus for years, but I needed something more. I needed better ways to process my inbox, calendar integration to reality-check my time, and automation to reduce the cognitive load.

So I built OFCLI for myself. It became the backbone of how I run my startup - combining OmniFocus as my trusted system with command-line efficiency and Apple ecosystem integration.

**This tool literally runs my life and my company.** I'm sharing it because the OmniFocus and Getting Things Done (GTD) community gave me the foundation for effective time management, and this is my way of giving back.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/jmg421/omnifocus-cli/issues)
- **Documentation**: [Full Documentation](https://github.com/jmg421/omnifocus-cli#readme)
- **Discussions**: [GitHub Discussions](https://github.com/jmg421/omnifocus-cli/discussions)

## 🎉 Acknowledgments

- OmniFocus team for creating an incredible productivity application
- David Allen for Getting Things Done methodology
- Apple for the robust AppleScript and EventKit frameworks
- The OmniFocus community for sharing workflows and wisdom

---

**Built with ❤️ by a solo founder who lives and breathes OmniFocus**

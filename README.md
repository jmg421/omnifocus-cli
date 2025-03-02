# OFCLI - OmniFocus Command Line Interface

A powerful command-line interface for OmniFocus with AI integration.

## Features

- Add tasks and projects
- List and filter tasks
- Complete tasks
- AI-powered task prioritization
- Delegate tasks with ease

## Requirements

- Python 3.9+
- OmniFocus for Mac
- API keys for OpenAI or Anthropic (for AI features)

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/omni-cli.git
cd omni-cli

# Install the package
pip install -e .
```

### Configuration

Create a `.env` file in your home directory with your API keys:

```
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

## Usage

### Adding Tasks

```bash
ofcli add --title "Complete project proposal" --project "Work" --due "tomorrow at 5pm"
```

### Listing Tasks

```bash
# List all tasks
ofcli list

# List tasks in a specific project
ofcli list --project "Work"

# Output in JSON format
ofcli list --json
```

### Completing Tasks

```bash
ofcli complete task_id_1 task_id_2
```

### AI Prioritization

```bash
# Prioritize all tasks
ofcli prioritize

# Prioritize tasks in a specific project
ofcli prioritize --project "Work"

# Limit the number of tasks to prioritize
ofcli prioritize --limit 5
```

### Delegating Tasks

```bash
ofcli delegate task_id --to "colleague@example.com"
```

## Advanced Usage

For more advanced usage options, please refer to the documentation in the `docs/` directory.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

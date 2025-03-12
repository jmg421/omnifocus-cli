# OFCLI - OmniFocus Command Line Interface

A powerful command-line interface for OmniFocus with AI integration and bidirectional Evernote sync for seamless context switching.

## Features

- Add tasks and projects
- List and filter tasks
- Complete tasks
- AI-powered task prioritization
- Delegate tasks with ease
- Full Evernote integration:
  - Sync tasks with related notes
  - Switch contexts seamlessly
  - Link actions to reference material
  - Create tasks from notes
  - Attach notes to tasks
  - Smart context detection
  - Automatic task-note linking

## Requirements

- Python 3.9+
- OmniFocus for Mac
- API keys for OpenAI or Anthropic (for AI features)
- Evernote account

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

## Evernote Integration

The Evernote integration enables seamless context switching between tasks and their related reference materials. It helps you maintain focus by ensuring all relevant information is linked and accessible.

1. Register your application at [Evernote Developers](https://dev.evernote.com/):
   - Create a new API key
   - Set OAuth callback URL to `http://localhost:8080`
   - Copy your Client ID and Client Secret

2. Update `.env` with your Evernote credentials:
```bash
EVERNOTE_CLIENT_ID=your_client_id
EVERNOTE_CLIENT_SECRET=your_client_secret
EVERNOTE_SANDBOX=true  # Set to false for production
```

3. First-time authentication:
   - Run any Evernote-related command
   - Browser will open for authorization
   - Grant access to your Evernote account
   - Authorization completes automatically

## Usage

### Task-Note Integration

```bash
# Link a note to a task
ofcli link task_id --note note_id

# Create a new task from a note
ofcli create-task --from-note note_id

# View task with its linked notes
ofcli view task_id --with-context

# Switch to a task's context
ofcli switch-context task_id

# Find tasks related to a note
ofcli find-tasks --note note_id

# Find notes related to a task
ofcli find-notes --task task_id

# Create a new note for task context
ofcli create-note task_id
```

### Context Management

```bash
# Show current context
ofcli context

# List available contexts
ofcli contexts

# Switch to a specific context
ofcli switch-context context_id

# Auto-suggest next context based on time/location
ofcli suggest-context
```

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

### Test Evernote Connection

```bash
ofcli test-evernote
```

### Export Task to Evernote

```bash
ofcli export-task [TASK_ID] --to evernote
```

## Advanced Usage

For more advanced usage options, please refer to the documentation in the `docs/` directory.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

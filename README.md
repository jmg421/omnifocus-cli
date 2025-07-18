# OFCLI - OmniFocus Command Line Interface

A powerful command-line interface for OmniFocus with AI integration and bidirectional Evernote sync for seamless context switching.

## Key Features (v0.2)

* **Authoritative AppleScript export** – every CLI operation pulls a fresh JSON export from OmniFocus (via `ensure_fresh_export`) so you’re always working with up-to-date data.
* **Schema-validated importer** – exports are validated with Pydantic models before processing; malformed data is rejected with clear error messages.
* **SQLite ingest with change report** – `scripts/ingest_export.py` upserts projects/tasks and prints a summary of new / updated / possible-duplicate items.
* Rich CLI:
  * Add, list, complete, and delegate tasks & projects.
  * AI-powered task prioritization.
* **Evernote integration** (optional, legacy) – link tasks ⇄ notes for contextual reference.

> ⚠️  CSV and Markdown importers are considered **legacy utilities**. They remain available behind the `--input-format csv` flag but are not the primary sync path.

## Requirements

- Python 3.9+
- OmniFocus for Mac
- API keys for OpenAI or Anthropic (for AI features)
- Evernote account

## Unified AppleScript Runner (experimental)

CLI commands that interact with OmniFocus now route through a central helper that decides **how** to run AppleScript:

* **Default**: uses the macOS `osascript` binary directly (unchanged behaviour).
* **Opt-in experimental path**: set an environment variable to enable a unified runner script that writes the AppleScript to a temp file and executes it through `scripts/run_script.py`.  This isolates AppleScript execution, makes logging easier, and will eventually support sandboxed mocking in unit-tests.

Activate the new path per-invocation:

```bash
# any ofcli sub-command – example:
OF_RUNNER_V2=1 python3 omni-cli/ofcli.py list-live-projects --json
```

The helper lives at `omnifocus_api/apple_script_client.execute_omnifocus_applescript`.  If you are writing new scripts or modifying existing ones, call this function instead of spawning `osascript` yourself.  It automatically honours the `OF_RUNNER_V2` flag.

> Note: JavaScript for Automation (.omnijs) scripts are also supported; the runner adds the `-l JavaScript` flag when the file extension is `.omnijs`.

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

## Usage overview

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

### Ingest fresh export into the local database

```bash
python3 scripts/ingest_export.py  # automatically exports, archives, validates, ingests, and prints a change report
```

Example summary:

```
Projects – new: 2, updated: 1
Tasks    – new: 14, updated: 3, potential dup names: 1
  • Possible duplicate task 'Pay rent' (id 7aB…)
```

### Evernote helpers (legacy)

```bash
# Link a note to a task
ofcli link task_id --note note_id

# Export task context to Evernote
ofcli export-task task_id --to evernote
```

## Advanced Usage

For more advanced usage options, please refer to the documentation in the `docs/` directory.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

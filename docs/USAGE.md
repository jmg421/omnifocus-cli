# USAGE.md

### Usage

## Installation

Ensure you have Python 3.8+ installed.

1. Clone the repository:
   > git clone https://github.com/your-username/omnifocus-cli.git  
   > cd omnifocus-cli

2. Install dependencies:
   > pip install -r requirements.txt

## Configuration

Set up your environment variables by creating a `.env` file or exporting them in your shell. The required variables are:
- `OPENAI_API_KEY` — Your OpenAI API key.
- `ANTHROPIC_API_KEY` — Your Anthropic API key.

For example, create a `.env` file with:


## Running the CLI

The CLI is installed as a console script called `ofcli`. Here are some common commands:

- **Add a Task:**
> ofcli add --title "New Task" --project "Work" --note "Details about the task" --due "2025-03-15"

- **List Tasks:**
> ofcli list --project "Work"  
Optionally output in JSON format:
> ofcli list --project "Work" --json

- **Complete a Task:**
> ofcli complete <task_id>

- **Prioritize Tasks using AI:**
> ofcli prioritize --project "Work" --limit 5

- **Delegate a Task:**
> ofcli delegate <task_id> --to "delegate@example.com" --method email

For a full list of commands and options, run:
> ofcli --help

---

# ARCHITECTURE.md

### Architecture

The OmniFocus CLI is organized into the following components:

- **`omnifocus_cli/commands/`**: Contains individual command handlers for adding, listing, completing, prioritizing, and delegating tasks.
- **`omnifocus_cli/omnifocus_api/`**: Manages communication with OmniFocus using AppleScript and Omni Automation (OmniJS). This includes functions for creating, fetching, and updating tasks.
- **`omnifocus_cli/ai_integration/`**: Integrates with AI services (OpenAI and Anthropic) to provide task prioritization, decision-making, and delegation assistance.
- **`omnifocus_cli/utils/`**: Offers utility functions for configuration, logging, output formatting, and user prompts.
- **`plugins/`**: Contains OmniFocus plugin scripts (JavaScript files) that can be linked into OmniFocus for extended functionality.
- **`tests/`**: Houses unit and integration tests for the CLI.
- **`docs/`**: Contains documentation, including usage guides, architecture overviews, and OmniFocus API references.

---

# OmniFocusAPIReference.md

### OmniFocus API Reference

#### AppleScript Integration

The CLI leverages AppleScript to interact with OmniFocus. Key functionalities include:

- **Creating a Task:**
- Uses commands like `make new task` or `make new inbox task`.
- Sets task properties such as `name`, `note`, and `due date`.

- **Fetching Tasks:**
- Retrieves tasks with properties like `id`, `name`, `note`, `completed`, and `due date`.
- Supports filtering tasks by project.

- **Completing a Task:**
- Marks tasks as complete by setting the `completed` property to `true`.

- **Adding Tags:**
- Finds or creates a tag, then associates it with a specified task.

#### Omni Automation (OmniJS)

For users who prefer OmniJS, the CLI includes an OmniJS client:
- **Executing JavaScript in OmniFocus:**
- Uses AppleScript's `evaluate javascript` command to run Omni Automation scripts.
- The `omnijs_client.py` module demonstrates how to evaluate JS code and handle the results.

#### References

For further details, refer to the official documentation:
- [OmniFocus AppleScript Dictionary](https://support.omnigroup.com/documentation/omnifocus-applescript-dictionary/)
- [OmniFocus Automation Documentation](https://support.omnigroup.com/documentation/omnifocus-automation/)



omnifocus-cli/
├── omnifocus_cli/
│   ├── __init__.py
│   ├── cli_main.py
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── add_command.py
│   │   ├── list_command.py
│   │   ├── complete_command.py
│   │   ├── prioritize_command.py
│   │   └── delegation_command.py
│   ├── omnifocus_api/
│   │   ├── __init__.py
│   │   ├── apple_script_client.py
│   │   ├── omnijs_client.py
│   │   ├── data_models.py
│   │   ├── batch_operations.py
│   │   └── search_filters.py
│   ├── ai_integration/
│   │   ├── __init__.py
│   │   ├── openai_client.py
│   │   ├── anthropic_client.py
│   │   ├── ai_utils.py
│   │   └── prompt_templates/
│   │       └── sample_prompts.md
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── logging_utils.py
│   │   ├── format_utils.py
│   │   └── prompt_utils.py
├── plugins/
│   ├── README.md
│   ├── sample_plugin.omnijs
│   └── advanced_delegation.omnijs
├── tests/
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_commands.py
│   ├── test_omnifocus_api.py
│   └── test_ai_integration.py
├── docs/
│   ├── README.md
│   ├── USAGE.md
│   ├── ARCHITECTURE.md
│   └── OmniFocusAPIReference.md
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
├── pyproject.toml
└── requirements.txt

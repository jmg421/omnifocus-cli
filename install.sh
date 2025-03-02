#!/bin/bash

# OFCLI Installation Script

set -e  # Exit on any error

echo "Installing OFCLI - OmniFocus Command Line Interface..."

# Check for Python 3.9+
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found."
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if (( $(echo "$PY_VERSION < 3.9" | bc -l) )); then
    echo "Error: Python 3.9 or higher is required. Found: $PY_VERSION"
    exit 1
fi

# Check for pip
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is required but not found."
    exit 1
fi

# Create virtual environment (optional)
read -p "Create a virtual environment for ofcli? [y/N] " CREATE_VENV
if [[ $CREATE_VENV =~ ^[Yy]$ ]]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Virtual environment activated."
fi

# Install the package
echo "Installing ofcli..."
pip3 install -e .

# Check if installation was successful
if command -v ofcli &> /dev/null; then
    echo "✅ OFCLI installed successfully!"
    echo "You can now use 'ofcli' from your terminal."
else
    echo "OFCLI was installed but the command 'ofcli' is not in your PATH."
    echo "You can still use the application with: ./ofcli.py"
    echo "You might need to run: export PATH=\$PATH:$HOME/.local/bin"
fi

# Prompt for API keys
echo ""
echo "Do you want to set up your AI API keys now? (Required for AI features)"
read -p "Set up API keys? [y/N] " SETUP_KEYS
if [[ $SETUP_KEYS =~ ^[Yy]$ ]]; then
    ENV_FILE="$HOME/.ofcli.env"
    echo "# OFCLI Environment Variables" > "$ENV_FILE"
    
    read -p "Enter your OpenAI API key (leave blank to skip): " OPENAI_KEY
    if [[ ! -z "$OPENAI_KEY" ]]; then
        echo "OPENAI_API_KEY=$OPENAI_KEY" >> "$ENV_FILE"
    fi
    
    read -p "Enter your Anthropic API key (leave blank to skip): " ANTHROPIC_KEY
    if [[ ! -z "$ANTHROPIC_KEY" ]]; then
        echo "ANTHROPIC_API_KEY=$ANTHROPIC_KEY" >> "$ENV_FILE"
    fi
    
    echo "API keys saved to $ENV_FILE"
    echo "You can edit this file anytime to update your keys."
fi

echo ""
echo "Installation complete! Try running 'ofcli --help' to get started."
echo "If you're using a virtual environment, remember to activate it with 'source venv/bin/activate' before using ofcli." 
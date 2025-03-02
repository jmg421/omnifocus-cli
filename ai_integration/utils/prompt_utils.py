def confirm_action(message: str) -> bool:
    """
    Prompts the user for a yes/no confirmation in the terminal.
    Returns True if user confirms, False otherwise.
    """
    response = input(f"{message} [y/N]: ").strip().lower()
    return response == "y"


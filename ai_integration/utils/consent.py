from .config import get_config, save_config

def check_ai_consent() -> bool:
    """
    Checks if the user has consented to using external AI providers.
    If consent has not been given or denied, it prompts the user interactively.
    Returns True if consent is given, False otherwise.
    """
    cfg = get_config()
    consent_given = cfg.get("ALLOW_EXTERNAL_AI_PROVIDERS")

    if consent_given is True:
        return True
    
    if consent_given is False:
        print("AI features are disabled by user configuration.")
        return False

    # If the key is not in the config, prompt the user
    print("\n--- AI Feature Consent ---")
    print("This feature uses a third-party AI provider (e.g., OpenAI, Anthropic) to generate suggestions.")
    print("To do this, your task data will be sent to the provider's API.")
    print("Your data will not be sent without your explicit permission.")
    
    while True:
        response = input("Do you consent to sending your task data to an external AI provider? (yes/no): ").lower().strip()
        if response in ["yes", "y"]:
            print("Consent given. AI features will be enabled.")
            save_config({"ALLOW_EXTERNAL_AI_PROVIDERS": True})
            return True
        elif response in ["no", "n"]:
            print("Consent denied. AI features will remain disabled.")
            save_config({"ALLOW_EXTERNAL_AI_PROVIDERS": False})
            return False
        else:
            print("Invalid response. Please enter 'yes' or 'no'.") 
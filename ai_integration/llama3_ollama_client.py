import requests
import sys

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

def query_llama3(prompt: str, model: str = MODEL, stream: bool = False) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=60)
    response.raise_for_status()
    # Ollama streams responses by default; if not streaming, get the 'response' field
    if stream:
        # Not implemented: streaming support
        raise NotImplementedError("Streaming not supported in this minimal client.")
    data = response.json()
    return data.get("response", "")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python llama3_ollama_client.py 'your prompt here'")
        sys.exit(1)
    prompt = sys.argv[1]
    print(query_llama3(prompt)) 
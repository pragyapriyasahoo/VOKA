import requests
from voka.config.settings import MODEL_NAME, OLLAMA_URL
from voka.llm.response import clean_response


class OllamaError(RuntimeError):
    """Raised when Ollama cannot produce a valid response."""


def generate_response(prompt: str) -> str:
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        result = response.json()
        text = result.get("response") if isinstance(result, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise OllamaError("Ollama returned an invalid or empty response.")
        return clean_response(text)
    except OllamaError:
        raise
    except requests.exceptions.ConnectionError as error:
        raise OllamaError("Could not connect to Ollama. Make sure Ollama is running.") from error
    except requests.exceptions.Timeout as error:
        raise OllamaError("The Ollama request timed out.") from error
    except requests.exceptions.HTTPError as error:
        raise OllamaError(f"Ollama returned an HTTP error: {error}") from error
    except (requests.exceptions.RequestException, ValueError, TypeError) as error:
        raise OllamaError(f"Ollama request failed: {error}") from error

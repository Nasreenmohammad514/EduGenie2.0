import os
import json
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
_model = None

if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    _model = genai.GenerativeModel("gemini-flash-latest")


def is_configured() -> bool:
    return _model is not None


def ask(prompt: str, system_instruction: str | None = None) -> str:
    """Send a prompt to Gemini and return plain text.

    Falls back to a clear placeholder message if no API key is configured,
    so the rest of the app (DB, RAG, quiz logic) can still be built and
    demoed before you have a key.
    """
    if _model is None:
        return (
            "[Gemini API key not configured] "
            "Add GEMINI_API_KEY to your .env file to get real answers. "
            f"Your prompt was: {prompt[:200]}"
        )

    full_prompt = prompt if not system_instruction else f"{system_instruction}\n\n{prompt}"
    response = _model.generate_content(full_prompt)
    return response.text.strip()


def ask_json(prompt: str, system_instruction: str | None = None) -> dict | list:
    """Ask Gemini for a response and parse it as JSON.

    Used for quiz generation and learning paths, where we need structured
    output rather than free text. Strips markdown code fences if Gemini
    wraps the JSON in them.
    """
    raw = ask(prompt, system_instruction)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Returned as an error payload so the router can decide how to
        # handle a malformed generation instead of crashing.
        return {"error": "Could not parse JSON from model", "raw": raw}

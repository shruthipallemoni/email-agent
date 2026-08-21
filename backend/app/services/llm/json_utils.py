"""
A small shared helper used anywhere we ask an LLM to respond with JSON.
"""


def strip_code_fences(text: str) -> str:
    """
    Some models wrap JSON in ```json ... ``` even when told not to.
    This removes that wrapping so json.loads() doesn't fail.
    """
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()
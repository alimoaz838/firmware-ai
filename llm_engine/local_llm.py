# llm_engine/local_llm.py
import subprocess
import shutil
from textwrap import dedent

def has_ollama():
    """Check if Ollama is installed and available."""
    return shutil.which("ollama") is not None

def ask_local_llm(prompt: str, model: str = "mistral") -> str:
    """
    Calls local Ollama model. If not installed, returns a friendly message.
    """
    if not has_ollama():
        return (
            "[LLM unavailable]\n"
            "Install Ollama from https://ollama.com\n"
            "Then run: ollama pull mistral"
        )

    proc = subprocess.run(
        ["ollama", "run", model],
        input=prompt.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False
    )
    return proc.stdout.decode("utf-8", errors="ignore")

def build_explain_prompt(error_line: str) -> str:
    """
    Build the LLM prompt explaining a single build error line.
    """
    return dedent(f"""
    You are an expert embedded firmware engineer.
    Analyze and explain the following STM32 compiler or linker error.
    Also provide exact fixes.

    ERROR:
    {error_line}

    Format your answer as:
    - Root cause
    - Fix steps
    - Things to double-check (HAL includes, .c files, CubeMX)
    """).strip()
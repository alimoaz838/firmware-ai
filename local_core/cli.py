import sys
from pathlib import Path

# --- FIX IMPORT PATHS ---
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
print("DEBUG: ROOT added to sys.path:", ROOT)

# Try imports with clear errors
try:
    from parsers.build_logs import parse_build_log
    from llm_engine.local_llm import ask_local_llm, build_explain_prompt
    print("DEBUG: Imports OK")
except Exception as e:
    print("❌ IMPORT ERROR:", e)
    sys.exit(1)

def main():
    # pick log file
    if len(sys.argv) > 1:
        log_path = Path(sys.argv[1])
    else:
        log_path = Path("build.log")

    print("DEBUG: Using log file:", log_path.resolve())
    print("DEBUG: Exists? ", log_path.exists())

    if not log_path.exists():
        print("❌ File not found")
        return

    text = log_path.read_text(errors="ignore")
    print("DEBUG: Content length:", len(text))
    print("DEBUG first 200 chars:\n", text[:200])

    findings = parse_build_log(text)
    errors = findings["errors"]
    warnings = findings["warnings"]

    print("\n=== RESULTS ===")
    print("Errors:", len(errors))
    print("Warnings:", len(warnings))

    if errors:
        print("\n--- First 3 Errors Explained by AI ---")
        for err in errors[:3]:
            print("\nERROR:", err)
            print(ask_local_llm(build_explain_prompt(err)))

if __name__ == "__main__":
    main()
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

from parsers.cube_ioc import CubeMXParser
from local_core.peripheral_graph import PeripheralGraph
from local_core.clock_tree import ClockTreeAnalyzer


def main():
    if len(sys.argv) > 1:
        arg = Path(sys.argv[1])
    else:
        arg = Path("build.log")

    # --- Handle .ioc files first ---
    if arg.suffix.lower() == ".ioc":
        if "--graph" in sys.argv:
            graph_ioc_command(arg)
        elif "--clock" in sys.argv:
            clock_ioc_command(arg)
        else:
            parse_ioc_command(arg)
        return

    # --- Otherwise treat as build log ---
    log_path = arg

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


def parse_ioc_command(ioc_path):
    parser = CubeMXParser(ioc_path).load()
    summary = parser.summary()

    print("\n=== CubeMX Project Summary ===")
    print(f"MCU: {summary['mcu']}")

    print("\nPins:")
    for pin, info in summary["pins"].items():
        print(f"  {pin}: {info}")

    print("\nRCC:")
    for key, val in summary["rcc"].items():
        print(f"  {key}: {val}")

    print("\nNVIC:")
    for key, val in summary["nvic"].items():
        print(f"  {key}: {val}")

    print("\nDMA:")
    for key, val in summary["dma"].items():
        print(f"  {key}: {val}")

    print("\nPeripherals:")
    for name, cfg in summary["peripherals"].items():
        print(f"  {name}: {cfg}")


def graph_ioc_command(ioc_path):
    parser = CubeMXParser(ioc_path).load()
    summary = parser.summary()

    graph = PeripheralGraph().build_from_ioc(summary)

    print("\n=== Peripheral Graph Summary ===")
    print("Nodes:")
    for n, attrs in graph.nodes(data=True):
        print(f"  {n} ({attrs})")

    print("\nEdges:")
    for src, dst, attrs in graph.edges(data=True):
        print(f"  {src} -> {dst} [{attrs}]")

def clock_ioc_command(ioc_path):
    parser = CubeMXParser(ioc_path).load()
    summary = parser.summary()

    analyzer = ClockTreeAnalyzer(summary["rcc"])
    clocks = analyzer.compute()

    print("\n=== Clock Tree Summary ===")
    for name, val in clocks.items():
        if val is None:
            print(f"  {name}: unknown")
        else:
            print(f"  {name}: {val/1_000_000:.2f} MHz")


if __name__ == "__main__":
    main()
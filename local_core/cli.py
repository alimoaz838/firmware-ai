import sys
from pathlib import Path
import json

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
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument("file", help="Path to .ioc or build.log")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--graph", action="store_true")
    parser.add_argument("--clock", action="store_true")

    args = parser.parse_args()
    arg = Path(args.file)

    # --- Handle .ioc files ---
    if arg.suffix.lower() == ".ioc":
        ioc = CubeMXParser(arg).load()

        if args.summary:
            ioc.summary()

        if args.json:
            data = ioc.to_json("project.json")
            print("\n=== JSON Output ===")
            print(json.dumps(data, indent=4))

        if args.graph:
            graph = PeripheralGraph().build_from_ioc(ioc.to_dict())
            print("\n=== Peripheral Graph ===")
            print(graph)

        if args.clock:
            analyzer = ClockTreeAnalyzer(ioc.get_rcc())
            clocks = analyzer.compute()
            print("\n=== Clock Tree Summary ===")
            for name, val in clocks.items():
                print(f"  {name}: {val}")

        # Default behavior: summary + JSON
        if not (args.summary or args.json or args.graph or args.clock):
            parse_ioc_command(arg)

        return

    # --- Otherwise treat as build log ---
    log_path = arg
    if not log_path.exists():
        print("❌ File not found")
        return

    text = log_path.read_text(errors="ignore")
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

    # Generate full structured data
    data = parser.to_dict()

    # Print human summary
    parser.summary()

    print("\n=== CubeMX Project Summary ===")
    print(f"MCU: {data['mcu']}")

    print("\nPins:")
    for pin, info in data["pins"].items():
        print(f"  {pin}: {info}")

    print("\nRCC:")
    for key, val in data["rcc"].items():
        print(f"  {key}: {val}")

    print("\nNVIC:")
    for key, val in data["nvic"].items():
        print(f"  {key}: {val}")

    print("\nDMA:")
    for key, val in data["dma"].items():
        print(f"  {key}: {val}")

    print("\nADC:")
    for name, cfg in data["adc"].items():
        print(f"  {name}: {cfg}")

    print("\nUSART:")
    for name, cfg in data["usart"].items():
        print(f"  {name}: {cfg}")

    print("\nTIM:")
    for name, cfg in data["tim"].items():
        print(f"  {name}: {cfg}")

    # Save JSON file
    json_data = parser.to_json("project.json")

    print("\n=== JSON Saved to project.json ===")
    print(json.dumps(json_data, indent=4))


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
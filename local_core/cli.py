import sys
from pathlib import Path
import json

# --- FIX IMPORT PATHS ---
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
print("DEBUG: ROOT added to sys.path:", ROOT)

# Correct imports
from rules_engine.rules_engine import RulesEngine
from local_core.hal_code_analyzer import HalCodeAnalyzer
from local_core.peripheral_graph import PeripheralGraph, export_graphviz

# Try imports with clear errors
try:
    from parsers.build_logs import parse_build_log
    from llm_engine.local_llm import ask_local_llm, build_explain_prompt
    print("DEBUG: Imports OK")
except Exception as e:
    print("❌ IMPORT ERROR:", e)
    sys.exit(1)

from parsers.cube_ioc import CubeMXParser
from local_core.clock_tree import ClockTreeAnalyzer


def main():
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument("file", help="Path to .ioc or build.log")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--graph", action="store_true")
    parser.add_argument("--clock", action="store_true")
    parser.add_argument("--rules", action="store_true")
    parser.add_argument("--export-graph", action="store_true")
    parser.add_argument("--diagnose-usart", type=str)

    args = parser.parse_args()
    arg = Path(args.file)
    # Load HAL once for both rules and diagnosis 
    project_root = ROOT 
    hal = HalCodeAnalyzer(project_root).load().to_dict()
    # --- Handle .ioc files ---
    if arg.suffix.lower() == ".ioc":
        ioc = CubeMXParser(arg).load()
        model = ioc.to_dict()

        # Summary
        if args.summary:
            ioc.summary()

        # JSON
        if args.json:
            data = ioc.to_json("project.json")
            print("\n=== JSON Output ===")
            print(json.dumps(data, indent=4))

        # Graph
        if args.graph or args.rules or args.export_graph or args.diagnose_usart:
            graph = PeripheralGraph().build_from_ioc(model)


        if args.graph:
            print("\n=== Peripheral Graph Summary ===")
            print(f"Nodes: {graph.number_of_nodes()}")
            print(f"Edges: {graph.number_of_edges()}")
            return

        # Export graphviz
        if args.export_graph:
            export_graphviz(graph, "hardware.dot")
            print("\nGraph exported to hardware.dot")
            return

        # Clock tree
        if args.clock:
            analyzer = ClockTreeAnalyzer(model["rcc"])
            analyzer.print_summary(model["usart"])
            return

        # Rules engine
        if args.rules:
            engine = RulesEngine(model, graph, hal)
            warnings = engine.run_all()

            print("\n=== Rules Report ===")
            if not warnings:
                print("  No issues found.")
            else:
                for w in warnings:
                    print(f" [{w['rule']}] {w['message']}") 
                    print(f" → {w['suggestion']}") 
                    if "code" in w: 
                        print(" Suggested code:") 
                        print(w["code"])
            return
        
        if args.diagnose_usart:
            engine = RulesEngine(model, graph, hal)
            warnings = engine.run_all()
            usart_warnings = engine.diagnose_usart(args.diagnose_usart)
            print(f"\n=== Diagnosis for {args.diagnose_usart} ===")
            for w in usart_warnings:
                print(f"[{w['rule']}] {w['message']}")
                print(f" → {w['suggestion']}")
                if "code" in w:
                    print("Suggested code:")
                    print(w["code"])
            return


        # Default behavior: summary + JSON
        if not (args.summary or args.json or args.graph or args.clock or args.rules):
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
    data = parser.to_dict()

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

    json_data = parser.to_json("project.json")

    print("\n=== JSON Saved to project.json ===")
    print(json.dumps(json_data, indent=4))


if __name__ == "__main__":
    main()

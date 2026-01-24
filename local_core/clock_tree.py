from typing import Dict, Any


class ClockTreeAnalyzer:
    """
    Reconstructs a simple clock tree from RCC values in the .ioc model
    and validates USART baud rates where possible.
    """

    def __init__(self, rcc: Dict[str, Any]):
        self.rcc = rcc

    # ---------------------------------------------------------
    # Basic clock reconstruction
    # ---------------------------------------------------------
    def compute(self) -> Dict[str, Any]:
        out = {}

        def as_int(key):
            v = self.rcc.get(key)
            try:
                return int(v) if v is not None else None
            except ValueError:
                return None

        out["HSE"] = as_int("HSE_VALUE")
        out["SYSCLK"] = as_int("SYSCLKFreq_VALUE")
        out["APB1"] = as_int("APB1Freq_Value")
        out["APB2"] = as_int("APB2Freq_Value")
        out["PLLCLK"] = as_int("PLLCLKFreq_Value")

        return out

    # ---------------------------------------------------------
    # USART baud validation (best-effort)
    # ---------------------------------------------------------
    def validate_usart_baud(self, usart_block: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Looks for keys like 'USART2.BaudRate' in the raw usart_block
        and compares against APB bus frequency if available.

        Returns a dict:
          { "USART2": { "baud": 115200, "bus": "APB1", "bus_freq": 42000000, "status": "ok/warn" }, ... }
        """
        results: Dict[str, Dict[str, Any]] = {}
        clocks = self.compute()

        for name, cfg in usart_block.items():
            # name is like "USART2"
            # cfg contains keys like "USART2.IPParameters", "USART2.VirtualMode", maybe "USART2.BaudRate"
            baud_key = f"{name}.BaudRate"
            if baud_key not in cfg:
                continue

            try:
                baud = int(cfg[baud_key])
            except ValueError:
                continue

            # Heuristic: F4 family -> USART1/6 on APB2, others on APB1
            if name in ("USART1", "USART6"):
                bus = "APB2"
            else:
                bus = "APB1"

            bus_freq = clocks.get(bus)
            status = "unknown"
            if bus_freq:
                # Very rough check: baud must be much smaller than bus clock
                if baud >= bus_freq // 8:
                    status = "suspicious"
                else:
                    status = "ok"

            results[name] = {
                "baud": baud,
                "bus": bus,
                "bus_freq": bus_freq,
                "status": status,
            }

        return results

    # ---------------------------------------------------------
    # Pretty print summary
    # ---------------------------------------------------------
    def print_summary(self, usart_block: Dict[str, Dict[str, Any]] | None = None):
        clocks = self.compute()
        print("\n=== Clock Tree Summary ===")
        for name, val in clocks.items():
            if val is None:
                print(f"  {name}: unknown")
            else:
                print(f"  {name}: {val/1_000_000:.2f} MHz")

        if usart_block:
            print("\n=== USART Baud Validation ===")
            results = self.validate_usart_baud(usart_block)
            if not results:
                print("  No baud rate info found in .ioc")
                return
            for usart, info in results.items():
                bf = info["bus_freq"]
                bf_str = f"{bf/1_000_000:.2f} MHz" if bf else "unknown"
                print(f"  {usart}: baud={info['baud']} on {info['bus']} ({bf_str}) -> {info['status']}")

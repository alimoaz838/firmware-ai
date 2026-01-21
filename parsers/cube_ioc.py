import json
from pathlib import Path


class CubeMXParser:
    def __init__(self, ioc_path):
        self.ioc_path = Path(ioc_path)
        self.raw = {}  # flat key=value store

    # ---------------------------------------------------------
    # Load .ioc file (line-by-line parser)
    # ---------------------------------------------------------
    def load(self):
        if not self.ioc_path.exists():
            raise FileNotFoundError(f".ioc file not found: {self.ioc_path}")

        with open(self.ioc_path, "r", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" not in line:
                    continue

                key, value = line.split("=", 1)
                self.raw[key.strip()] = value.strip()

        return self

    # ---------------------------------------------------------
    # MCU
    # ---------------------------------------------------------
    def get_mcu(self):
        return self.raw.get("ProjectManager.DeviceId", None)

    # ---------------------------------------------------------
    # GPIO / Pins
    # ---------------------------------------------------------
    def get_pins(self):
        pins = {}
        for key, value in self.raw.items():
            if "." in key:
                pin = key.split(".")[0]
                if pin.startswith(("PA", "PB", "PC", "PD", "PE", "PF", "PG", "PH", "PI")):
                    field = key.split(".", 1)[1]
                    pins.setdefault(pin, {})[field] = value
        return pins

    # ---------------------------------------------------------
    # DMA
    # ---------------------------------------------------------
    def get_dma(self):
        dma = {}
        for key, value in self.raw.items():
            if key.startswith("Dma."):
                parts = key.split(".")
                if len(parts) >= 3:
                    periph = parts[1]
                    field = ".".join(parts[2:])
                    dma.setdefault(periph, {})[field] = value
        return dma

    # ---------------------------------------------------------
    # NVIC
    # ---------------------------------------------------------
    def get_nvic(self):
        nvic = {}
        for key, value in self.raw.items():
            if key.startswith("NVIC.") and key.count(".") == 1:
                irq = key.replace("NVIC.", "")
                fields = value.split(":")
                if len(fields) >= 3:
                    nvic[irq] = {
                        "enabled": fields[0] == "true",
                        "priority": int(fields[1].replace("\\", "").strip()),
                        "subpriority": int(fields[2].replace("\\", "").strip())
                    }
        return nvic

    # ---------------------------------------------------------
    # ADC
    # ---------------------------------------------------------
    def get_adc(self):
        adc = {}
        for key, value in self.raw.items():
            if key.startswith("ADC"):
                block = key.split(".")[0]
                adc.setdefault(block, {})[key] = value
        return adc

    # ---------------------------------------------------------
    # USART
    # ---------------------------------------------------------
    def get_usart(self):
        usart = {}
        for key, value in self.raw.items():
            if key.startswith("USART"):
                block = key.split(".")[0]
                usart.setdefault(block, {})[key] = value
        return usart

    # ---------------------------------------------------------
    # TIM
    # ---------------------------------------------------------
    def get_tim(self):
        tim = {}
        for key, value in self.raw.items():
            if key.startswith("TIM"):
                block = key.split(".")[0]
                tim.setdefault(block, {})[key] = value
        return tim

    # ---------------------------------------------------------
    # RCC
    # ---------------------------------------------------------
    def get_rcc(self):
        rcc = {}
        for key, value in self.raw.items():
            if key.startswith("RCC."):
                rcc[key.replace("RCC.", "")] = value
        return rcc

    # ---------------------------------------------------------
    # Full structured output
    # ---------------------------------------------------------
    def to_dict(self):
        return {
            "mcu": self.get_mcu(),
            "pins": self.get_pins(),
            "dma": self.get_dma(),
            "nvic": self.get_nvic(),
            "adc": self.get_adc(),
            "usart": self.get_usart(),
            "tim": self.get_tim(),
            "rcc": self.get_rcc(),
        }

    # ---------------------------------------------------------
    # JSON output
    # ---------------------------------------------------------
    def to_json(self, path="project.json"):
        data = self.to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
        return data

    # ---------------------------------------------------------
    # Human-readable summary
    # ---------------------------------------------------------
    def summary(self):
        data = self.to_dict()

        print("\n=== CubeMX Hardware Summary ===")
        print(f"MCU: {data['mcu']}")

        print("\nPins:")
        for pin, info in data["pins"].items():
            sig = info.get("Signal", "None")
            mode = info.get("Mode", "")
            print(f"  {pin} → {sig} {f'({mode})' if mode else ''}")

        print("\nDMA:")
        for periph, cfg in data["dma"].items():
            inst = cfg.get("0.Instance", "Unknown")
            print(f"  {periph} → {inst}")

        print("\nNVIC:")
        for irq, cfg in data["nvic"].items():
            print(f"  {irq} → Enabled={cfg['enabled']} prio={cfg['priority']}")

        print("\nClocks:")
        rcc = data["rcc"]
        print(f"  HSE = {rcc.get('HSE_VALUE')}")
        print(f"  SYSCLK = {rcc.get('SYSCLKFreq_VALUE')}")
        print(f"  PLLCLK = {rcc.get('PLLCLKFreq_Value')}")

        return data

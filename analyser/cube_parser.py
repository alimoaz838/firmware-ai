import configparser
from pathlib import Path

class CubeMXParser:
    def __init__(self, ioc_path):
        self.ioc_path = Path(ioc_path)
        self.config = configparser.ConfigParser()

    def load(self):
        if not self.ioc_path.exists():
            raise FileNotFoundError(f".ioc file not found: {self.ioc_path}")

        self.config.read(self.ioc_path)
        return self

    def get_mcu(self):
        return self.config.get("ProjectManager", "Device", fallback=None)

    def get_pins(self):
        pins = {}
        for section in self.config.sections():
            if section.startswith("Pin"):
                name = self.config.get(section, "Name", fallback=None)
                signal = self.config.get(section, "Signal", fallback=None)
                pins[name] = signal
        return pins

    def get_peripherals(self):
        peripherals = {}
        if "RCC" in self.config:
            for key, value in self.config.items("RCC"):
                peripherals[key] = value
        return peripherals

    def summary(self):
        return {
            "mcu": self.get_mcu(),
            "pins": self.get_pins(),
            "peripherals": self.get_peripherals(),
        }

import configparser
from pathlib import Path

class CubeMXParser:
    """
    Minimal CubeMX .ioc parser.
    Extracts:
      - MCU model
      - Pin assignments
      - RCC peripheral settings
    """

    def __init__(self, ioc_path):
        self.ioc_path = Path(ioc_path)
        self.config = configparser.ConfigParser()

    def load(self):
        if not self.ioc_path.exists():
            raise FileNotFoundError(f".ioc file not found: {self.ioc_path}")

        # CubeMX .ioc files are INI-like
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
                if name:
                    pins[name] = signal
        return pins

    def get_rcc(self):
        rcc = {}
        if "RCC" in self.config:
            for key, value in self.config.items("RCC"):
                rcc[key] = value
        return rcc
    
    def get_nvic(self):
        """
        Extract basic NVIC info from the .ioc.
        This is heuristic-based and can be refined later.
        """
        nvic = {}

        # Some CubeMX versions use a [NVIC] section
        if "NVIC" in self.config:
            for key, value in self.config.items("NVIC"):
                nvic[key] = value

        # Also scan all sections for NVIC-like keys
        for section in self.config.sections():
            for key, value in self.config.items(section):
                if "NVIC" in key.upper() or "IRQ" in key.upper():
                    full_key = f"{section}.{key}"
                    nvic[full_key] = value

        return nvic
    
    def get_dma(self):
        """
        Extract DMA-related configuration.
        Very generic: collects any key with 'DMA' in it.
        """
        dma = {}

        for section in self.config.sections():
            if "DMA" in section.upper():
                dma[section] = dict(self.config.items(section))
                continue

            for key, value in self.config.items(section):
                if "DMA" in key.upper():
                    full_key = f"{section}.{key}"
                    dma[full_key] = value

        return dma
    
    def get_pins(self):
        """
        Return a dict:
        {
          "PA2": {
              "signal": "USART2_TX",
              "mode": "...",
              "pull": "...",
              "speed": "...",
          },
          ...
        }
        """
        pins = {}
        for section in self.config.sections():
            if section.startswith("Pin"):
                name = self.config.get(section, "Name", fallback=None)
                if not name:
                    continue

                pin_info = {}
                for key, value in self.config.items(section):
                    key_upper = key.upper()
                    if key_upper == "SIGNAL":
                        pin_info["signal"] = value
                    elif "MODE" in key_upper:
                        pin_info["mode"] = value
                    elif "PULL" in key_upper:
                        pin_info["pull"] = value
                    elif "SPEED" in key_upper:
                        pin_info["speed"] = value
                    else:
                        # keep other raw fields if needed
                        pin_info[key] = value

                pins[name] = pin_info

        return pins
    
    def get_peripheral_configs(self):
        """
        Collect basic config for common peripherals (TIM, USART/UART, I2C, SPI, ADC).
        Returns:
        {
          "USART2": { ... },
          "TIM3": { ... },
          ...
        }
        """
        periphs = {}
        prefixes = ("USART", "UART", "SPI", "I2C", "TIM", "ADC")

        for section in self.config.sections():
            upper = section.upper()
            if any(upper.startswith(p) for p in prefixes):
                periphs[section] = dict(self.config.items(section))

        return periphs

    def summary(self):
        return {
            "mcu": self.get_mcu(),
            "pins": self.get_pins(),
            "rcc": self.get_rcc(),
            "nvic": self.get_nvic(),
            "dma": self.get_dma(),
            "peripherals": self.get_peripheral_configs(),
        }




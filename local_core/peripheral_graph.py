import networkx as nx

class PeripheralGraph:
    """
    Builds a directed graph of MCU peripherals, pins, and signals
    based on CubeMX .ioc parsed data.
    """

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_node(self, name, **attrs):
        self.graph.add_node(name, **attrs)

    def add_edge(self, src, dst, relation):
        self.graph.add_edge(src, dst, relation=relation)

    def build_from_ioc(self, ioc_summary):
        mcu = ioc_summary.get("mcu", "MCU")
        self.add_node(mcu, type="mcu")

        # Add pins and signals
        for pin, info in ioc_summary["pins"].items():
            self.add_node(pin, type="pin")
            self.add_edge(mcu, pin, relation="has_pin")

            signal = info.get("signal")
            if signal:
                self.add_node(signal, type="signal")
                self.add_edge(pin, signal, relation="pin_to_signal")

        # Add RCC peripherals (filter out PLL and prescalers)
        skip_keys = {"HSE_VALUE", "PLL_M", "PLL_N", "PLL_P", "APB1_PRESCALER", "APB2_PRESCALER"}

        for key, value in ioc_summary["rcc"].items():
            key_upper = key.upper()

            if key_upper in skip_keys:
                continue  # skip non-peripherals

            # Only treat real peripherals as peripherals
            if any(prefix in key_upper for prefix in ["USART", "UART", "SPI", "I2C", "TIM", "DMA", "ADC", "GPIO"]):
                self.add_node(key_upper, type="peripheral")
                self.add_edge("RCC", key_upper, relation=f"clock_{value}")

        return self.graph


    def summary(self):
        return {
            "nodes": list(self.graph.nodes(data=True)),
            "edges": list(self.graph.edges(data=True))
        }

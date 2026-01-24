from dataclasses import dataclass
from typing import Dict, Any
import networkx as nx
import pydot


def export_graphviz(graph, path="hardware.dot"):
    nx.drawing.nx_pydot.write_dot(graph, path)

@dataclass
class PeripheralGraph:
    """
    Builds a hardware dependency graph from the CubeMX .ioc model.

    Nodes:
      - Peripherals (USART2, TIM1, ADC1, DMA1_Stream5, EXTI11, etc.)
      - Pins (PA2, PB10, PC11, ...)
      - Buses / clocks (APB1, APB2, AHB, SYSCLK)

    Edges:
      - DMA -> Peripheral
      - EXTI -> Pin
      - TIM -> Pin (per channel)
      - USART -> Pin (TX/RX/CK)
      - Peripheral -> Bus/Clock
    """

    def __init__(self):
        self.g = nx.DiGraph()

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------
    def build_from_ioc(self, model: Dict[str, Any]) -> nx.DiGraph:
        self._add_clock_nodes(model.get("rcc", {}))
        self._add_pin_and_signal_nodes(model.get("pins", {}))
        self._add_dma_edges(model.get("dma", {}))
        self._add_exti_edges(model.get("pins", {}))
        self._add_tim_channel_edges(model.get("pins", {}))
        self._add_usart_pin_edges(model.get("pins", {}))
        return self.g

    # ---------------------------------------------------------
    # Clocks / buses
    # ---------------------------------------------------------
    def _add_clock_nodes(self, rcc: Dict[str, Any]):
        # Basic clock/bus nodes
        for name in ["HSE", "SYSCLK", "APB1", "APB2"]:
            self.g.add_node(name, type="clock")

        # Attach frequencies if present
        if "HSE_VALUE" in rcc:
            self.g.nodes["HSE"]["freq"] = int(rcc["HSE_VALUE"])
        if "SYSCLKFreq_VALUE" in rcc:
            self.g.nodes["SYSCLK"]["freq"] = int(rcc["SYSCLKFreq_VALUE"])
        if "APB1Freq_Value" in rcc:
            self.g.nodes["APB1"]["freq"] = int(rcc["APB1Freq_Value"])
        if "APB2Freq_Value" in rcc:
            self.g.nodes["APB2"]["freq"] = int(rcc["APB2Freq_Value"])

    # ---------------------------------------------------------
    # Pins and basic signals
    # ---------------------------------------------------------
    def _add_pin_and_signal_nodes(self, pins: Dict[str, Dict[str, Any]]):
        for pin, info in pins.items():
            self.g.add_node(pin, type="pin")

            signal = info.get("Signal")
            mode = info.get("Mode")
            if signal:
                # Add peripheral/signal node
                self.g.add_node(signal, type="signal", mode=mode)
                # Edge: signal -> pin
                self.g.add_edge(signal, pin, type="signal_to_pin")

    # ---------------------------------------------------------
    # DMA -> Peripheral edges
    # ---------------------------------------------------------
    def _add_dma_edges(self, dma: Dict[str, Dict[str, Any]]):
        for periph, cfg in dma.items():
            # Example: periph = "USART2_RX"
            instance = cfg.get("0.Instance")
            if not instance:
                continue

            # Node for DMA stream
            self.g.add_node(instance, type="dma_stream")
            # Node for logical DMA request (e.g., USART2_RX)
            self.g.add_node(periph, type="dma_request")

            # Edge: DMA stream -> DMA request
            self.g.add_edge(instance, periph, type="dma_stream_to_request")

            # Try to infer owning peripheral (USART2 from USART2_RX)
            base = periph.split("_")[0]
            self.g.add_node(base, type="peripheral")
            # Edge: DMA request -> peripheral
            self.g.add_edge(periph, base, type="dma_to_peripheral")

    # ---------------------------------------------------------
    # EXTI -> Pin edges
    # ---------------------------------------------------------
    def _add_exti_edges(self, pins: Dict[str, Dict[str, Any]]):
        for pin, info in pins.items():
            signal = info.get("Signal", "")
            if signal.startswith("GPXTI"):
                # Example: GPXTI11 -> EXTI11
                line = signal.replace("GPXTI", "")
                exti_name = f"EXTI{line}"
                self.g.add_node(exti_name, type="exti")
                self.g.add_edge(exti_name, pin, type="exti_to_pin")

    # ---------------------------------------------------------
    # TIM channel -> Pin edges
    # ---------------------------------------------------------
    def _add_tim_channel_edges(self, pins: Dict[str, Dict[str, Any]]):
        for pin, info in pins.items():
            signal = info.get("Signal", "")
            if signal.startswith("S_TIM") or signal.startswith("TIM"):
                # Examples:
                #   S_TIM1_CH1
                #   TIM3_CH2
                base = signal.replace("S_", "")
                # Split TIMx_CHy
                try:
                    tim, ch = base.split("_", 1)
                except ValueError:
                    continue

                self.g.add_node(tim, type="timer")
                self.g.add_node(base, type="timer_channel")

                # Timer -> channel
                self.g.add_edge(tim, base, type="timer_to_channel")
                # Channel -> pin
                self.g.add_edge(base, pin, type="channel_to_pin")

    # ---------------------------------------------------------
    # USART -> Pin edges (TX/RX/CK)
    # ---------------------------------------------------------
    def _add_usart_pin_edges(self, pins: Dict[str, Dict[str, Any]]):
        for pin, info in pins.items():
            signal = info.get("Signal", "")
            if "USART" in signal:
                # Examples:
                #   USART2_TX
                #   USART2_RX
                #   USART3_CK
                parts = signal.split("_")
                if len(parts) < 2:
                    continue
                usart = parts[0]   # USART2
                role = parts[1]    # TX / RX / CK

                self.g.add_node(usart, type="usart")
                self.g.add_edge(usart, pin, type="usart_to_pin", role=role)
   

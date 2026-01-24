from typing import Dict, Any, List
import re


class RulesEngine:
    """
    Runs consistency checks on:
      - .ioc hardware model
      - Peripheral graph
      - HAL code analysis (optional)
    """

    def __init__(self, model: Dict[str, Any], graph, hal_info: Dict[str, Any] | None = None):
        self.model = model
        self.graph = graph
        self.hal_info = hal_info or {}
        self.warnings: List[Dict[str, Any]] = []

    def run_all(self) -> List[Dict[str, Any]]:
        self._rule_exti_without_irq()
        self._rule_dma_stream_reused()
        self._rule_usart_configured_but_no_init()
        self._rule_irq_enabled_but_no_handler()
        self._rule_pin_mode_mismatch()
        self._rule_missing_hal_start_functions()
        self._rule_missing_callbacks()
        self._rule_clock_domain_mismatch()
        self._rule_peripheral_enabled_but_unused()
        self._rule_dma_irq_not_enabled_in_mx_dma_init()
        self._rule_usart_clock_not_enabled_in_mx_usart_init()
        self._rule_gpio_not_initialized()
        return self.warnings

    # ---------------------------------------------------------
    # Rule: EXTI pin has no IRQ enabled
    # ---------------------------------------------------------
    def _rule_exti_without_irq(self):
        nvic = self.model.get("nvic", {})
        enabled_irqs = {name for name, cfg in nvic.items() if cfg.get("enabled")}

        exti_nodes = [n for n, d in self.graph.nodes(data=True) if d.get("type") == "exti"]
        for exti in exti_nodes:
            m = re.match(r"EXTI(\d+)", exti)
            if not m:
                continue
            line = int(m.group(1))

            if line >= 10:
                irq_name = "EXTI15_10_IRQn"
            elif line >= 5:
                irq_name = "EXTI9_5_IRQn"
            else:
                irq_name = f"EXTI{line}_IRQn"

            if irq_name not in enabled_irqs:
                pins = list(self.graph.successors(exti))
                pins_str = ", ".join(pins) if pins else "unknown pins"
                self.warnings.append({
                    "rule": "exti_without_irq",
                    "message": f"{exti} mapped to {pins_str} but {irq_name} is not enabled in NVIC",
                    "suggestion": f"Enable {irq_name} in NVIC in CubeMX or via HAL.",
                    "code": (
                        f"// Enable EXTI interrupt for line {line}\n"
                        f"HAL_NVIC_SetPriority({irq_name}, 0, 0);\n"
                        f"HAL_NVIC_EnableIRQ({irq_name});"
                    )
                })

    # ---------------------------------------------------------
    # Rule: DMA stream reused by multiple requests
    # ---------------------------------------------------------
    def _rule_dma_stream_reused(self):
        for node, data in self.graph.nodes(data=True):
            if data.get("type") == "dma_stream":
                succ = list(self.graph.successors(node))
                if len(succ) > 1:
                    self.warnings.append({
                        "rule": "dma_stream_reused",
                        "message": f"{node} used by multiple DMA requests: {', '.join(succ)}",
                        "suggestion": "Reassign one of these requests to a different DMA stream."
                    })

    # ---------------------------------------------------------
    # Rule: USART configured in .ioc but no MX_USARTx_Init in code
    # ---------------------------------------------------------
    def _rule_usart_configured_but_no_init(self):
        usart_blocks = self.model.get("usart", {})
        if not usart_blocks:
            return

        called_inits = set(self.hal_info.get("mx_inits", []))

        for usart_name in usart_blocks.keys():
            func = f"MX_{usart_name}_Init"
            if func not in called_inits:
                self.warnings.append({
                    "rule": "usart_no_init_call",
                    "message": f"{usart_name} configured in .ioc but {func} not called in main.c",
                    "suggestion": f"Call {func}() during system initialization before using {usart_name}.",
                    "code": f"{func}();"
                })

    # ---------------------------------------------------------
    # Rule: IRQ enabled in NVIC but no handler in code
    # ---------------------------------------------------------
    def _rule_irq_enabled_but_no_handler(self):
        nvic = self.model.get("nvic", {})
        enabled_irqs = [name for name, cfg in nvic.items() if cfg.get("enabled")]

        handlers = set(self.hal_info.get("irq_handlers", []))

        for irq in enabled_irqs:
            handler = irq.replace("_IRQn", "_IRQHandler")
            if handler not in handlers:
                self.warnings.append({
                    "rule": "irq_no_handler",
                    "message": f"{irq} enabled in NVIC but {handler} not found in code",
                    "suggestion": f"Implement {handler}() in your interrupt source file."
                })

    # ---------------------------------------------------------
    # Rule: Pin mode mismatch (USART/TIM/ADC)
    # ---------------------------------------------------------
    def _rule_pin_mode_mismatch(self):
        pins = self.model.get("pins", {})

        for pin, info in pins.items():
            signal = info.get("Signal")
            mode = info.get("Mode", "")

            if not signal:
                continue

            # USART pins must be AF mode
            if "USART" in signal and "AF" not in mode and "Synchronous" not in mode:
                self.warnings.append({
                    "rule": "pin_mode_mismatch",
                    "message": f"{pin} used for {signal} but not in Alternate Function mode",
                    "suggestion": f"Set {pin} to AF mode for {signal} in CubeMX."
                })

            # TIM channels must be AF mode
            if ("TIM" in signal or "S_TIM" in signal) and "AF" not in mode:
                self.warnings.append({
                    "rule": "pin_mode_mismatch",
                    "message": f"{pin} used for {signal} but not in AF mode",
                    "suggestion": f"Set {pin} to AF mode for {signal}."
                })

            # ADC pins must be analog
            if "ADC" in signal and "Analog" not in mode:
                self.warnings.append({
                    "rule": "pin_mode_mismatch",
                    "message": f"{pin} used for ADC but not in Analog mode",
                    "suggestion": f"Set {pin} to Analog mode for ADC input."
                })

    # ---------------------------------------------------------
    # Rule: Missing HAL start functions (USART DMA, TIM PWM, ADC IT)
    # ---------------------------------------------------------
    def _rule_missing_hal_start_functions(self):
        hal_calls = self.hal_info.get("hal_calls", [])
        usart_blocks = self.model.get("usart", {})
        tim_blocks = self.model.get("tim", {})
        adc_blocks = self.model.get("adc", {})

        # USART RX DMA
        for usart in usart_blocks:
            if f"{usart}_RX" in self.model.get("dma", {}):
                if "HAL_UART_Receive_DMA" not in hal_calls:
                    self.warnings.append({
                        "rule": "missing_hal_start",
                        "message": f"{usart} uses DMA RX but HAL_UART_Receive_DMA() not called",
                        "suggestion": f"Call HAL_UART_Receive_DMA(&h{usart.lower()}, buffer, size).",
                        "code": f"HAL_UART_Receive_DMA(&h{usart.lower()}, rx_buffer, RX_SIZE);"
                    })

        # TIM PWM
        for tim in tim_blocks:
            if "CH" in str(tim_blocks[tim]):
                if "HAL_TIM_PWM_Start" not in hal_calls:
                    self.warnings.append({
                        "rule": "missing_hal_start",
                        "message": f"{tim} configured for PWM but HAL_TIM_PWM_Start() not called",
                        "suggestion": f"Call HAL_TIM_PWM_Start(&h{tim.lower()}, TIM_CHANNEL_X)."
                    })

        # ADC interrupt mode
        for adc in adc_blocks:
            if "SamplingTime" in str(adc_blocks[adc]):
                if "HAL_ADC_Start_IT" not in hal_calls:
                    self.warnings.append({
                        "rule": "missing_hal_start",
                        "message": f"{adc} configured but HAL_ADC_Start_IT() not called",
                        "suggestion": f"Call HAL_ADC_Start_IT(&h{adc.lower()}).",
                        "code": f"HAL_ADC_Start_IT(&h{adc.lower()});"
                    })

    # ---------------------------------------------------------
    # Rule: Missing callbacks
    # ---------------------------------------------------------
    def _rule_missing_callbacks(self):
        callbacks = set(self.hal_info.get("callbacks", []))

        # EXTI
        if "HAL_GPIO_EXTI_Callback" not in callbacks:
            self.warnings.append({
                "rule": "missing_callback",
                "message": "EXTI interrupts enabled but HAL_GPIO_EXTI_Callback() not implemented",
                "suggestion": "Implement HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)."
            })

        # ADC
        if "HAL_ADC_ConvCpltCallback" not in callbacks:
            self.warnings.append({
                "rule": "missing_callback",
                "message": "ADC interrupt mode enabled but HAL_ADC_ConvCpltCallback() missing",
                "suggestion": "Implement HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)."
            })

        # TIM
        if "HAL_TIM_PeriodElapsedCallback" not in callbacks:
            self.warnings.append({
                "rule": "missing_callback",
                "message": "Timer interrupt enabled but HAL_TIM_PeriodElapsedCallback() missing",
                "suggestion": "Implement HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)."
            })

    # ---------------------------------------------------------
    # Rule: Clock domain mismatch (simple USART check)
    # ---------------------------------------------------------
    def _rule_clock_domain_mismatch(self):
        clocks = self.model.get("rcc", {})
        usart_blocks = self.model.get("usart", {})

        apb1 = int(clocks.get("APB1Freq_Value", 0))
        apb2 = int(clocks.get("APB2Freq_Value", 0))

        for usart in usart_blocks:
            if usart in ("USART1", "USART6"):
                bus = apb2
            else:
                bus = apb1

            if bus < 8_000_000:  # < 8 MHz is suspicious
                self.warnings.append({
                    "rule": "clock_domain_mismatch",
                    "message": f"{usart} running on very low bus clock ({bus} Hz)",
                    "suggestion": "Increase APB clock or lower baud rate."
                })

    # ---------------------------------------------------------
    # Rule: Peripheral enabled but unused
    # ---------------------------------------------------------
    def _rule_peripheral_enabled_but_unused(self):
        hal_calls = self.hal_info.get("hal_calls", [])
        usart_blocks = self.model.get("usart", {})
        adc_blocks = self.model.get("adc", {})
        tim_blocks = self.model.get("tim", {})

        # USART
        for usart in usart_blocks:
            if usart not in str(hal_calls):
                self.warnings.append({
                    "rule": "unused_peripheral",
                    "message": f"{usart} configured in .ioc but never used in code",
                    "suggestion": f"Remove {usart} from CubeMX or use HAL_UART_Transmit/Receive."
                })

        # ADC
        for adc in adc_blocks:
            if adc not in str(hal_calls):
                self.warnings.append({
                    "rule": "unused_peripheral",
                    "message": f"{adc} configured but no HAL_ADC_Start() or HAL_ADC_Start_IT() found",
                    "suggestion": f"Remove {adc} or start conversions in code."
                })

        # TIM
        for tim in tim_blocks:
            if tim not in str(hal_calls):
                self.warnings.append({
                    "rule": "unused_peripheral",
                    "message": f"{tim} configured but no HAL_TIM_* calls found",
                    "suggestion": f"Remove {tim} or start the timer in code."
                })

    # ---------------------------------------------------------
    # Rule: DMA IRQ not enabled / not in MX_DMA_Init
    # ---------------------------------------------------------
    def _rule_dma_irq_not_enabled_in_mx_dma_init(self):
        dma_cfg = self.model.get("dma", {})
        nvic = self.model.get("nvic", {})
        mx_bodies = self.hal_info.get("mx_init_bodies", {})

        if "DMA" not in mx_bodies:
            if dma_cfg:
                self.warnings.append({
                    "rule": "dma_irq_no_mx_dma_init",
                    "message": "DMA configured in .ioc but no MX_DMA_Init() function found in code",
                    "suggestion": "Ensure MX_DMA_Init() exists and is called from main.c."
                })
            return

        dma_body = mx_bodies["DMA"]

        for req, cfg in dma_cfg.items():
            instance = cfg.get("0.Instance")
            if not instance:
                continue

            irq_name = f"{instance}_IRQn"
            nvic_entry = nvic.get(irq_name)

            if not nvic_entry or not nvic_entry.get("enabled"):
                self.warnings.append({
                    "rule": "dma_irq_not_enabled",
                    "message": f"{instance} used for {req} but {irq_name} is not enabled in NVIC",
                    "suggestion": f"Enable {irq_name} in NVIC in CubeMX or via HAL_NVIC_EnableIRQ.",
                    "code": (
                        f"HAL_NVIC_SetPriority({irq_name}, 0, 0);\n"
                        f"HAL_NVIC_EnableIRQ({irq_name});"
                    )
                })
                continue

            pattern = rf"HAL_NVIC_EnableIRQ\s*\(\s*{irq_name}\s*\)"
            if not re.search(pattern, dma_body):
                self.warnings.append({
                    "rule": "dma_irq_not_enabled_in_mx_dma_init",
                    "message": f"{irq_name} enabled in NVIC but MX_DMA_Init() does not call HAL_NVIC_EnableIRQ({irq_name})",
                    "suggestion": f"Add HAL_NVIC_EnableIRQ({irq_name}); inside MX_DMA_Init().",
                    "code": f"HAL_NVIC_EnableIRQ({irq_name});"
                })

    # ---------------------------------------------------------
    # Rule: USART clock not enabled in MX_USARTx_Init
    # ---------------------------------------------------------
    def _rule_usart_clock_not_enabled_in_mx_usart_init(self):
        usart_blocks = self.model.get("usart", {})
        mx_bodies = self.hal_info.get("mx_init_bodies", {})

        for usart in usart_blocks:
            body = mx_bodies.get(usart)
            if not body:
                self.warnings.append({
                    "rule": "usart_no_mx_init_body",
                    "message": f"{usart} configured in .ioc but MX_{usart}_Init() body not found in code",
                    "suggestion": f"Ensure MX_{usart}_Init() is present in main project sources."
                })
                continue

            pattern = rf"__HAL_RCC_{usart}_CLK_ENABLE\s*\("
            if not re.search(pattern, body):
                self.warnings.append({
                    "rule": "usart_clock_not_enabled",
                    "message": f"{usart} configured but MX_{usart}_Init() does not enable its RCC clock",
                    "suggestion": f"Add __HAL_RCC_{usart}_CLK_ENABLE(); at the start of MX_{usart}_Init().",
                    "code": f"__HAL_RCC_{usart}_CLK_ENABLE();"
                })

    # ---------------------------------------------------------
    # Rule: GPIO not initialized in MX_GPIO_Init
    # ---------------------------------------------------------
    def _rule_gpio_not_initialized(self):
        mx_bodies = self.hal_info.get("mx_init_bodies", {})
        gpio_body = mx_bodies.get("GPIO", "")

        if not gpio_body:
            self.warnings.append({
                "rule": "missing_mx_gpio_init",
                "message": "MX_GPIO_Init() not found in project sources",
                "suggestion": "Ensure MX_GPIO_Init() exists and is called from main.c."
            })
            return

        pins = self.model.get("pins", {})

        for pin, info in pins.items():
            signal = info.get("Signal")
            if not signal:
                continue

            if any(x in signal for x in ["USART", "TIM", "ADC", "GPXTI"]):
                port = pin[:2]  # PA, PB, PC...
                pattern = rf"\b{port}\b.*\b{pin}\b"
                if not re.search(pattern, gpio_body):
                    self.warnings.append({
                        "rule": "gpio_not_initialized",
                        "message": f"{pin} used for {signal} but not initialized in MX_GPIO_Init()",
                        "suggestion": f"Add GPIO init code for {pin} inside MX_GPIO_Init().",
                        "code": (
                            f"GPIO_InitTypeDef GPIO_InitStruct = {{0}};\n"
                            f"__HAL_RCC_{port}_CLK_ENABLE();\n"
                            f"GPIO_InitStruct.Pin = {pin};\n"
                            f"GPIO_InitStruct.Mode = GPIO_MODE_AF_PP; // or correct mode for {signal}\n"
                            f"GPIO_InitStruct.Pull = GPIO_NOPULL;\n"
                            f"GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;\n"
                            f"GPIO_InitStruct.Alternate = /* correct AF for {signal} */;\n"
                            f"HAL_GPIO_Init({port}, &GPIO_InitStruct);"
                        )
                    })

    # ---------------------------------------------------------
    # Diagnose helpers
    # ---------------------------------------------------------
    def diagnose_usart(self, name: str) -> List[Dict[str, Any]]:
        """
        Return only the warnings relevant to a specific USART peripheral.
        """
        relevant = []
        for w in self.warnings:
            if name in w.get("message", "") or name in w.get("suggestion", ""):
                relevant.append(w)
        return relevant

import re
from pathlib import Path
from typing import Dict, Any, List


class HalCodeAnalyzer:
    """
    Lightweight HAL code analyzer:
      - Finds MX_XXX_Init() calls in main.c
      - Finds IRQHandler() functions in interrupt files
      - Finds HAL_XXX(...) calls across sources
      - Finds HAL_XXX_Callback(...) implementations
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.main_text = ""
        self.it_texts: List[str] = []
        self.all_texts: List[str] = []

    # ---------------------------------------------------------
    # Load project sources
    # ---------------------------------------------------------
    def load(self):
        core_src = self.project_root / "Core" / "Src"

        # main.c
        main_c = core_src / "main.c"
        if main_c.exists():
            self.main_text = main_c.read_text(errors="ignore")
            self.all_texts.append(self.main_text)

        # interrupt files (stm32f4xx_it.c, etc.)
        if core_src.exists():
            for f in core_src.glob("*it.c"):
                txt = f.read_text(errors="ignore")
                self.it_texts.append(txt)
                self.all_texts.append(txt)

        # any other C files in Core/Src
        if core_src.exists():
            for f in core_src.glob("*.c"):
                if f.name not in ("main.c",) and not f.name.endswith("it.c"):
                    txt = f.read_text(errors="ignore")
                    self.all_texts.append(txt)

        return self

    # ---------------------------------------------------------
    # MX_XXX_Init calls
    # ---------------------------------------------------------
    def get_mx_inits(self) -> List[str]:
        """
        Returns list like ["USART2", "ADC1", "TIM1", ...]
        from calls MX_USART2_Init(), MX_ADC1_Init(), etc.
        """
        return re.findall(r'\bMX_([A-Za-z0-9_]+)_Init\s*\(', self.main_text)

    # ---------------------------------------------------------
    # IRQHandler functions
    # ---------------------------------------------------------
    def get_irq_handlers(self) -> List[str]:
        """
        Returns list like ["EXTI15_10_IRQHandler", "DMA1_Stream5_IRQHandler", ...]
        """
        handlers: List[str] = []
        for text in self.it_texts:
            handlers += re.findall(r'\bvoid\s+([A-Za-z0-9_]+_IRQHandler)\s*\(', text)
        return handlers

    # ---------------------------------------------------------
    # HAL_XXX(...) calls
    # ---------------------------------------------------------
    def get_hal_calls(self) -> List[str]:
        """
        Returns list of HAL function names used, e.g.:
          ["HAL_UART_Receive_DMA", "HAL_TIM_PWM_Start", ...]
        """
        calls: List[str] = []
        pattern = re.compile(r'\b(HAL_[A-Za-z0-9_]+)\s*\(')
        for text in self.all_texts:
            calls += pattern.findall(text)
        # deduplicate
        return sorted(set(calls))

    # ---------------------------------------------------------
    # HAL_XXX_Callback(...) implementations
    # ---------------------------------------------------------
    def get_callbacks(self) -> List[str]:
        """
        Returns list like:
          ["HAL_GPIO_EXTI_Callback", "HAL_TIM_PeriodElapsedCallback", ...]
        """
        callbacks: List[str] = []
        pattern = re.compile(r'\bvoid\s+(HAL_[A-Za-z0-9_]+Callback)\s*\(')
        for text in self.all_texts:
            callbacks += pattern.findall(text)
        return sorted(set(callbacks))

    # ---------------------------------------------------------
    # Optional: MX_XXX_Init bodies (for deeper analysis later)
    # ---------------------------------------------------------
    def get_mx_init_bodies(self) -> Dict[str, str]:
        """
        Returns dict:
          { "USART2": "void MX_USART2_Init(void) { ... }", ... }
        """
        bodies: Dict[str, str] = {}
        pattern = re.compile(
            r'void\s+MX_([A-Za-z0-9_]+)_Init\s*\([^)]*\)\s*\{',
            re.MULTILINE
        )

        for text in self.all_texts:
            for match in pattern.finditer(text):
                name = match.group(1)
                start = match.start()
                # naive brace matching
                body = self._extract_brace_block(text, start)
                if body:
                    bodies[name] = body

        return bodies

    def _extract_brace_block(self, text: str, start_index: int) -> str | None:
        """
        Given index at 'void MX_XXX_Init(...) {', return the full function body
        including braces. Very simple brace counter.
        """
        brace_index = text.find("{", start_index)
        if brace_index == -1:
            return None

        depth = 0
        for i in range(brace_index, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start_index:i+1]
        return None
        # ---------------------------------------------------------
    # Queries on MX_XXX_Init bodies
    # ---------------------------------------------------------
    def body_contains(self, periph: str, pattern: str) -> bool:
        """
        Returns True if MX_<periph>_Init body contains the given regex pattern.
        Example: body_contains("DMA", r"HAL_NVIC_EnableIRQ\s*\(\s*DMA1_Stream5_IRQn")
        """
        bodies = self.get_mx_init_bodies()
        body = bodies.get(periph)
        if not body:
            return False
        return re.search(pattern, body) is not None

    def any_body_contains(self, pattern: str) -> bool:
        """
        Returns True if any MX_XXX_Init body contains the given regex pattern.
        """
        for body in self.get_mx_init_bodies().values():
            if re.search(pattern, body):
                return True
        return False

    # ---------------------------------------------------------
    # Aggregate
    # ---------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mx_inits": self.get_mx_inits(),
            "irq_handlers": self.get_irq_handlers(),
            "hal_calls": self.get_hal_calls(),
            "callbacks": self.get_callbacks(),
            "mx_init_bodies": self.get_mx_init_bodies(),
        }


class ClockTreeAnalyzer:
    """
    Very simple clock tree analyzer for STM32-style PLL configs.
    Uses data from the .ioc RCC section.
    """

    def __init__(self, rcc_section: dict):
        # rcc_section is summary["rcc"] from CubeMXParser
        self.rcc = {k.upper(): v for k, v in rcc_section.items()}
        self.clocks = {}

    def _get_int(self, key, default=None):
        val = self.rcc.get(key)
        try:
            return int(val)
        except (TypeError, ValueError):
            return default

    def compute(self):
        """
        Compute a few key clocks:
        - HSE
        - SYSCLK (via PLL)
        - APB1, APB2 (if prescalers present)
        """
        # HSE value (fallback 8 MHz)
        hse = self._get_int("HSE_VALUE", 8_000_000)
        self.clocks["HSE"] = hse

        pll_m = self._get_int("PLL_M")
        pll_n = self._get_int("PLL_N")
        pll_p = self._get_int("PLL_P")

        sysclk = None
        if pll_m and pll_n and pll_p:
            sysclk = (hse / pll_m) * pll_n / pll_p

        self.clocks["SYSCLK"] = sysclk

        # Optional: APB1/APB2 prescalers if present
        apb1_presc = self._get_int("APB1_PRESCALER", 4)
        apb2_presc = self._get_int("APB2_PRESCALER", 2)

        if sysclk:
            self.clocks["APB1"] = sysclk / apb1_presc
            self.clocks["APB2"] = sysclk / apb2_presc
        else:
            self.clocks["APB1"] = None
            self.clocks["APB2"] = None

        return self.clocks

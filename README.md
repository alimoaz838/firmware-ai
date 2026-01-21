# firmware-ai
AI-powered static analysis and debugging assistant for embedded firmware (STM32, nRF52, RP2040). Local + hybrid AI. Understands CubeMX, HAL, linker scripts, startup code, and build logs.
# Firmware AI — Embedded Firmware Debugging Assistant

Firmware AI is a hybrid local+cloud AI tool designed specifically for embedded firmware engineers.  
It understands STM32, nRF52, RP2040, CubeMX, HAL, linker scripts, startup code, and build logs.

General-purpose AI models (GPT‑5, Code Llama, Mistral) are powerful, but none specialize in embedded firmware.  
This tool fills that gap.

---

## ✨ Features

### 🔍 Static Analysis
- Build log parsing
- CubeMX `.ioc` parsing
- HAL configuration analysis
- Linker script inspection
- Startup assembly inspection
- Peripheral graph reconstruction
- Clock tree validation
- DMA/ISR conflict detection
- GPIO AF conflict detection

### 🤖 AI Reasoning
- Local LLM support (Ollama)
- Multi-line error context
- Hardware-aware explanations
- HAL/CubeMX-aware suggestions

# 📘 Firmware‑AI  
### *AI‑powered assistant for STM32 firmware development*

Firmware‑AI is a hybrid **static‑analysis + AI reasoning tool** designed to help embedded engineers debug, analyze, and understand STM32 firmware projects.

It combines:

- **Static analysis** of build logs and CubeMX `.ioc` files  
- **Hardware‑aware reasoning** (peripheral graph, clock tree)  
- **Local LLM explanations** using Ollama  

The goal is simple:  
**Make firmware debugging faster, smarter, and less painful.**

---

## ✨ Features

### 🔍 Build Log Analyzer
- Parses GCC/Clang/LD build logs  
- Extracts errors & warnings  
- Sends top errors to a local LLM  
- Produces human‑readable explanations  
- Suggests fixes and double‑checks  

### 📁 CubeMX `.ioc` Parser
Extracts hardware configuration directly from CubeMX:

- MCU model  
- Pin → signal mapping  
- GPIO modes, pull, speed  
- RCC configuration (HSE, PLL, prescalers)  
- DMA configuration  
- NVIC configuration  
- Peripheral configs (USART, TIM, ADC, SPI, I2C)

### 🧠 Peripheral Graph Builder
Builds a directed graph of the hardware topology:

- MCU → Pins  
- Pins → Signals  
- RCC → Peripherals  

Useful for detecting:

- AF conflicts  
- Missing clock enables  
- Misconfigured pins  

### ⏱ Clock Tree Analyzer
Computes key clock frequencies:

- HSE  
- SYSCLK  
- APB1  
- APB2  
- PLL effects  

Useful for:

- UART baud rate validation  
- Timer frequency checks  
- ADC sampling rate checks  

### 🤖 Local LLM Integration (Ollama)
- Uses a local model (e.g., Mistral)  
- No cloud dependency  
- Explains errors in plain English  
- Suggests fixes  

---

## 📂 Project Structure

firmware_ai/
│
├── local_core/
│   ├── cli.py                  # Main CLI entry point
│   ├── peripheral_graph.py    # Builds hardware graph
│   ├── clock_tree.py          # Computes clock frequencies
│
├── parsers/
│   ├── build_logs.py          # GCC/Clang/LD log parser
│   ├── cube_ioc.py            # CubeMX .ioc parser
│
├── llm_engine/
│   ├── local_llm.py           # Ollama integration
│
├── rules_engine/
│   ├── engine.py               # Rule loader
│   ├── isr_rules.yaml         # Example rule set
│
└── examples/
├── sample.ioc              # Example CubeMX file


---

## 🛠 Installation

### 1. Clone the repo

git clone https://github.com/<your-org>/firmware-ai.git
cd firmware-ai


### 2. Install dependencies

pip install -r requirements.txt

### 3. (Optional) Install Ollama
https://ollama.com

Code

Pull a model:
ollama pull mistral

Code

---

## 🧪 Usage — All Commands

### 1. Analyze a build log
python local_core/cli.py build.log

Code

### 2. Parse a CubeMX `.ioc` file
python local_core/cli.py project.ioc

Code

### 3. Generate a peripheral graph
python local_core/cli.py project.ioc  --graph

Code

### 4. Analyze the clock tree
python local_core/cli.py project.ioc  --clock

Code

### 5. Default behavior
If no file is provided, it analyzes:
build.log

Code

---

## 🧩 Example Workflow

### Check build errors
python local_core/cli.py build.log

Code

### Inspect CubeMX configuration
python local_core/cli.py MyBoard.ioc

Code

### Visualize hardware graph
python local_core/cli.py MyBoard.ioc  --graph

Code

### Verify clock configuration
python local_core/cli.py MyBoard.ioc  --clock


---

## 📅 Roadmap

### Short‑term
- DMA channel conflict detection  
- GPIO AF conflict detection  
- Timer channel mapping  
- UART baud rate validation  
- ADC sampling rate validation  

### Mid‑term
- HAL init‑order checker  
- Interrupt priority analyzer  
- Memory map + linker script parser  
- Startup file analyzer  

### Long‑term
- Full project‑wide static analysis  
- Auto‑fix suggestions  
- VSCode extension  
- Web UI  

---

## 🤝 Contributing

Contributions are welcome!  
Open an issue or submit a PR to:

- Add new rules  
- Improve the `.ioc` parser  
- Add support for new STM32 families  
- Improve the graph engine  
- Add new analysis modules  

---

## 📧 Contact

Maintainer: **Ali Moaz**  
For questions or ideas, open an issue or reach out.

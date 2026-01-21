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
- “Explain like a senior engineer” mode

### 🛠️ Developer Tools
- CLI tool
- VS Code extension (coming soon)
- Web dashboard (coming soon)

---

## 🚀 Quick Start

### 1. Install dependencies

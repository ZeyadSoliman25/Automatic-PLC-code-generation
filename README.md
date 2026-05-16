# 🤖 AutoPLC — AI Code Generator for Siemens TIA Portal

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/TIA%20Portal-V17%2B-orange.svg" alt="TIA Portal">
  <img src="https://img.shields.io/badge/Inference-Qwen3--Coder--Next-purple.svg" alt="Local AI">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</p>

AutoPLC generates Siemens **STL / SCL** code from natural-language prompts or control narrative documents using a locally quantized Qwen3 AI model. It produces TIA Openness-compliant XML and imports it directly into your `.apXX` project — fully offline, zero API costs, complete privacy.

---

## 📋 Table of Contents

- [Features](#-features)
- [Workflow](#-workflow)
- [Installation](#-installation)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [Advanced Tips](#-advanced-tips)
- [Disclaimer](#-disclaimer)
- [Contributing](#-contributing)
- [Acknowledgments](#-acknowledgments)

---

## ✨ Features

| Feature | Details |
|---|---|
| 🧠 **Local AI Inference** | Runs `Qwen/Qwen3-Coder-Next` with 4-bit NF4 quantization (~2.5 GB VRAM) |
| 📝 **Dual Input Modes** | Text prompts or uploaded `.txt` / `.docx` / `.pdf` control narratives |
| 🔀 **Auto Language Routing** | Dynamically switches between STL and SCL generation pipelines |
| 📦 **Direct TIA Import** | Injects generated Openness XML straight into your `.apXX` project |
| 🖥️ **Modern GUI** | Clean, responsive `customtkinter` desktop interface |
| 🔒 **Fully Offline** | No API keys, no cloud calls, no data leaves your machine |

---

## 🔄 Workflow

```
User Input  ──►  Parser Layer  ──►  Language Router  ──►  Local AI Gen
                                                               │
TIA Openness Import  ◄──  XML Injection  ◄──────────────────────
```

---

## 📦 Installation

### Prerequisites

- **OS:** Windows 10 / 11 (TIA Portal Openness API is Windows-only)
- **Python:** 3.10+
- **GPU:** NVIDIA with CUDA support — ≥ 4 GB VRAM recommended for 4-bit inference
- **TIA Portal:** V17+ with the **Openness API** feature enabled during installation

### 1 — Clone the repository

```bash
git clone https://github.com/your-username/AutoPLC.git
cd AutoPLC
```

### 2 — Install Python dependencies

```bash
pip install -r requirements.txt
```

> **Windows note — bitsandbytes:** The standard `bitsandbytes` package does not ship CUDA binaries for Windows. Install the pre-compiled wheel instead:
> ```bash
> pip install bitsandbytes-windows
> ```

### 3 — Configure the TIA Openness DLL path

Open `TIA_Handler.py` and update the reference to match your installed TIA Portal version:

```python
# TIA_Handler.py
clr.AddReference(
    r"C:\Program Files\Siemens\Automation\Portal V17\PublicAPI\V17\Siemens.Engineering.dll"
)
```

---

## 🚀 Usage

### GUI (recommended)

```bash
python GUI.py
```

1. **Input mode** — choose between a free-text prompt or a document upload (`.txt`, `.docx`, `.pdf`)
2. **Settings** — select TIA version, target PLC type, and output language (STL / SCL)
3. **Project file** — browse to your `.apXX` TIA Portal project
4. Click **Generate Code** — the AI runs locally, generates the XML, and imports it into your project automatically

### Programmatic / batch use

```python
from generate_stl import generate_ob1
from generate_scl import generate_ob1_scl

# STL
stl_path = generate_ob1("Latch motor on Start, unlatch on Stop.")

# SCL
scl_path = generate_ob1_scl("Conveyor belt with speed ramp-up over 5 seconds and emergency stop.")
```

---

## 🗂️ Project Structure

```
AutomaticPLCCodeGenerator/
├── GUI.py                  # Desktop interface & workflow orchestrator
├── TIA_Handler.py          # TIA Portal Openness API wrapper (Python.NET)
├── generate_stl.py         # STL pipeline — local AI + template injection
├── generate_scl.py         # SCL pipeline — local AI + template injection
├── OB1_template.xml        # TIA Openness XML template (STL)
├── OB1_SCL_template.xml    # TIA Openness XML template (SCL)
└── requirements.txt        # Python dependencies
```

---

## ⚙️ Advanced Tips

**Custom coding standards** — Edit `SYSTEM_PROMPT` in `generate_stl.py` or `generate_scl.py` to enforce stricter XML rules or add company-specific naming conventions and comment styles.

**VRAM-constrained machines** — The 4-bit NF4 quantization already targets ~2.5 GB VRAM. If you hit OOM errors, reduce `max_new_tokens` in the inference call or try an 8-bit quantization configuration.

**Multiple OBs** — The template system is not limited to OB1. Duplicate either template, adjust the `<Name>`, `<Number>`, and `<SecondaryType>` fields, then pass the new template path to `generate_ob1()` / `generate_ob1_scl()` via their `template_path` argument.

---

## ⚠️ Disclaimer

> AI-generated PLC code **must be reviewed, simulated, and validated by a qualified automation engineer** before deployment to any physical hardware or safety-critical system. AutoPLC is a productivity assistant — it is not a certified safety tool and provides no safety guarantees. The authors and contributors accept no liability for equipment damage, production loss, personal injury, or any other incident arising from the use of this software.

---

## 🤝 Contributing

Contributions are welcome! To get started:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes with clear messages
4. Open a Pull Request describing what you changed and why

Please ensure any new generation logic is tested against at least one TIA Portal import cycle before submitting.

---

## 🙏 Acknowledgments

- [Qwen Team](https://github.com/QwenLM/Qwen) — for the open-weight `Qwen3-Coder-Next` model
- [Siemens AG](https://www.siemens.com) — for the TIA Portal Openness API
- [Hugging Face](https://huggingface.co) & [bitsandbytes](https://github.com/TimDettmers/bitsandbytes) — for quantization and inference tooling
- The industrial automation community — for open knowledge sharing and feedback

---

<p align="center">Made with ☕ and ladder logic</p>

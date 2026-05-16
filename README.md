# 🤖 AutoPLC AI Agent for Siemens TIA Portal

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![TIA Portal](https://img.shields.io/badge/TIA%20Portal-V17%2B-orange.svg)
![Local AI](https://img.shields.io/badge/Inference-Qwen3--Coder--Next-purple)
![License](https://img.shields.io/badge/License-MIT-green.svg)

AutoPLC generates Siemens STL/SCL code from prompts or docs using a locally quantized Qwen3 AI model. It creates TIA Openness-compliant XML and directly imports it into your `.apXX` project. Fully offline, zero API costs, complete privacy.

## 🌟 Features
- 🧠 **Local AI Inference**: Runs `Qwen/Qwen3-Coder-Next` with 4-bit NF4 quantization (~2.5 GB VRAM)
- 📝 **Dual Input**: Text prompts or uploaded `.txt`/`.docx`/`.pdf` control narratives
- 🔀 **Auto Routing**: Dynamically switches between STL & SCL generation pipelines
- 📦 **Direct TIA Import**: Injects generated Openness XML straight into your `.apXX` project
- 🖥️ **Modern GUI**: Clean, responsive `customtkinter` desktop interface

## 🔄 Workflow
User Input → Parser Layer → Language Router → Local AI Gen → XML Injection → TIA Openness Import

## 📦 Installation

### 1. Prerequisites
- **Windows 10/11** (TIA Portal & Openness API are Windows-only)
- Python 3.10+
- NVIDIA GPU with CUDA support (≥4 GB VRAM recommended for 4-bit inference)
- Siemens TIA Portal V17+ with **Openness API** enabled

### 2. Install Dependencies
```bash
pip install -r requirements.txt

### 3. Configure Openness DLL
Open TIA_Handler.py and update the DLL path to match your installed TIA version:
```python
clr.AddReference(r"C:\Program Files\Siemens\Automation\Portal V17\PublicAPI\V17\Siemens.Engineering.dll")

### Usage
1- Launch the GUI
```bash
python GUI.py

2- Configure Settings
    *Choose input mode (text or document upload)
    *Select TIA version, PLC type, and language (STL/SCL)
    *Browse to your .apXX TIA project file

3- Generate & Import
Click Generate Code → AI runs locally → XML is automatically injected into your project

### Project Structure
AutomaticPLCCodeGenerator/
├── GUI.py                  # Main desktop interface & workflow orchestrator
├── TIA_Handler.py          # TIA Portal Openness API wrapper (Python.NET)
├── generate_stl.py         # STL code generator (local AI + template injection)
├── generate_scl.py         # SCL code generator (local AI + template injection)
├── OB1_template.xml        # TIA Openness XML template for STL
├── OB1_SCL_template.xml    # TIA Openness XML template for SCL
└── requirements.txt        # Python dependencies

### Advanced Tips
-VRAM Optimization: 4-bit quantization requires bitsandbytes. On Windows, use precompiled wheels: (pip install bitsandbytes-windows)

-Batch/Programmatic Use: Call generators directly in your scripts:
```python
from generate_stl import generate_ob1
xml_path = generate_ob1("Latch motor on start, unlatch on stop.")

-Custom Prompts: Edit SYSTEM_PROMPT in generate_*.py to enforce stricter XML rules or add company-specific coding standards.

### Important Disclaimer
AI-generated PLC code must be reviewed, simulated, and tested by a qualified automation engineer before deployment to physical hardware. This tool is an assistant, not a certified safety system. The authors assume no liability for equipment damage, production loss, or safety incidents.

### Contributing
Contributions are welcome! Please fork the repo, create a feature branch, and open a Pull Request with clear descriptions of your changes.

### Acknowledgments
-Qwen Team for the open-weight Qwen3-Coder-Next model
-Siemens AG for the TIA Portal Openness API
-Hugging Face & BitsAndBytes for quantization & inference tooling
-The industrial automation community for open knowledge sharing

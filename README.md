# Fermeon — AI CAD Generator

Fermeon is a multi-LLM application that transforms natural language prompts into manufacturable CAD models (STEP/STL files). It intelligently routes logic through leading models (GPT-4o, Claude 3.5 Sonnet, Gemini 2.0, DeepSeek, Mistral) and local models (Ollama Qwen2.5-Coder) using a highly consistent CadQuery generation framework.

## 🌟 Features
*   **Multi-LLM Independence:** Seamlessly switch between external providers and zero-cost local LLMs.
*   **Self-Correcting Execution:** Code is executed in a secure Python sandbox; if CAD generation fails, the error is fed back to the LLM for automatic revision.
*   **100% Client-Side API Keys:** Complete security with keys stored exclusively in local browser storage using AES-GCM encryption.
*   **Instant Export:** Download models as `.STEP` (Parametric CAD format) and `.STL` (3D printing).
*   **Interactive 3D Preview:** Live, glassmorphic WebGL model viewer utilizing `three.js`.

## ⚙️ Quick Start
We recommend using the provided launcher to start the Python backend automatically.

1.  Clone this repository.
2.  Install Python 3.11+.
3.  Double click `start.bat` (Windows) or `./start.ps1`.

The launcher will verify prerequisites, install pip dependencies, start the FastAPI server, auto-start Ollama (if installed locally), and launch the interface in your default browser at http://localhost:8000.

To use the local CLI fallback:
Run `fermeon.bat` in the root folder to access the lightweight terminal prompt.

## 💻 Tech Stack
*   **Frontend:** Vanilla HTML/CSS/JS (Lightweight, blazingly fast, no build step required)
*   **Backend:** FastAPI, Python, CadQuery, LiteLLM
*   **Local AI Engine:** Ollama (qwen2.5-coder:14b parameter size highly recommended)

## 🪪 License
Copyright © 2026 Nilesh Sarkar.

# Fermeon — AI CAD Generator

Fermeon is a multi-LLM application that transforms natural language prompts into manufacturable CAD models (STEP/STL files). It intelligently routes logic through leading models (GPT-4o, Claude 3.5 Sonnet, Gemini 2.0, DeepSeek, Mistral) and local models (Ollama Qwen2.5-Coder) using a highly consistent CadQuery generation framework.

## 🌟 Features
*   **Multi-LLM Independence:** Seamlessly switch between external providers and zero-cost local LLMs.
*   **Self-Correcting Execution:** Code is executed in a secure Python sandbox; if CAD generation fails, the error is fed back to the LLM for automatic revision.
*   **100% Client-Side API Keys:** Complete security with keys stored exclusively in local browser storage using AES-GCM encryption.
*   **Instant Export:** Download models as `.STEP` (Parametric CAD format) and `.STL` (3D printing).
*   **Interactive 3D Preview:** Live, glassmorphic WebGL model viewer utilizing `three.js`.

## ⚙️ Quick Start
We recommend using the provided launcher to start both the Python backend and Next.js frontend automatically.

1.  Clone this repository.
2.  Install Python 3.11+ and Node.js.
3.  Double click `start.bat`.

The launcher will verify prerequisites, install pip/npm dependencies, start both servers, auto-start Ollama (if installed locally), and launch the interface in your default browser.

To use the local CLI fallback:
Run `fermeon.bat` in the root folder to access the lightweight terminal prompt.

## 💻 Tech Stack
*   **Frontend:** Next.js, React, Tailwind CSS, Three.js (React Three Fiber)
*   **Backend:** FastAPI, Python, CadQuery, LiteLLM
*   **Local AI Engine:** Ollama (qwen2.5-coder:14b parameter size highly recommended)

## 🪪 License
Copyright © 2026 Nilesh Sarkar.

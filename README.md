# VetClaim AI 🚀

VetClaim AI is an intelligent assistant designed to help veterans navigate the complex VA disability claims process. It audits existing claim documents using LLMs (specifically Google's Gemini), identifies missing evidence or potential under-ratings based on **38 CFR Part 4**, and automatically fills out the necessary VA appeal forms.

## ✨ Features

- **AI-Powered Audit**: Analyzes DBQs, medical records, and decision letters to find discrepancies.
- **CFR Regulation Mapping**: Cross-references findings with official VA rating criteria.
- **Automatic Form Filling**: Generates ready-to-file PDFs for HLR (20-0996), Supplemental Claims (20-0995), and more.
- **Mock VA Portal**: A demonstration environment to show how data is submitted and received by the VA.
- **Voice Integration**: Experimental VAPI integration for simulated calls with VA representatives.
- **Intelligent Chat**: A specialized advisor that knows the specifics of your case and the relevant regulations.

## 🏗️ Architecture

The project is split into three main components:

1.  **Frontend**: A modern React-based dashboard for veterans.
2.  **Backend**: A Python (Flask) API that orchestrates the document parsing, AI auditing, and form-filling agents.
3.  **Mock VA Portal**: A separate service that simulates the VA's internal systems to demonstrate the end-to-end filing flow.

## 🛠️ Setup Instructions

### Prerequisites
- Python 3.9+
- Node.js & npm
- A Google Gemini API Key

### Backend Setup
1. Navigate to the `backend` directory.
2. Create a `.env` file based on `.env.example`:
   ```bash
   GOOGLE_API_KEY=your_gemini_api_key_here
   VAPI_PRIVATE_KEY=your_vapi_key_optional
   ```
3. Install dependencies:
   ```bash
   pip install -r ../requirements.txt
   ```
4. Start the server:
   ```bash
   python server.py
   ```
   *The backend runs on port 5001.*

### Frontend Setup
1. Navigate to the `frontend` directory.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the dev server:
   ```bash
   npm run dev
   ```
   *The frontend runs on port 5173.*

### Mock VA Portal Setup
1. Navigate to the `mock_va_portal` directory.
2. Start the mock portal server:
   ```bash
   python server.py
   ```
   *The portal runs on port 5050.*

## 📂 Project Structure

- `backend/`: Flask server and AI agents (`auditor_agent`, `parser_agent`, `filer_agent`).
- `frontend/`: React source code and assets.
- `mock_va_portal/`: Simulation environment for VA submission processing.
- `veterans/`: (Ignored) Example data for testing locally.

## 🔥 Quick Start (Helper Script)
You can use the provided `start.sh` script to launch all components simultaneously:
```bash
chmod +x start.sh
./start.sh
```

---

### If `./start.sh` doesn't work, use these manual instructions:

**1. Start the Backend:**
```bash
cd backend
python3 server.py
```

**2. Start the Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**3. Start the Mock VA Portal:**
```bash
cd mock_va_portal
python3 server.py
```

---
*Disclaimer: This tool is for demonstration purposes and is not affiliated with the Department of Veterans Affairs.*

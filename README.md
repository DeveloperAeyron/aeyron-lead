# 🛰️ Lead Radar

A modern, high-performance lead generation dashboard built with **Next.js 15**, **FastAPI**, and **Playwright**. Discover, enrich, and export business leads in real-time with an Aeyron-inspired design aesthetic.

## 🚀 Quick Start (Windows)

The easiest way to start both the backend and frontend is to use the provided launchers in the root directory:

1.  **Windows (CMD)**: Double-click **`run_dev.bat`**
2.  **PowerShell**: Run **`./run_dev.ps1`**
3.  **Bash/Git Bash**: Run **`bash run_dev.sh`**

The scripts will launch:
*   **Backend Server**: Running on `http://localhost:8000`
*   **Frontend Dashboard**: Running on `http://localhost:3000`

## 🔌 Point the frontend at a different backend (e.g. ngrok)

The frontend reads `NEXT_PUBLIC_API_URL` to decide where to call the backend.

- Create `frontend/.env.local` (do not commit it)
- Put your backend URL in it:

```bash
NEXT_PUBLIC_API_URL=https://YOUR-SUBDOMAIN.ngrok-free.app
```

Restart the frontend dev server after changing env vars.

---

## 🛠️ Project Structure

The project is organized into two main components:

*   **/backend**: Python FastAPI server that wraps the Google Maps scraper.
    *   `server.py`: The main API and SSE lead streamer.
    *   `spawn-radius-scraper.py`: The core scraping engine.
    *   `sessions/`: Stores lead data (XLSX/JSON) for every run.
*   **/frontend**: Next.js dashboard with a premium dark-mode interface.
    *   `app/leadhunt`: Real-time scraping control panel.
    *   `app/dashboard`: Session history and stats.
    *   `components/`: Reusable UI components (Sidebar, LeadTable, etc.).

---

## 📦 Manual Setup

### 1. Backend Setup
```bash
python -m venv venv
venv\Scripts\activate
pip install -r backend/requirements.txt
python -m playwright install chromium
```

### 2. Frontend Setup
```bash
cd frontend
npm install
```

### 3. Run Manually
**Backend:**
```bash
cd backend
..\venv\Scripts\python server.py
```

**Frontend:**
```bash
cd frontend
npm run dev
```

---

## 🎨 Features
- **Real-time Streaming**: Leads appear in the dashboard as soon as they are found.
- **Advanced Configuration**: Fine-tune radius, depth, and seed candidates.
- **Collapsible Sidebar**: Maximize workspace with a sleek, interactive navigation.
- **Export System**: Generate XLSX or CSV files with custom website filters.
- **Theme Support**: Premium dark mode with electric cyan accents.

---

## ⚖️ Notes
- **Headed Mode**: The scraper runs in headed mode by default so you can monitor the discovery process.
- **Persistence**: Leads are saved to the `backend/sessions/` directory immediately upon discovery.

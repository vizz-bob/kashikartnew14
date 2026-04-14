# KashiKart — Tender Management Desktop Application

A full-stack Windows desktop application for automated tender discovery and management.

## Project Structure

```
kashikart/
├── Kahiskart-0.0.7-kashikart/   ← Python FastAPI Backend
│   ├── app/                      ← Application source code
│   ├── main.spec                 ← PyInstaller build spec
│   ├── requirements.txt          ← Python dependencies
│   ├── .env.example              ← Environment variable template
│   └── tender_dev.db             ← SQLite database (not committed)
│
├── kashikart-gaurav/             ← React + Electron Frontend
│   ├── src/                      ← React source code
│   ├── electron/                 ← Electron main process
│   ├── public/                   ← Static assets
│   └── package.json              ← Node dependencies + build config
│
└── .github/workflows/
    ├── build-release.yml         ← Auto-build .exe on version tag
    └── build-dev.yml             ← Build check on push/PR
```

## Quick Start (Development)

### Backend
```bash
cd Kahiskart-0.0.7-kashikart
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
cp .env.example .env           # Fill in real values
uvicorn app.main:app --reload
```

### Frontend
```bash
cd kashikart-gaurav
npm install
npm run dev
```

## Building Windows .exe Files

### Option 1: GitHub Actions (Recommended)
Push a version tag to trigger an automated build:
```bash
git tag v1.0.0
git push origin v1.0.0
```
Download the built `.exe` files from the GitHub Release page.

### Option 2: Manual Build on Windows
See `KashiKart_Build_Deployment_Guide.docx` for step-by-step instructions.

## GitHub Secrets Required

Set these in: GitHub repo → Settings → Secrets → Actions

| Secret | Description |
|--------|-------------|
| `SECRET_KEY` | JWT signing key (min 32 chars) |
| `SMTP_USER` | Gmail address for notifications |
| `SMTP_PASSWORD` | Gmail App Password |
| `SMTP_FROM_EMAIL` | From address for emails |

## Stack

| Layer | Technology |
|-------|-----------|
| Backend API | Python 3.11, FastAPI, SQLAlchemy, SQLite |
| Auth | JWT (python-jose), bcrypt (passlib) |
| Scraping | Selenium, Playwright, cloudscraper, BeautifulSoup |
| Scheduler | APScheduler |
| Frontend | React 19, Vite, Tailwind CSS |
| Desktop wrapper | Electron 32 |
| Build (backend) | PyInstaller |
| Build (frontend) | electron-builder (NSIS) |

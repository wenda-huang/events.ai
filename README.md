# events.ai

Pittsburgh meetup map: Next.js client and FastAPI server.

## Run

Backend:

```
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Frontend (also starts the FastAPI backend on port 8000 if it is not already running):

```
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Put Querit, Carto, and OpenRouter keys in `config.ini` at the repo root.

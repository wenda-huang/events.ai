# events.ai

Pittsburgh meetup map: Next.js client and FastAPI server.

## Run

Backend:

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

Frontend:

```
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Put Querit, Carto, and OpenRouter keys in `config.ini` at the repo root.

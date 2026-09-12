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

Open `http://localhost:3000`. Put Querit and Carto keys in `config.ini` at the repo root. Add an OpenAI-compatible key in `.env` if you want the scanner to turn search hits into events.

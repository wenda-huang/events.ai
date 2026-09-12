# events.ai

**Show up to the right room, with the right people.**

events.ai is a local meetup map. Tell it what you’re into, and it surfaces nearby events, recommends ones that fit you, and can invite nearby matches when you host.

## What it does

- **See what’s happening around you.** Browse a live map of meetups in your city. Dial the radius, pick a time window, filter by interests, or search in plain language (“live jazz”, “farmers market”, “pickup basketball”).
- **Get personal recommendations.** After onboarding with your interests and location, the map highlights events you’re most likely to actually want.
- **Host in a few minutes.** Drop an address, set capacity and tags, and publish. The event lands on the map for people nearby.
- **Fill the room automatically.** Turn on auto-invite and nearby people with overlapping interests get a personal invite — not a blast to the whole city.
- **Manage your night.** Join, accept, or decline from My events. Invites explain why you were matched.
- **Keep the map current.** A city-wide scan pulls real-world listings (concerts, markets, workshops, and more) so you’re not staring at an empty calendar.

Live in New York, Los Angeles, Chicago, Houston, Phoenix, Philadelphia, San Antonio, San Diego, Dallas, and Pittsburgh.

## Run it

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

```
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Add keys in `config.ini` at the repo root.

# AdStackr Demo Ad Server

Minimal ad server for demonstrating the decision → impression → click flow.

## Setup

```bash
pip install fastapi uvicorn sqlalchemy
```

## Run

```bash
cd ad-server
uvicorn main:app --reload
```

The server starts on `http://127.0.0.1:8000`. On first boot it creates
`ad_server.db`, builds the schema, and seeds one placement with three creatives.

## Golden Path

```bash
# 1. Request an ad
curl -s "http://127.0.0.1:8000/ad?placement_id=homepage_hero&user_id=user_123" | python -m json.tool

# 2. Copy the impression_url and click_url from the response, then:
curl -s "<impression_url>"
curl -s "<click_url>"

# 3. Inspect what happened
curl -s "http://127.0.0.1:8000/debug/decisions" | python -m json.tool
curl -s "http://127.0.0.1:8000/debug/events"    | python -m json.tool
```

## Endpoints

| Method | Path                | Purpose                       |
|--------|---------------------|-------------------------------|
| GET    | `/ad`               | Serve an ad decision          |
| POST   | `/event/impression` | Log impression (JSON body)    |
| POST   | `/event/click`      | Log click (JSON body)         |
| GET    | `/track/impression` | Tracking-pixel impression     |
| GET    | `/track/click`      | Tracking-pixel click          |
| GET    | `/debug/decisions`  | Last 20 decisions             |
| GET    | `/debug/events`     | Last 50 events                |

Interactive docs at `http://127.0.0.1:8000/docs`.

## File Structure

```
ad-server/
├── main.py        # FastAPI app, routes, startup
├── models.py      # SQLAlchemy models + DB engine
├── schemas.py     # Pydantic request/response models
├── optimizer.py   # Decision logic (swap for real optimizer later)
├── seed.py        # Table creation + seed data
└── README.md
```

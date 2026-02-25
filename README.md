# AfriGov Sentinel

**AI-powered civic incident surveillance system for West Africa**
Built for the [Elasticsearch Agent Builder Hackathon 2026](https://devpost.com/software/afrigov-sentinel)

---

## Architecture

```
Citizen → Frontend (HTML)
              ↓
         FastAPI Backend
          ↙          ↘
  Elasticsearch      Elastic Agent Builder
  (storage +          (AI analysis +
   search +            decision making)
   aggregations)
              ↘
         Response → Citizen
```

## Stack
- **Backend**: FastAPI (Python)
- **Database**: Elasticsearch (Elastic Cloud)
- **AI Brain**: Elastic Agent Builder
- **Frontend**: Vanilla HTML/CSS/JS

## Setup

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/afrigov-sentinel
cd afrigov-sentinel/backend
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp ../.env.example .env
# Edit .env with your Elastic Cloud credentials
```

### 3. Configure Elastic Agent Builder

In Kibana:
1. Go to **Search → Agents → Create Agent**
2. Name it `AfriGov Sentinel`
3. Connect it to your `incidents` index
4. Copy the Agent ID from the URL
5. Add it to `.env` as `ELASTIC_AGENT_ID`

### 4. Seed Data

```bash
python seed_data.py
```

### 5. Run

```bash
uvicorn main:app --reload
```

### 6. Open Frontend

Open `frontend/index.html` in your browser.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/report-incident` | Submit + analyze incident |
| GET | `/incidents` | List all incidents |
| GET | `/stats` | Aggregated statistics |
| GET | `/health` | System health check |

## How It Works

1. Citizen fills out the form and submits an incident
2. Backend indexes it in Elasticsearch
3. Backend searches for similar past incidents
4. Elastic Agent Builder analyzes the incident with full context
5. Agent returns: risk score (0-5), decision, explanation, action plan
6. Decision is logged in `agent_decisions` index
7. Result displayed to citizen in real time
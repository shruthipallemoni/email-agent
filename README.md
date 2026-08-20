# AI Email & Productivity Agent

An AI agent that connects to Gmail, reads and understands emails, and drafts
replies for you to approve before sending.

This project is being built **step by step (in blocks)**. Each block adds one
working piece on top of the last one.

## Progress

- [x] Block 1 — Project foundation
- [ ] Block 2 — Authentication and Google OAuth
- [ ] Block 3 — Gmail API integration
- [ ] Block 4 — PostgreSQL persistence
- [ ] Block 5 — LLM email understanding
- [ ] Block 6 — LangGraph agent
- [ ] Block 7 — Reply generation
- [ ] Block 8 — Reply validation
- [ ] Block 9 — Human-in-the-loop approval
- [ ] Block 10 — Gmail sending

## Project structure

```
email-agent/
├── backend/          # FastAPI server (Python)
│   ├── app/
│   │   ├── api/      # URL routes (endpoints)
│   │   ├── core/     # settings, logging
│   │   ├── models/   # database tables (added in Block 4)
│   │   ├── schemas/  # data shapes for requests/responses
│   │   └── services/ # business logic (Gmail, AI, etc.)
│   └── tests/
├── frontend/         # React + TypeScript dashboard
└── docker-compose.yml # runs the PostgreSQL database locally
```

## How to run it

### 1. Start the database
```bash
docker-compose up -d
```

### 2. Start the backend
```bash
cd backend
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```
Backend will run at: http://localhost:8000
Check it's alive at: http://localhost:8000/api/health

### 3. Start the frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend will run at: http://localhost:5173

If everything is connected correctly, opening the frontend in your browser
should show a green "Connected to backend" message.

### 4. Run backend tests
```bash
cd backend
pytest
```

# The Doorman Game 🎭

A conversational AI social engineering simulator where you try to convince a nightclub doorman to let you in.

## Quick Start

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
echo "VENICE_API_KEY=your-api-key" > .env

# Run server
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## How It Works

- **You**: Try to convince Marcus the doorman to let you into BLVD Dubai
- **Judge Agent**: Hidden AI that scores your persuasiveness (-20 to +20)
- **Doorman Agent**: Marcus responds in character based on your approach
- **Win Condition**: Reach 100 influence points

## Tech Stack

- **Backend**: FastAPI, Python
- **Frontend**: React, Vite
- **AI**: Venice AI API (OpenAI-compatible)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/test-env` | Health check |
| POST | `/chat` | Send message, get response |
| GET | `/session/{id}` | Get session state |
| POST | `/session/reset` | Reset game |


# agenoscope
Diagnose why your AI agents fail. Connect LangSmith or push traces via SDK, get root-cause analysis and safe fix suggestions — with human approval and your own API keys (BYOK).

## 🚀 Quick Start

### Option 1: Using Docker Compose (Recommended)

Start both backend and frontend with a single command:
```bash
docker-compose up --build
```

Access the app at: [http://localhost](http://localhost)

### Option 2: Local Development

#### Backend
```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Create default superuser
python -m app.utils.create_superuser
# Follow prompts to set email/password

# Run server
uvicorn app.main:app --reload
```

Backend will be available at: [http://localhost:8000](http://localhost:8000)
API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

#### Frontend
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend will be available at: [http://localhost:5173](http://localhost:5173)

## 📂 Project Structure

```
agenoscope/
├── backend/             # Python FastAPI backend
│   ├── app/
│   │   ├── api/         # API endpoints
│   │   │   ├── v1/
│   │   │   └── deps.py    # Dependencies (auth, db)
│   │   ├── models/      # SQLAlchemy models
│   │   ├── schemas/     # Pydantic schemas
│   │   ├── core/        # Core modules
│   │   │   ├── config.py  # Configuration
│   │   │   ├── security.py  # Security utils (password, tokens)
│   │   │   └── rate_limit.py  # Rate limiting
│   │   └── main.py      # Application entry point
│   └── requirements.txt
├── frontend/            # React frontend
│   ├── src/
│   │   ├── api/         # API client
│   │   ├── components/  # React components
│   │   ├── pages/       # Page components
│   │   ├── context/     # Auth context
│   │   ├── types/       # TypeScript types
│   │   └── App.tsx      # Main application
│   ├── package.json
│   └── vite.config.ts
├── agenoscope-architecture.md  # System architecture
├── Dockerfile               # Docker configuration
├── docker-compose.yml       # Multi-container setup
└── .gitignore               # Git ignore rules
```

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI
- **Database**: SQLite (default), PostgreSQL (production)
- **ORM**: SQLAlchemy 2.0
- **Security**: JWT, bcrypt
- **Rate Limiting**: Redis-based

### Frontend
- **Framework**: React 18
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Build Tool**: Vite

## 🤝 Contributing

1. Create a feature branch: `git checkout -b feat/your-feature`
2. Make your changes
3. Test thoroughly
4. Submit a pull request

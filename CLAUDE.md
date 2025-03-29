# Fantasy Football Projections - Claude Guide

## Commands
- **Backend**: `cd backend && uvicorn main:app --reload`
- **Frontend**: `cd frontend && npm run dev`
- **Tests**: `cd backend && python -m pytest tests/`
- **Single Test**: `cd backend && python -m pytest tests/path/to/test_file.py::TestClass::test_method -v`
- **Lint (Frontend)**: `npm run lint`
- **Build (Frontend)**: `npm run build`

## Environment
- Python 3.11+ with conda: `conda env create -f backend/environment.yml`
- Activate: `conda activate fantasy-football`

## Code Style Guidelines
- **Python**: 
  - Type hints required for all functions
  - Follow PEP 8 with Black formatting
  - Use explicit exception handling with appropriate logging
  - Async/await pattern for service methods
  
- **TypeScript**:
  - Strict type checking
  - Component props must be typed
  - Use functional components with hooks
  - Follow ESLint + Prettier conventions

## Project Structure
- Backend (FastAPI): API routes, database models, services with business logic
- Frontend (React/TS): Components, services, utilities
- Use absolute imports where possible
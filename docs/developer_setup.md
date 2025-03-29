# Developer Setup Guide

This guide provides comprehensive instructions for setting up the Fantasy Football Projections application for local development.

## Prerequisites

Before you begin, make sure you have the following installed:

- Python 3.11 or higher
- Node.js 18 or higher
- Conda (recommended for environment management)
- Git
- A code editor of your choice (VS Code recommended)

## Backend Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/fantasy-football-projections.git
cd fantasy-football-projections
```

### 2. Create and Activate Conda Environment

```bash
conda env create -f backend/environment.yml
conda activate fantasy-football
```

This will install all the required Python dependencies specified in the `environment.yml` file, including:

- FastAPI
- SQLAlchemy
- Pydantic
- Uvicorn
- Numpy
- Pandas
- Pytest

### 3. Initialize the Database

```bash
python backend/database/init_db.py
```

This script creates the SQLite database and initializes the schema.

### 4. Import Sample Data (Optional)

To populate the database with sample data for development:

```bash
cd backend/scripts
python upload_season.py --season 2024 --verify
```

### 5. Start the Backend Server

```bash
cd backend
uvicorn main:app --reload
```

The backend API will be available at `http://localhost:8000`.

## Frontend Setup

### 1. Install Node Dependencies

```bash
cd frontend
npm install
```

This installs all the required Node.js dependencies specified in `package.json`, including:

- React
- TypeScript
- Vite
- React Router
- shadcn/ui components
- Recharts
- TailwindCSS

### 2. Start the Frontend Development Server

```bash
npm run dev
```

The frontend application will be available at `http://localhost:5173`.

## Development Workflow

### Backend Development

1. **Code Structure**
   - Models are defined in `backend/database/models.py`
   - Business logic is implemented in service classes in `backend/services/`
   - API endpoints are defined in `backend/api/routes/`
   - Schemas are defined in `backend/api/schemas.py`

2. **Running Tests**
   ```bash
   cd backend
   python -m pytest tests/
   ```

3. **Adding a New Endpoint**
   1. Define the request/response schemas in `schemas.py`
   2. Implement business logic in an appropriate service class
   3. Create the endpoint in the relevant route file

4. **Database Migrations**
   Currently, the application uses SQLite with direct schema changes. A formal migration system will be implemented in the future.

### Frontend Development

1. **Code Structure**
   - React components are in `frontend/src/components/`
   - API client is in `frontend/src/services/api.ts`
   - Types are defined in `frontend/src/types/`
   - Utility functions are in `frontend/src/utils/`

2. **Component Development**
   1. Create new React components in the `components` directory
   2. Import and use shadcn/ui components for consistent styling
   3. Use TypeScript interfaces for props and state

3. **Adding a New Page**
   1. Create a new page component in `frontend/src/pages/`
   2. Add the route in `frontend/src/routes.tsx`

4. **Styling**
   - The project uses TailwindCSS for styling
   - Component-specific styles can be added in the `frontend/src/components` directory
   - Global styles are in `frontend/src/style.css`

## Project Configuration

### Environment Variables

The application doesn't currently use environment variables, but a `.env` file structure will be implemented for configuration in future versions.

### TypeScript Configuration

- TypeScript configurations are defined in:
  - `frontend/tsconfig.json` for React application
  - `frontend/tsconfig.node.json` for Vite configuration

### Testing Setup

- Backend testing uses pytest
  - Fixtures are defined in `backend/tests/conftest.py`
  - Unit tests are in `backend/tests/unit/`
  - Integration tests are in `backend/tests/integration/`
  - System tests are in `backend/tests/system/`

- Frontend testing will use Vitest (to be implemented)

## Development Guidelines

### Code Style

#### Python
- Follow PEP 8 guidelines
- Use type hints for all functions
- Document functions and classes with docstrings
- Use Black for formatting

#### TypeScript/React
- Use ESLint with TypeScript rules
- Use Prettier for formatting
- Use functional components with hooks
- Use TypeScript interfaces for props and state

### Git Workflow

1. Create a feature branch from `main`
   ```bash
   git checkout -b feature/name-of-feature
   ```

2. Make changes and commit
   ```bash
   git add .
   git commit -m "Description of changes"
   ```

3. Run tests to ensure everything is working
   ```bash
   cd backend
   python -m pytest tests/
   ```

4. Push the branch and create a pull request
   ```bash
   git push origin feature/name-of-feature
   ```

### Documentation Guidelines

- Update `README.md` for major changes
- Document new API endpoints in `backend/api/docs/README.md`
- Update model documentation in `docs/model.md` for projection algorithm changes
- Comment complex logic with clear explanations

## Troubleshooting

### Common Backend Issues

1. **Database Connection Error**
   - Ensure the database file exists
   - Check file permissions
   - Verify connection string in `database.py`

2. **API Endpoint Errors**
   - Check route definitions
   - Validate request schemas
   - Look for missing dependencies

### Common Frontend Issues

1. **Dependency Issues**
   - Try `npm clean-install` to reinstall all dependencies
   - Check for version conflicts in `package.json`

2. **Build Errors**
   - Check TypeScript errors
   - Verify import paths
   - Look for missing dependencies

3. **API Connection Issues**
   - Ensure backend server is running
   - Check API base URL configuration in `api.ts`
   - Verify CORS settings

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [React Documentation](https://react.dev/)
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)
- [Vite Documentation](https://vitejs.dev/guide/)
- [TailwindCSS Documentation](https://tailwindcss.com/docs)
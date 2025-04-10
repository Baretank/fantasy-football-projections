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

### 4. Setup NFL Data Sources

The application uses the `nfl_data_py` package and official NFL APIs for importing NFL data. We've created a setup script that will verify and install all required dependencies:

```bash
cd backend/scripts
python setup_nfl_data.py
```

This script will:
1. Check if `nfl_data_py` and `aiohttp` packages are installed
2. Update your conda environment if needed
3. Install any missing dependencies
4. Provide instructions for importing NFL data

### 5. Import NFL Data (Optional)

To populate the database with real NFL data for development, you have two options:

#### Option A: Full Import (All At Once)

```bash
cd backend/scripts
python import_nfl_data.py --seasons 2023 --type full
```

This will use the NFLDataImportService to import all data from NFL sources at once. The first run may take some time as it downloads and processes all data for the season.

You can also import specific data types:
```bash
# Import only player data
python import_nfl_data.py --seasons 2023 --type players

# Import only weekly stats
python import_nfl_data.py --seasons 2023 --type weekly

# Import only team stats
python import_nfl_data.py --seasons 2023 --type team

# Calculate season totals from weekly data
python import_nfl_data.py --seasons 2023 --type totals

# Validate imported data
python import_nfl_data.py --seasons 2023 --type validate
```

#### Option B: Position-by-Position Import (Recommended)

For better resource management, especially with large datasets, use the position-based import script:

```bash
# Import team data first
python import_by_position.py --season 2023 --position team

# Import QB data
python import_by_position.py --season 2023 --position QB

# Import RB data
python import_by_position.py --season 2023 --position RB

# Import WR data
python import_by_position.py --season 2023 --position WR

# Import TE data
python import_by_position.py --season 2023 --position TE

# Alternative: Import all positions with one command (still done sequentially)
python import_by_position.py --season 2023 --position all
```

This approach uses less memory, as it processes one position at a time, making it ideal for development environments.

#### Monitoring Import Process

You can monitor the import process through:
1. Console output: Provides real-time feedback during imports
2. Log files: Detailed logs are saved to the `backend/logs` directory
3. Database logging: Import operations are logged to the `import_logs` table
4. Metrics tracking: Request counts, errors, and processing times are tracked

#### Verifying Import Results

After importing data, you can verify what was imported using the check_import.py tool:

```bash
# Basic check
python check_import.py

# Filter by position
python check_import.py --position QB --season 2023

# Check specific player
python check_import.py --player "Patrick Mahomes"

# Show import logs
python check_import.py --logs
```

### 5.1 NFL Data Import Architecture

The NFL data import system uses a modular adapter-based architecture:

1. **Data Source Adapters**:
   - `NFLDataPyAdapter`: Interface to the nfl-data-py Python package
   - `NFLApiAdapter`: Interface to the official NFL API with rate limiting
   - `WebDataAdapter`: For testing and fallback options

2. **Core Import Service**:
   - `NFLDataImportService`: Main service that coordinates data import and processing

3. **API Endpoints**:
   - `/batch/import/nfl-data/{season}`: Full endpoint for importing NFL data
   - Supports background processing of long-running imports

For testing the NFL data import system:
```bash
# Run NFL data-specific tests
python -m pytest "tests/unit/test_nfl_data_import_service.py" -v
python -m pytest "tests/integration/test_nfl_data_integration.py" -v
python -m pytest "tests/system/test_import_projection_flow.py" -v
```

### 6. Start the Backend Server

```bash
cd backend
uvicorn main:app --reload
```

The backend API will be available at `http://localhost:8000` and the interactive API documentation at `http://localhost:8000/docs`.

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
   - Data source adapters are in `backend/services/adapters/`
   - Import services are in `backend/services/`
   - Command-line tools are in `backend/scripts/`

2. **Running Tests**
   ```bash
   # Run all tests
   cd backend
   python -m pytest tests/
   
   # Run specific test categories
   python -m pytest tests/unit/
   python -m pytest tests/integration/
   python -m pytest tests/system/
   
   # Run NFL data import tests specifically
   python -m pytest "tests/unit/test_nfl_data_import_service.py" -v
   python -m pytest "tests/unit/test_external_response_handling.py" -v
   python -m pytest "tests/unit/test_rate_limiting.py" -v
   python -m pytest "tests/unit/test_position_import_accuracy.py" -v
   python -m pytest "tests/integration/test_nfl_data_integration.py" -v
   python -m pytest "tests/system/test_import_projection_flow.py" -v
   
   # Use the run_tests.sh script for specific test categories
   ./tests/system/run_tests.sh import    # Run import-related system tests
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

3. **NFL Data Import Issues**
   - Install required packages with `python setup_nfl_data.py`
   - Check if the nfl-data-py package is installed and working
   - Verify internet connectivity for external API calls
   - Check for rate limiting issues in the console output or logs
   - Examine the import logs in the database for detailed error information
   - For testing issues, ensure test fixtures and mocks are properly set up

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
- [NFL Data PY Documentation](https://pypi.org/project/nfl-data-py/)
- [NFL API Resources](https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c)
- [NFL Fantasy Data Fields Reference](https://api.fantasy.nfl.com/v2/docs)
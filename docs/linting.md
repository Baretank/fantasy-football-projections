# Linting Documentation

This project uses linting tools to maintain code quality and consistency across both the frontend and backend.

## Overview

### Frontend (TypeScript/React)
- **ESLint**: Static code analysis and style enforcement for TypeScript/React

### Backend (Python)
- **flake8**: Code style and syntax checking
- **black**: Automatic code formatting
- **mypy**: Static type checking

## Running Linting Tools

### Frontend

```bash
# Navigate to frontend directory
cd frontend

# Run lint with strict checking (will fail on warnings)
npm run lint

# Run lint with warnings allowed
npm run lint:warn

# Run linting with automatic fixes
npm run lint:fix
```

### Backend

```bash
# Navigate to backend directory
cd backend

# Run flake8 linting
flake8 .

# Run black formatting
black .

# Run mypy type checking
mypy .
```

## Configuration Files

### Frontend
- `.eslintrc.json`: ESLint configuration with rules for TypeScript/React

### Backend
- `.flake8`: Basic configuration excluding certain errors
- `setup.cfg`: Additional configuration
- `pyproject.toml`: Black formatting configuration
- `mypy.ini`: Type checking configuration

## Type Stubs (Python)

The following type stubs are installed to improve type checking:
- `types-psutil`: For system monitoring
- `types-requests`: For HTTP requests
- `types-tabulate`: For pretty printing tabular data
- `pandas-stubs`: For pandas DataFrame operations


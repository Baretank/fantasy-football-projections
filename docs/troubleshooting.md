# Troubleshooting Guide for Fantasy Football Projections App

## Scenarios Functionality

### Common Issues and Solutions

#### 1. Scenarios not appearing in the UI

**Potential causes:**
- Backend server not running
- Database missing scenario data
- API connection issues
- Incorrect endpoint URLs
- IPv6/IPv4 mismatch issues

**Solutions:**
- Check backend server status with: `cd backend && uvicorn main:app --reload`
- Verify scenarios exist in database:
  ```bash
  cd backend
  python -c "from backend.database.database import SessionLocal; from backend.database.models import Scenario; db = SessionLocal(); print([s.name for s in db.query(Scenario).all()])"
  ```
- Create baseline scenarios if none exist:
  ```bash
  cd backend
  python scripts/create_baseline_scenario.py --season 2024 --type all
  ```
- Check browser console for API errors and connection issues
- Verify the API endpoint in the browser network tab (should be `/api/scenarios`)
- Use the `run.py` script to start the backend which explicitly uses IPv4:
  ```bash
  cd backend
  python run.py
  ```

#### 2. Cannot create new scenarios

**Potential causes:**
- Backend validation errors
- Duplicate scenario names
- Missing required fields
- API connectivity issues

**Solutions:**
- Check browser console for specific error messages
- Verify scenario name is unique
- Ensure all required fields are provided in the request
- Check backend logs for detailed validation errors
- Verify Vite proxy configuration in frontend is using IPv4:
  ```typescript
  // frontend/vite.config.ts
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',  // Use explicit IPv4 address
        changeOrigin: true,
        secure: false,
      },
    },
  }
  ```

#### 3. Scenario comparison not working

**Potential causes:**
- No player projections associated with scenarios
- Insufficient data for comparison
- API errors in comparison endpoint

**Solutions:**
- First verify scenarios have projections:
  ```bash
  cd backend
  python -c "from backend.database.database import SessionLocal; from backend.database.models import Projection; db = SessionLocal(); print([p.projection_id for p in db.query(Projection).filter(Projection.scenario_id != None).limit(5).all()])"
  ```
- If no scenario projections exist, populate projections for scenarios:
  ```bash
  cd backend
  python -c "from backend.database.database import SessionLocal; from backend.database.models import Scenario, Projection, Player; db = SessionLocal(); scenario = db.query(Scenario).first(); projections = db.query(Projection).filter(Projection.scenario_id == None).limit(5).all(); for p in projections: new_p = Projection(player_id=p.player_id, scenario_id=scenario.scenario_id, season=p.season, games=p.games, half_ppr=p.half_ppr); db.add(new_p); db.commit(); print('Added', len(projections), 'projections to scenario:', scenario.name)"
  ```
- Check browser network tab for detailed API error information

## Network Connectivity Issues

### IPv6/IPv4 Connection Problems

**Symptoms:**
- "Connection refused" errors in the browser console
- `ECONNREFUSED ::1:8000` errors
- API endpoints work in Postman but not in browser
- Frontend shows empty data with no visible errors

**Solutions:**
1. Explicitly use IPv4 in the backend:
   ```bash
   cd backend
   # Use the run.py script (recommended)
   python run.py
   
   # Or start uvicorn with explicit IPv4
   uvicorn main:app --reload --host 127.0.0.1
   ```

2. Update Vite proxy in frontend to use IPv4:
   ```typescript
   // In frontend/vite.config.ts
   server: {
     proxy: {
       '/api': {
         target: 'http://127.0.0.1:8000',  // Use explicit IPv4 address
         changeOrigin: true,
         secure: false,
       },
     },
   }
   ```

3. Test API connectivity directly:
   ```bash
   # Use the test script
   cd backend
   python scripts/test_api.py
   
   # Or use curl
   curl http://127.0.0.1:8000/api/scenarios
   ```

4. For debugging, use the test-cors.html page:
   ```bash
   # Open the test page in your browser
   open frontend/test-cors.html
   ```

## General Troubleshooting

### Frontend Issues

#### 1. Frontend not connecting to backend

**Solutions:**
- Check that backend is running on port 8000
- Verify proxy settings in `vite.config.ts` are using explicit IPv4:
  ```typescript
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',  // Use explicit IPv4
        changeOrigin: true,
        secure: false,
      },
    },
  }
  ```
- Add credentials to fetch API calls:
  ```typescript
  // In api.ts fetchApi function
  const options: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',  // Important for CORS requests
  };
  ```
- Restart both frontend and backend servers

#### 2. TypeScript errors preventing build

**Solutions:**
- Run `npm run build` to see specific errors
- Address critical type issues first (see bugfixing.md)
- Use type assertions where necessary to bypass non-critical errors

#### 3. Redux DevTools errors

**Solutions:**
- Install Redux DevTools browser extension for proper debugging
- Configure Redux DevTools in store setup code if needed

### Backend Issues

#### 1. Database connection errors

**Solutions:**
- Verify SQLite database file exists in correct location
- Check database connection string in `database.py`
- Run database initialization script if needed:
  ```bash
  cd backend
  python -c "from backend.database.database import Base, engine; Base.metadata.create_all(bind=engine)"
  ```

#### 2. API endpoint 404 errors

**Solutions:**
- Check route configuration in FastAPI app
- Verify route path in browser matches backend implementation
- Use a tool like curl to test API endpoints directly:
  ```bash
  curl http://localhost:8000/api/scenarios
  ```
- Check route order in FastAPI app (parameterized routes like `/{player_id}` can capture static routes like `/rookies` if ordered incorrectly)

#### 3. Data import issues

**Solutions:**
- Run data import scripts manually:
  ```bash
  cd backend
  python scripts/import_nfl_data.py --seasons 2024 --type full
  ```
- Check logs for detailed error information during import
- Use position-by-position import for better memory management:
  ```bash
  python scripts/import_by_position.py --season 2024 --position all
  ```
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
  - Use ESLint with TypeScript rules
  - Prettier for formatting
  - Strict TypeScript checks enabled
  - Functional components with hooks

## SQLAlchemy Operations
- **Query Examples**:
  ```python
  # Basic querying
  players = db.query(Player).filter(Player.position == "QB").all()
  
  # Join example
  projections = db.query(Projection).join(Player).filter(Player.team == "KC").all()
  
  # Complex filtering
  stats = db.query(BaseStat).filter(
      and_(BaseStat.player_id == player_id, BaseStat.season == season)
  ).all()
  ```

- **Async Pattern**:
  ```python
  async def get_projection(self, projection_id: str) -> Optional[Projection]:
      """Retrieve a specific projection."""
      return self.db.query(Projection).filter(Projection.projection_id == projection_id).first()
      
  # Call with await
  projection = await projection_service.get_projection(projection_id)
  ```

- **Transaction Pattern**:
  ```python
  try:
      # Database operations
      self.db.add(new_object)
      self.db.commit()
      return new_object
  except Exception as e:
      self.db.rollback()
      logger.error(f"Error: {str(e)}")
      return None
  ```

## Testing Guidelines
- **Test Fixtures**:
  ```python
  @pytest.fixture(scope="function")
  def sample_players(test_db):
      """Create sample players for testing."""
      players = [
          Player(
              player_id=str(uuid.uuid4()),
              name="Patrick Mahomes",
              team="KC",
              position="QB"
          ),
          # More players...
      ]
      
      for player in players:
          test_db.add(player)
      test_db.commit()
      
      return {"players": players, "ids": {p.name: p.player_id for p in players}}
  ```

- **Mocking Database**:
  ```python
  @pytest.mark.asyncio
  async def test_service_with_mock_db(mocker):
      # Mock the database session
      mock_db = mocker.MagicMock()
      
      # Configure mock returns
      mock_query = mocker.MagicMock()
      mock_filter = mocker.MagicMock()
      mock_filter.first.return_value = Player(name="Test Player", team="KC", position="QB")
      mock_query.filter.return_value = mock_filter
      mock_db.query.return_value = mock_query
      
      # Create service with mock db
      service = DataService(mock_db)
      
      # Test method
      result = await service.get_player("test_id")
      assert result.name == "Test Player"
  ```

## TypeScript Type Definitions
- **Data Interfaces**:
  ```typescript
  // Player types
  interface Player {
    player_id: string;
    name: string;
    team: string;
    position: 'QB' | 'RB' | 'WR' | 'TE';
    created_at: string;
    updated_at: string;
  }
  
  // Projection types
  interface Projection {
    projection_id: string;
    player_id: string;
    scenario_id?: string;
    season: number;
    games: number;
    half_ppr: number;
    
    // Position-specific stats
    pass_attempts?: number;
    completions?: number;
    pass_yards?: number;
    // (other stats...)
  }
  ```

- **Component Props**:
  ```typescript
  // Component prop types
  interface StatsDisplayProps {
    playerId: string;
    position: 'QB' | 'RB' | 'WR' | 'TE';
    season: number;
  }
  
  interface ProjectionAdjusterProps {
    projection: Projection;
    onSave: (adjustments: Adjustments) => Promise<void>;
  }
  ```

## Development Workflows
### Database Changes
1. Update model in `backend/database/models.py`
2. Add migration if needed (using Alembic)
3. Update services to use new field/model
4. Add/update API schema in `backend/api/schemas.py`
5. Test with actual database before committing

### Frontend Component Development
1. Define TypeScript interfaces for the component
2. Create component file with proper props typing
3. Implement component logic with React hooks
4. Connect to API services via fetch/axios
5. Add styling using TailwindCSS
6. Test component in isolation before integration

### API Testing Workflow
1. Start backend server: `cd backend && uvicorn main:app --reload`
2. Use Swagger UI: http://localhost:8000/docs
3. Test endpoints with appropriate payloads
4. Verify responses match expected schemas
5. Add unit tests for new functionality

## Project Conventions
### Naming Conventions
- **Services**: Suffix with `Service`, e.g. `ProjectionService`
- **Routes**: Group by resource in separate router files
- **Models**: PascalCase singular nouns, e.g. `Player`, `Projection`
- **Database IDs**: Use UUIDs, not sequential integers
- **API Schemas**: Suffix with purpose, e.g. `PlayerResponse`, `ProjectionRequest`

### Error Handling Patterns
- **Backend**:
  - Use explicit exception types (`ProjectionError`, etc.)
  - Wrap service methods in try/except blocks
  - Log errors with context before re-raising
  - Return meaningful HTTP status codes and error messages

- **Frontend**:
  - Use try/catch for API calls
  - Provide user-friendly error messages
  - Log detailed errors to console
  - Display appropriate UI for error states (toast, inline error, etc.)

### State Management
- Use React hooks for component state
- Context API for shared state across components
- Custom hooks for reusable logic
- Fetch API for data retrieval with proper error handling

## Project Structure

```
fantasy-football-projections/
├── backend/                 # Python FastAPI backend
│   ├── api/                 # API routes and schemas
│   │   └── routes/          # API endpoint definitions
│   ├── database/            # Database models and connection
│   ├── services/            # Business logic and data processing
│   └── tests/               # Backend tests
├── frontend/                # React + TypeScript frontend
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── services/        # API client and data services
│   │   └── utils/           # Helper functions
│   └── public/              # Static assets
└── data/                    # Local database and data files
```
```
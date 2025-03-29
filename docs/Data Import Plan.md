This is an excellent analysis of your Excel-based fantasy football projections model. Comparing it to your current Python codebase, I can see both strengths in your existing implementation and opportunities for enhancement based on this model analysis.
Strengths in Your Current Python Implementation

Solid Database Structure: Your SQLAlchemy models in models.py already address most of the core entities (Player, TeamStat, BaseStat, Projection, GameStats). The structure is well-designed for storing the data.
Service-Based Architecture: The separation of concerns with DataService, ProjectionService, and TeamStatsService is excellent and aligns well with the model's complexity.
Basic Projection Pipeline: The ProjectionService already implements the fundamental projection calculation logic with position-specific handling.

Key Gaps to Address

Enhanced Statistical Variables: Your current model is missing several of the refined statistical metrics from your Excel model:

Sack tracking and net passing yards
Fumble tracking and net rushing yards
More granular efficiency metrics (TD%, INT%, Sack%, etc.)


Manual Override System: There's no equivalent to your Excel model's override system that tracks:

Original calculated values
Manual override values
Override flags


Fill Player System: Your current implementation doesn't have the automatic reconciliation system to ensure team-level stats match the sum of player stats.
Regression Analysis: The sophisticated regression system (z-scores, variable regression rates) is largely absent from the current code.

Implementation Recommendations
1. Enhance the Data Models
pythonCopy# Add to models.py - Projection class
class Projection(Base):
    # Existing fields...
    
    # Enhanced passing stats
    gross_pass_yards = Column(Float)
    sacks = Column(Float)
    sack_yards = Column(Float)
    net_pass_yards = Column(Float)
    pass_td_rate = Column(Float)
    int_rate = Column(Float)
    sack_rate = Column(Float)
    
    # Enhanced rushing stats
    gross_rush_yards = Column(Float)
    fumbles = Column(Float)
    fumble_rate = Column(Float)
    net_rush_yards = Column(Float)
    rush_td_rate = Column(Float)
    
    # Efficiency metrics
    att_pct = Column(Float)  # % of team pass attempts
    comp_pct = Column(Float)  # completion percentage
    yards_per_att = Column(Float)  # gross YPA
    net_yards_per_att = Column(Float)  # net YPA
    car_pct = Column(Float)  # % of team rush attempts
    yards_per_carry = Column(Float)  # gross YPC
    net_yards_per_carry = Column(Float)  # net YPC
    tar_pct = Column(Float)  # % of team targets
    catch_pct = Column(Float)  # catch rate
    yards_per_target = Column(Float)  # YPT
    rec_td_rate = Column(Float)  # TD% on targets
    
    # Override tracking
    is_manual_override = Column(Boolean, default=False)
    
    # Fill player flag
    is_fill_player = Column(Boolean, default=False)
2. Create a Manual Override System
pythonCopyclass ManualOverride(Base):
    """Track manual overrides to projection values"""
    __tablename__ = "manual_overrides"
    
    override_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    projection_id = Column(String, ForeignKey("projections.projection_id"))
    field_name = Column(String, nullable=False)  # Name of overridden field
    calculated_value = Column(Float)  # Original calculated value
    manual_value = Column(Float)  # User-specified value
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    projection = relationship("Projection", back_populates="overrides")
3. Implement the Fill Player System
pythonCopyasync def generate_fill_players(self, team: str, season: int) -> List[Projection]:
    """Generate fill players to ensure team stats match player stats."""
    # Get team stats
    team_stats = await self.get_team_stats(team, season)
    if not team_stats:
        return []
        
    fill_players = []
    
    # Process each position
    for position in ['QB', 'RB', 'WR', 'TE']:
        # Get all projections for this team/position
        player_projections = await self.get_player_projections(
            team=team, 
            position=position,
            season=season,
            exclude_fill=True
        )
        
        # Calculate position totals from existing players
        position_totals = self._sum_position_stats(player_projections)
        
        # Calculate team position allocation based on historical norms
        team_position_alloc = self._get_team_position_allocation(
            team_stats, position
        )
        
        # Calculate fill player stats (team alloc - player sum)
        fill_stats = self._calculate_fill_stats(
            team_position_alloc, position_totals
        )
        
        # Create fill player if needed
        if self._needs_fill_player(fill_stats):
            fill_player = await self._create_fill_player(
                team, position, season, fill_stats
            )
            fill_players.append(fill_player)
    
    return fill_players
4. Implement Advanced Regression Analysis
pythonCopyasync def apply_regression_analysis(
    self, player_id: str, efficiency_metrics: Dict[str, float]
) -> Dict[str, float]:
    """Apply statistical regression to player efficiency metrics."""
    # Get player info
    player = await self.get_player(player_id)
    if not player:
        return efficiency_metrics
    
    # Get historical data for this position
    historical_data = await self._get_position_historical_data(player.position)
    
    regressed_metrics = {}
    
    # Process each efficiency metric
    for metric, value in efficiency_metrics.items():
        # Calculate league average and standard deviation
        league_avg = historical_data[metric].mean()
        league_std = historical_data[metric].std()
        
        # Calculate z-score
        if league_std > 0:
            z_score = (value - league_avg) / league_std
        else:
            z_score = 0
            
        # Apply regression based on z-score magnitude
        regression_factor = self._get_regression_factor(z_score)
        
        # Apply position-specific adjustments
        regression_factor = self._adjust_for_position(
            regression_factor, player.position, metric
        )
        
        # Calculate regressed value
        regressed_value = league_avg + ((value - league_avg) * regression_factor)
        regressed_metrics[metric] = regressed_value
    
    return regressed_metrics
5. Enhanced Calculation Methods
pythonCopydef _calculate_fantasy_points(self, projection: Projection) -> float:
    """Calculate half-PPR fantasy points with enhanced accuracy."""
    points = 0.0
    
    # Passing points
    if projection.net_pass_yards:  # Use net passing yards
        points += (projection.net_pass_yards / 25.0)  # 0.04 points per passing yard
    if projection.pass_td:
        points += (projection.pass_td * 4.0)
    if projection.interceptions:
        points -= (projection.interceptions * 2.0)
        
    # Rushing points
    if projection.net_rush_yards:  # Use net rushing yards
        points += (projection.net_rush_yards / 10.0)  # 0.1 points per rushing yard
    if projection.rush_td:
        points += (projection.rush_td * 6.0)
    
    # Fumble penalty
    if projection.fumbles:
        points -= (projection.fumbles * 2.0)
        
    # Receiving points
    if projection.receptions:
        points += (projection.receptions * 0.5)  # Half PPR
    if projection.rec_yards:
        points += (projection.rec_yards / 10.0)  # 0.1 points per receiving yard
    if projection.rec_td:
        points += (projection.rec_td * 6.0)
        
    return points
Integration Strategy
To integrate these new features with your existing codebase:

Phased Enhancement:

First, enhance data models to support all metrics
Second, implement manual override tracking
Third, add the fill player system
Finally, add advanced regression analysis


Database Migration:

Create an Alembic migration to add new fields
Ensure backward compatibility with existing data


Service Enhancements:

Extend ProjectionService to handle advanced calculations
Create a new RegressionService for statistical analysis
Add ManualOverrideService to manage overrides


UI Considerations:

Add UI elements to show/edit manual overrides
Display fill player statistics
Visualize regression impacts



Final Assessment
Your Excel model is more sophisticated than your current Python implementation, particularly in:

Statistical thoroughness (handling net yards, fumbles, sacks)
Reconciliation mechanisms (fill players)
Regression analysis
Manual override tracking

However, your Python architecture is solid and well-positioned to incorporate these additional features. The service-based approach with clear separation of concerns will make these enhancements straightforward to implement.

# Fantasy Football Projections System: Implementation Plan

## Overview

This implementation plan outlines the development roadmap for transforming the current Python-based fantasy football projections system to match the sophistication of the Excel model while adding robust manual override capabilities. The plan is structured into phases with clear milestones, focusing first on core functionality and gradually incorporating advanced features.

## Phase 1: Database Schema Enhancement (2 weeks)

### 1.1 Extend Base Models (Week 1)
- Update `models.py` to include enhanced statistical tracking:
  - Add sack and fumble tracking fields
  - Add efficiency metrics (TD%, INT%, Sack%, etc.)
  - Add net yardage calculations
  - Add status fields for manual overrides

```python
# Projection model enhancements
class Projection(Base):
    # Existing fields...
    
    # Enhanced passing stats
    gross_pass_yards = Column(Float)
    sacks = Column(Float)
    sack_yards = Column(Float)
    net_pass_yards = Column(Float)
    pass_td_rate = Column(Float)
    int_rate = Column(Float)
    sack_rate = Column(Float)
    
    # Enhanced rushing stats
    gross_rush_yards = Column(Float)
    fumbles_lost = Column(Float)
    fumble_rate = Column(Float)
    net_rush_yards = Column(Float)
    rush_td_rate = Column(Float)
    
    # Efficiency metrics
    pass_att_pct = Column(Float)  # % of team pass attempts
    comp_pct = Column(Float)      # completion percentage
    yards_per_att = Column(Float) # gross YPA
    net_yards_per_att = Column(Float) # net YPA
    car_pct = Column(Float)       # % of team rush attempts
    yards_per_carry = Column(Float) # gross YPC
    net_yards_per_carry = Column(Float) # net YPC
    tar_pct = Column(Float)       # % of team targets
    catch_pct = Column(Float)     # catch rate
    yards_per_target = Column(Float) # YPT
    rec_td_rate = Column(Float)   # TD% on targets
    
    # Override tracking
    has_overrides = Column(Boolean, default=False)
    is_fill_player = Column(Boolean, default=False)
```

### 1.2 Create Override Models (Week 1)
- Implement models for tracking manual overrides and adjustments

```python
class StatOverride(Base):
    __tablename__ = "stat_overrides"
    
    override_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    player_id = Column(String, ForeignKey("players.player_id"))
    projection_id = Column(String, ForeignKey("projections.projection_id"))
    stat_name = Column(String, nullable=False)
    calculated_value = Column(Float, nullable=False)
    manual_value = Column(Float, nullable=False)
    notes = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    player = relationship("Player", back_populates="stat_overrides")
    projection = relationship("Projection", back_populates="stat_overrides")
```

### 1.3 Create Scenario Models (Week 2)
- Implement models for projection scenarios

```python
class ProjectionScenario(Base):
    __tablename__ = "projection_scenarios"
    
    scenario_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(String)
    is_baseline = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    projections = relationship("Projection", back_populates="scenario")
```

### 1.4 Set Up Migrations (Week 2)
- Create Alembic migrations for schema changes
- Test migration on development database
- Verify data integrity after migration

## Phase 2: Core Service Layer Implementation (3 weeks)

### 2.1 Enhanced ProjectionService (Week 1)
- Update calculation methods to use enhanced metrics
- Implement position-specific projection formulas

```python
async def _calculate_qb_stats(self, player: Player, team_stats: TeamStat) -> Dict[str, float]:
    """Calculate QB-specific projection stats with enhanced metrics."""
    # Get efficiency metrics
    pass_att_pct = await self._get_efficiency_metric(player.player_id, "pass_att_pct", 0.95)
    comp_pct = await self._get_efficiency_metric(player.player_id, "comp_pct", 0.65)
    yards_per_att = await self._get_efficiency_metric(player.player_id, "yards_per_att", 7.2)
    td_rate = await self._get_efficiency_metric(player.player_id, "pass_td_rate", 0.045)
    int_rate = await self._get_efficiency_metric(player.player_id, "int_rate", 0.025)
    sack_rate = await self._get_efficiency_metric(player.player_id, "sack_rate", 0.06)
    
    # Calculate volume stats
    games = 17  # Full season
    pass_attempts = team_stats.pass_attempts * games * pass_att_pct
    completions = pass_attempts * comp_pct
    gross_pass_yards = pass_attempts * yards_per_att
    pass_tds = pass_attempts * td_rate
    interceptions = pass_attempts * int_rate
    
    # Calculate sacks
    dropbacks = pass_attempts / (1 - sack_rate)
    sacks = dropbacks * sack_rate
    sack_yards = sacks * 7  # Average sack yards loss
    
    # Calculate net passing yards
    net_pass_yards = gross_pass_yards - sack_yards
    
    return {
        "pass_attempts": pass_attempts,
        "completions": completions,
        "gross_pass_yards": gross_pass_yards,
        "sacks": sacks,
        "sack_yards": sack_yards,
        "net_pass_yards": net_pass_yards,
        "pass_td": pass_tds,
        "interceptions": interceptions
    }
```

### 2.2 Implement OverrideService (Week 2)
- Create service for managing manual overrides
- Implement CRUD operations for overrides
- Handle recalculation of dependent stats

```python
class OverrideService:
    def __init__(self, db: Session):
        self.db = db
        
    async def create_stat_override(
        self, player_id: str, projection_id: str, 
        stat_name: str, manual_value: float, notes: str = None
    ) -> StatOverride:
        """Create a new stat override."""
        # Get projection to get original value
        projection = self.db.query(Projection).get(projection_id)
        if not projection:
            raise ValueError(f"Projection {projection_id} not found")
            
        # Get calculated value
        calculated_value = getattr(projection, stat_name, None)
        if calculated_value is None:
            raise ValueError(f"Invalid stat name: {stat_name}")
            
        # Create override
        override = StatOverride(
            player_id=player_id,
            projection_id=projection_id,
            stat_name=stat_name,
            calculated_value=calculated_value,
            manual_value=manual_value,
            notes=notes
        )
        
        self.db.add(override)
        self.db.commit()
        
        # Mark projection as having overrides
        projection.has_overrides = True
        self.db.commit()
        
        return override
    
    async def get_player_overrides(self, player_id: str) -> List[StatOverride]:
        """Get all overrides for a player."""
        return self.db.query(StatOverride).filter(
            StatOverride.player_id == player_id
        ).all()
    
    async def apply_overrides_to_projection(self, projection: Projection) -> Projection:
        """Apply all applicable overrides to a projection."""
        # Get overrides for this projection
        overrides = self.db.query(StatOverride).filter(
            StatOverride.projection_id == projection.projection_id
        ).all()
        
        # Apply each override
        for override in overrides:
            setattr(projection, override.stat_name, override.manual_value)
            
        # Recalculate dependent stats
        await self._recalculate_dependent_stats(projection)
        
        return projection
    
    async def _recalculate_dependent_stats(self, projection: Projection) -> None:
        """Recalculate stats dependent on overridden values."""
        # Implementation will depend on field relationships
        pass
```

### 2.3 Implement ScenarioService (Week 3)
- Create service for managing projection scenarios
- Implement methods for creating and applying scenarios

```python
class ScenarioService:
    def __init__(self, db: Session):
        self.db = db
        self.projection_service = ProjectionService(db)
        self.override_service = OverrideService(db)
        
    async def create_scenario(self, name: str, description: str = None) -> ProjectionScenario:
        """Create a new projection scenario."""
        scenario = ProjectionScenario(
            name=name,
            description=description
        )
        
        self.db.add(scenario)
        self.db.commit()
        
        return scenario
    
    async def clone_scenario(
        self, source_scenario_id: str, new_name: str, new_description: str = None
    ) -> ProjectionScenario:
        """Clone an existing scenario with all its projections and overrides."""
        # Implementation
        pass
    
    async def get_scenario_projections(
        self, scenario_id: str, position: Optional[str] = None
    ) -> List[Projection]:
        """Get all projections for a scenario with optional position filter."""
        query = self.db.query(Projection).filter(Projection.scenario_id == scenario_id)
        
        if position:
            query = query.join(Player).filter(Player.position == position)
            
        return query.all()
```

### 2.4 Fill Player System (Week 3)
- Implement system for auto-generating fill players

```python
async def generate_fill_players(
    self, team: str, season: int, scenario_id: str = None
) -> List[Projection]:
    """Generate fill players to reconcile team and player projections."""
    team_stats = await self.team_stat_service.get_team_stats(team, season)
    if not team_stats:
        logger.error(f"No team stats found for {team} in {season}")
        return []
        
    fill_players = []
    
    # Process each position
    for position in ["QB", "RB", "WR", "TE"]:
        # Calculate position totals (without existing fill players)
        position_totals = await self._get_position_totals(team, position, season, scenario_id)
        
        # Calculate expected team position allocation
        team_position_alloc = self._calculate_team_position_allocation(team_stats, position)
        
        # Calculate difference (what fill player needs to provide)
        fill_stats = {}
        for stat, team_total in team_position_alloc.items():
            player_total = position_totals.get(stat, 0)
            fill_stats[stat] = max(0, team_total - player_total)
        
        # Create fill player if needed
        if self._needs_fill_player(fill_stats):
            fill_player = await self._create_fill_player(team, position, season, fill_stats, scenario_id)
            fill_players.append(fill_player)
    
    return fill_players
```

## Phase 3: API Endpoint Implementation (2 weeks)

### 3.1 Override API Endpoints (Week 1)
- Implement REST endpoints for override operations

```python
@router.post(
    "/overrides",
    response_model=OverrideResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_override(
    request: OverrideRequest,
    db: Session = Depends(get_db)
):
    """Create a new stat override."""
    override_service = OverrideService(db)
    try:
        override = await override_service.create_stat_override(
            player_id=request.player_id,
            projection_id=request.projection_id,
            stat_name=request.stat_name,
            manual_value=request.manual_value,
            notes=request.notes
        )
        return override
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get(
    "/overrides/player/{player_id}",
    response_model=List[OverrideResponse]
)
async def get_player_overrides(
    player_id: str,
    db: Session = Depends(get_db)
):
    """Get all overrides for a player."""
    override_service = OverrideService(db)
    return await override_service.get_player_overrides(player_id)
```

### 3.2 Scenario API Endpoints (Week 1)
- Implement REST endpoints for scenario operations

```python
@router.post(
    "/scenarios",
    response_model=ScenarioResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_scenario(
    request: ScenarioRequest,
    db: Session = Depends(get_db)
):
    """Create a new projection scenario."""
    scenario_service = ScenarioService(db)
    scenario = await scenario_service.create_scenario(
        name=request.name,
        description=request.description
    )
    return scenario

@router.get(
    "/scenarios/{scenario_id}/projections",
    response_model=List[ProjectionResponse]
)
async def get_scenario_projections(
    scenario_id: str,
    position: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get projections for a scenario."""
    scenario_service = ScenarioService(db)
    return await scenario_service.get_scenario_projections(scenario_id, position)
```

### 3.3 Enhanced Projection Endpoints (Week 2)
- Update projection endpoints to include override capabilities

```python
@router.post(
    "/projections/with-overrides",
    response_model=ProjectionResponse
)
async def generate_projection_with_overrides(
    request: ProjectionWithOverridesRequest,
    db: Session = Depends(get_db)
):
    """Generate a projection with overrides applied."""
    projection_service = ProjectionService(db)
    override_service = OverrideService(db)
    
    # Generate base projection
    projection = await projection_service.create_base_projection(
        player_id=request.player_id,
        season=request.season
    )
    
    # Apply overrides
    if request.overrides:
        for stat_name, value in request.overrides.items():
            await override_service.create_stat_override(
                player_id=request.player_id,
                projection_id=projection.projection_id,
                stat_name=stat_name,
                manual_value=value
            )
        
        # Apply overrides and recalculate
        projection = await override_service.apply_overrides_to_projection(projection)
    
    return projection
```

### 3.4 Batch Operation Endpoints (Week 2)
- Implement endpoints for batch operations

```python
@router.post(
    "/overrides/batch",
    response_model=BatchOverrideResponse
)
async def create_batch_overrides(
    request: BatchOverrideRequest,
    db: Session = Depends(get_db)
):
    """Apply the same override to multiple players."""
    override_service = OverrideService(db)
    projection_service = ProjectionService(db)
    
    results = []
    for player_id in request.player_ids:
        try:
            # Get latest projection for player
            projection = await projection_service.get_latest_projection(player_id)
            if not projection:
                results.append({
                    "player_id": player_id,
                    "success": False,
                    "message": "No projection found"
                })
                continue
                
            # Create override
            override = await override_service.create_stat_override(
                player_id=player_id,
                projection_id=projection.projection_id,
                stat_name=request.stat_name,
                manual_value=request.value
            )
            
            results.append({
                "player_id": player_id,
                "success": True,
                "override_id": override.override_id
            })
            
        except Exception as e:
            results.append({
                "player_id": player_id,
                "success": False,
                "message": str(e)
            })
    
    return {"results": results}
```

## Phase 4: Frontend Implementation (4 weeks)

### 4.1 Basic Override UI (Week 1-2)
- Implement UI for viewing and editing player projections
- Add override functionality to the UI

```typescript
// React component for player projection with override capability
const PlayerProjectionEditor = ({ playerId, onSave }) => {
  const [projection, setProjection] = useState(null);
  const [overrides, setOverrides] = useState({});
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    // Fetch player projection
    const fetchProjection = async () => {
      setLoading(true);
      try {
        const data = await api.getLatestProjection(playerId);
        setProjection(data);
        // Initialize overrides with current values
        const initialOverrides = {};
        Object.keys(data).forEach(key => {
          if (typeof data[key] === 'number') {
            initialOverrides[key] = data[key];
          }
        });
        setOverrides(initialOverrides);
      } catch (error) {
        console.error("Failed to fetch projection", error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchProjection();
  }, [playerId]);
  
  const handleOverrideChange = (stat, value) => {
    setOverrides({
      ...overrides,
      [stat]: value
    });
  };
  
  const saveOverrides = async () => {
    // Compare and only send actual overrides
    const changedOverrides = {};
    Object.keys(overrides).forEach(key => {
      if (projection[key] !== overrides[key]) {
        changedOverrides[key] = overrides[key];
      }
    });
    
    if (Object.keys(changedOverrides).length === 0) {
      return; // No changes
    }
    
    try {
      const result = await api.saveOverrides(playerId, projection.projection_id, changedOverrides);
      onSave && onSave(result);
    } catch (error) {
      console.error("Failed to save overrides", error);
    }
  };
  
  if (loading) {
    return <div>Loading...</div>;
  }
  
  return (
    <div className="projection-editor">
      <h2>{projection.player?.name} - {projection.player?.team}</h2>
      
      <div className="projection-sections">
        <div className="section">
          <h3>Passing</h3>
          <div className="stat-row">
            <label>Pass Attempts</label>
            <input 
              type="number" 
              value={overrides.pass_attempts || 0} 
              onChange={(e) => handleOverrideChange('pass_attempts', parseFloat(e.target.value))}
            />
            {projection.pass_attempts !== overrides.pass_attempts && (
              <span className="override-indicator">Modified</span>
            )}
          </div>
          {/* More passing stats */}
        </div>
        
        {/* Rushing section */}
        {/* Receiving section */}
      </div>
      
      <button onClick={saveOverrides}>Save Overrides</button>
    </div>
  );
};
```

### 4.2 Scenario Management UI (Week 2-3)
- Implement UI for creating and managing scenarios
- Add ability to compare scenarios

```typescript
const ScenarioManager = () => {
  const [scenarios, setScenarios] = useState([]);
  const [activeScenario, setActiveScenario] = useState(null);
  const [newScenarioName, setNewScenarioName] = useState('');
  
  useEffect(() => {
    // Fetch scenarios
    const fetchScenarios = async () => {
      try {
        const data = await api.getScenarios();
        setScenarios(data);
        if (data.length > 0) {
          setActiveScenario(data[0]);
        }
      } catch (error) {
        console.error("Failed to fetch scenarios", error);
      }
    };
    
    fetchScenarios();
  }, []);
  
  const createScenario = async () => {
    if (!newScenarioName.trim()) return;
    
    try {
      const newScenario = await api.createScenario({
        name: newScenarioName,
        description: ''
      });
      
      setScenarios([...scenarios, newScenario]);
      setNewScenarioName('');
    } catch (error) {
      console.error("Failed to create scenario", error);
    }
  };
  
  const cloneScenario = async (scenarioId) => {
    try {
      const sourceScenario = scenarios.find(s => s.scenario_id === scenarioId);
      if (!sourceScenario) return;
      
      const newScenario = await api.cloneScenario(scenarioId, {
        name: `Copy of ${sourceScenario.name}`,
        description: sourceScenario.description
      });
      
      setScenarios([...scenarios, newScenario]);
    } catch (error) {
      console.error("Failed to clone scenario", error);
    }
  };
  
  return (
    <div className="scenario-manager">
      <div className="scenario-list">
        <h2>Projection Scenarios</h2>
        <ul>
          {scenarios.map(scenario => (
            <li 
              key={scenario.scenario_id}
              className={activeScenario?.scenario_id === scenario.scenario_id ? 'active' : ''}
              onClick={() => setActiveScenario(scenario)}
            >
              {scenario.name}
              <button onClick={() => cloneScenario(scenario.scenario_id)}>Clone</button>
            </li>
          ))}
        </ul>
        
        <div className="new-scenario">
          <input 
            type="text" 
            value={newScenarioName} 
            onChange={(e) => setNewScenarioName(e.target.value)}
            placeholder="New scenario name"
          />
          <button onClick={createScenario}>Create</button>
        </div>
      </div>
      
      {activeScenario && (
        <div className="scenario-details">
          <h2>{activeScenario.name}</h2>
          <p>{activeScenario.description}</p>
          
          {/* Scenario projections component */}
        </div>
      )}
    </div>
  );
};
```

### 4.3 Batch Override UI (Week 3)
- Implement UI for batch operations

```typescript
const BatchOverridePanel = () => {
  const [selectedPlayers, setSelectedPlayers] = useState([]);
  const [statToOverride, setStatToOverride] = useState('');
  const [overrideValue, setOverrideValue] = useState('');
  const [overrideType, setOverrideType] = useState('absolute'); // 'absolute', 'percentage', 'increment'
  
  const applyBatchOverride = async () => {
    if (!statToOverride || !overrideValue || selectedPlayers.length === 0) {
      return;
    }
    
    try {
      // For each player, fetch current projection, calculate new value, apply override
      for (const playerId of selectedPlayers) {
        const projection = await api.getLatestProjection(playerId);
        
        let newValue = parseFloat(overrideValue);
        if (overrideType === 'percentage') {
          // Apply percentage change
          newValue = projection[statToOverride] * (1 + newValue / 100);
        } else if (overrideType === 'increment') {
          // Add/subtract value
          newValue = projection[statToOverride] + newValue;
        }
        
        // Create override
        await api.createOverride({
          player_id: playerId,
          projection_id: projection.projection_id,
          stat_name: statToOverride,
          manual_value: newValue
        });
      }
      
      // Show success notification
      
    } catch (error) {
      console.error("Failed to apply batch override", error);
      // Show error notification
    }
  };
  
  return (
    <div className="batch-override-panel">
      <h2>Batch Override</h2>
      
      <div className="player-selector">
        <PlayerSearchMulti onSelect={setSelectedPlayers} />
        <div>{selectedPlayers.length} players selected</div>
      </div>
      
      <div className="override-controls">
        <div className="form-group">
          <label>Stat to Override</label>
          <select value={statToOverride} onChange={(e) => setStatToOverride(e.target.value)}>
            <option value="">Select Stat</option>
            <option value="pass_attempts">Pass Attempts</option>
            <option value="completions">Completions</option>
            <option value="pass_yards">Pass Yards</option>
            {/* More options */}
          </select>
        </div>
        
        <div className="form-group">
          <label>Override Type</label>
          <select value={overrideType} onChange={(e) => setOverrideType(e.target.value)}>
            <option value="absolute">Absolute Value</option>
            <option value="percentage">Percentage Change</option>
            <option value="increment">Increment/Decrement</option>
          </select>
        </div>
        
        <div className="form-group">
          <label>Value</label>
          <input 
            type="number" 
            value={overrideValue} 
            onChange={(e) => setOverrideValue(e.target.value)}
            step={overrideType === 'percentage' ? 5 : 1}
          />
          {overrideType === 'percentage' && <span>%</span>}
        </div>
        
        <button onClick={applyBatchOverride}>Apply to Selected Players</button>
      </div>
    </div>
  );
};
```

### 4.4 Visualization & Comparison (Week 4)
- Implement data visualization for projections
- Add comparison features

```typescript
const ProjectionComparisonChart = ({ players, stat }) => {
  const [data, setData] = useState([]);
  
  useEffect(() => {
    const fetchProjections = async () => {
      const projectionData = [];
      
      for (const playerId of players) {
        try {
          const player = await api.getPlayer(playerId);
          const baseProjection = await api.getBaseProjection(playerId);
          const overriddenProjection = await api.getProjectionWithOverrides(playerId);
          
          projectionData.push({
            name: player.name,
            base: baseProjection[stat] || 0,
            overridden: overriddenProjection[stat] || 0
          });
          
        } catch (error) {
          console.error(`Failed to fetch data for player ${playerId}`, error);
        }
      }
      
      setData(projectionData);
    };
    
    if (players.length > 0 && stat) {
      fetchProjections();
    }
  }, [players, stat]);
  
  if (data.length === 0) {
    return <div>No data available</div>;
  }
  
  return (
    <div className="projection-comparison">
      <h3>{stat.replace('_', ' ')} Comparison</h3>
      
      <BarChart width={600} height={400} data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="base" fill="#8884d8" name="Base Projection" />
        <Bar dataKey="overridden" fill="#82ca9d" name="With Overrides" />
      </BarChart>
    </div>
  );
};
```

## Phase 5: Testing & Deployment (3 weeks)

### 5.1 Unit Testing (Week 1)
- Implement unit tests for all services

```python
class TestOverrideService:
    @pytest.mark.asyncio
    async def test_create_override(self, override_service, test_player, test_projection):
        """Test creating a new override."""
        override = await override_service.create_stat_override(
            player_id=test_player.player_id,
            projection_id=test_projection.projection_id,
            stat_name="pass_attempts",
            manual_value=500.0
        )
        
        assert override is not None
        assert override.player_id == test_player.player_id
        assert override.projection_id == test_projection.projection_id
        assert override.stat_name == "pass_attempts"
        assert override.calculated_value == test_projection.pass_attempts
        assert override.manual_value == 500.0
        
        # Verify projection has been marked as having overrides
        assert test_projection.has_overrides is True
    
    @pytest.mark.asyncio
    async def test_apply_overrides(self, override_service, test_player, test_projection):
        """Test applying overrides to a projection."""
        # Create test override
        await override_service.create_stat_override(
            player_id=test_player.player_id,
            projection_id=test_projection.projection_id,
            stat_name="pass_attempts",
            manual_value=500.0
        )
        
        # Apply overrides
        updated_projection = await override_service.apply_overrides_to_projection(test_projection)
        
        assert updated_projection.pass_attempts == 500.0
        
        # Dependent stats should be recalculated
        # This test depends on the specific dependencies in your model
        assert updated_projection.completions != test_projection.completions
```

### 5.2 Integration Testing (Week 1-2)
- Implement integration tests for API endpoints

```python
class TestOverrideAPI:
    async def test_create_override_endpoint(self, client, test_player, test_projection):
        """Test the create override endpoint."""
        response = await client.post(
            "/api/overrides",
            json={
                "player_id": test_player.player_id,
                "projection_id": test_projection.projection_id,
                "stat_name": "pass_attempts",
                "manual_value": 500.0
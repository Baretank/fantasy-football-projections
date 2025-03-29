# Fantasy Football Statistical Projection Model: Technical Implementation and Methodology

## Abstract

This document details our statistical model for projecting fantasy football player performance. The model incorporates team-level offensive metrics, individual player efficiency patterns, and a sophisticated system for manual overrides to generate accurate fantasy point projections. By leveraging multi-year historical data, regression analysis, and allowing for scenario-based adjustments, the system provides a flexible framework for fantasy football analysis and decision-making that combines statistical rigor with expert judgment.

## 1. Introduction

Fantasy football projections require a balance of statistical analysis and contextual understanding. Our enhanced model formalizes these relationships through a structured approach that:

1. Establishes team-level "constraint envelopes"
2. Projects player performance within team constraints
3. Allows for expert-driven manual overrides
4. Maintains mathematical consistency across changes
5. Supports multiple projection scenarios

This approach preserves the mathematical integrity of projections while enabling analysts to apply their domain expertise through a flexible override system.

## 2. Enhanced Data Structure

### 2.1 Team-Level Statistics (Per Game)

The model uses team-level offensive statistics as the foundation for all projections:

**Core Volume Metrics**
- **Plays**: Total offensive plays per game
- **Pass %**: Percentage of plays that are pass attempts

**Enhanced Passing Stats**
- **PaATT**: Pass attempts per game
- **Gross PaYD**: Passing yards before sack adjustments
- **Sacks**: Sacks allowed per game
- **Sack Yards**: Average yards lost on sacks
- **Total Sack Yards**: Total yards lost to sacks per game
- **Net PaYD**: Passing yards after sack adjustments
- **Y/A** (Gross): Yards per pass attempt before sack adjustments
- **NY/A** (Net): Net yards per pass attempt after sack adjustments
- **PaTD**: Passing touchdowns per game
- **TD%**: Passing touchdown percentage
- **INT**: Interceptions per game
- **INT%**: Interception percentage

**Enhanced Rushing Stats**
- **Car**: Rush attempts (carries) per game
- **Gross RuYD**: Rushing yards before fumble adjustments
- **Fumbles Lost**: Fumbles lost per game
- **Fumble Rate**: Fumbles lost per rush attempt
- **Net RuYD**: Rushing yards after fumble adjustments
- **YPC** (Gross): Yards per carry before fumble adjustments
- **NYPC** (Net): Net yards per carry after fumble adjustments
- **RuTD**: Rushing touchdowns per game
- **Rush TD%**: Rushing touchdown percentage

**Receiving Stats**
- **Tar**: Targets per game
- **Comp%**: Pass completion percentage
- **Rec**: Receptions per game
- **ReYD**: Receiving yards per game
- **ReTD**: Receiving touchdowns per game

**Aggregate Stats**
- **ToYD**: Total yards per game (Net PaYD + Net RuYD)
- **ToTD**: Total touchdowns per game (PaTD + RuTD)
- **HPPR**: Team fantasy points in Half-PPR format

### 2.2 Player Statistics (Season Totals)

Player projections include standard and enhanced metrics:

**Identity**
- **Player**: Player name
- **Team**: Team abbreviation
- **Pos**: Position (QB, RB, WR, TE)
- **Status**: Starter, Backup, Fill (automatically populated)
- **Gm**: Projected games played

**Passing Stats**
- **PaATT**: Pass attempts
- **Comp**: Pass completions
- **Gross PaYD**: Passing yards before sack adjustments
- **Sacks**: Sacks taken
- **Sack Yards Lost**: Yards lost to sacks
- **Net PaYD**: Passing yards after sack adjustments
- **PaTD**: Passing touchdowns
- **INT**: Interceptions thrown

**Rushing Stats**
- **Car**: Rush attempts
- **Gross RuYD**: Rushing yards before fumble adjustments
- **Fumbles Lost**: Fumbles lost
- **Net RuYD**: Rushing yards after fumble adjustments
- **RuTD**: Rushing touchdowns

**Receiving Stats**
- **Tar**: Targets
- **Rec**: Receptions
- **ReYD**: Receiving yards
- **ReTD**: Receiving touchdowns

**Fantasy Scoring**
- **HPPR**: Half-PPR fantasy points (season total)
- **PG**: Fantasy points per game

### 2.3 Player Efficiency Metrics

- **Att%**: Percentage of team pass attempts
- **Comp%**: Completion percentage
- **YPA** (Gross): Yards per pass attempt before sacks
- **NYPA** (Net): Net yards per pass attempt after sacks
- **TD%** (passing): Touchdown percentage on passes
- **INT%**: Interception percentage
- **Sack%**: Percentage of dropbacks resulting in sacks
- **Yards/Sack**: Average yards lost per sack
- **Car%**: Percentage of team rush attempts
- **YPC** (Gross): Yards per carry before fumbles
- **NYPC** (Net): Net yards per carry after fumbles
- **Fumble%**: Fumbles per rush attempt
- **Rush TD%**: Touchdown percentage on rushes
- **Tar%**: Percentage of team targets
- **Catch%**: Catch rate (Rec/Tar)
- **YPT**: Yards per target
- **Rec TD%**: Touchdown percentage on targets

### 2.4 Override System

The model includes a comprehensive override system to track manual adjustments:

**StatOverride**
- **override_id**: Unique identifier
- **player_id**: Associated player
- **projection_id**: Associated projection
- **stat_name**: The specific stat being overridden (e.g., "pass_attempts")
- **calculated_value**: Original model-generated value
- **manual_value**: User-specified override value
- **notes**: Optional commentary on override rationale
- **created_at**: Timestamp

**EfficiencyOverride**
- **override_id**: Unique identifier
- **player_id**: Associated player
- **metric_name**: The efficiency metric being adjusted (e.g., "yards_per_carry")
- **default_value**: Original calculated efficiency
- **modifier**: Multiplier (1.0 = no change)
- **final_value**: Result after applying modifier
- **notes**: Reasoning for adjustment
- **created_at**: Timestamp

**ContextualAdjustment**
- **adjustment_id**: Unique identifier
- **adjustment_type**: Type of adjustment ("coaching", "injury", "schedule")
- **player_id**: Affected player (optional)
- **team**: Affected team (optional)
- **position**: Affected position (optional)
- **affected_stats**: JSON of stats and their modifiers
- **description**: Explanation of adjustment
- **severity**: Impact magnitude (0.0-1.0)
- **created_at**: Timestamp

### 2.5 Scenario System

The model supports multiple projection scenarios:

**ProjectionScenario**
- **scenario_id**: Unique identifier
- **name**: Scenario name
- **description**: Scenario description
- **is_baseline**: Whether this is the baseline scenario
- **created_at**: Timestamp

## 3. Calculation Methodology

### 3.1 Team Projection Formulas

1. **PaATT** = Plays × Pass%
2. **Gross PaYD** = PaATT × Y/A (Gross)
3. **Total Sack Yards** = Sacks × Sack Yards
4. **Net PaYD** = Gross PaYD - Total Sack Yards
5. **PaTD** = PaATT × TD% (passing)
6. **Car** = Plays - PaATT - Sacks
7. **Gross RuYD** = Car × YPC (Gross)
8. **Net RuYD** = Gross RuYD × (1 - Fumble Rate)
9. **RuTD** = Car × Rush TD%
10. **Tar** ≈ PaATT (usually within 1-2%)
11. **Rec** = Tar × Comp%
12. **ReYD** = Net PaYD (matches net passing yards)
13. **ReTD** = PaTD (matches passing TDs)
14. **ToYD** = Net PaYD + Net RuYD
15. **ToTD** = PaTD + RuTD

### 3.2 Player Projection Formulas

1. **PaATT** = (Team PaATT × 17) × Att%
2. **Comp** = PaATT × Comp%
3. **Gross PaYD** = PaATT × YPA (Gross)
4. **Sacks** = (PaATT / (1 - Sack%)) × Sack%
5. **Sack Yards Lost** = Sacks × Yards/Sack
6. **Net PaYD** = Gross PaYD - Sack Yards Lost
7. **PaTD** = PaATT × TD% (passing)
8. **INT** = PaATT × INT%
9. **Car** = (Team Car × 17) × Car%
10. **Gross RuYD** = Car × YPC (Gross)
11. **Fumbles Lost** = Car × Fumble%
12. **Net RuYD** = Gross RuYD - (Fumble impact adjustment)
13. **RuTD** = Car × Rush TD%
14. **Tar** = (Team Tar × 17) × Tar%
15. **Rec** = Tar × Catch%
16. **ReYD** = Tar × YPT
17. **ReTD** = Tar × Rec TD%
18. **HPPR** = (Net PaYD × 0.04) + (PaTD × 4) + (INT × -2) + (Fumbles Lost × -2) + (Net RuYD × 0.1) + (RuTD × 6) + (Rec × 0.5) + (ReYD × 0.1) + (ReTD × 6)
19. **PG** = HPPR / Gm

### 3.3 Adjustment Processing

The model processes adjustments through a hierarchical system:

1. **Team-level adjustments**: Applied first, affecting all players on the team
2. **Position group adjustments**: Applied second, affecting all players at a position
3. **Individual player adjustments**: Applied last, affecting only the specific player

Each adjustment maintains mathematical consistency by:

- Preserving team total plays
- Maintaining valid target/touch shares
- Adjusting related metrics proportionally
- Ensuring consistent touchdown distribution
- Recalculating dependent values

### 3.4 Multi-Year Regression System

The model includes a regression system to prevent unrealistic projections:

1. Calculate z-scores for team and player efficiency metrics
2. Apply regression based on z-score magnitude:
   - |z| > 2.0: 50% regression to mean
   - 1.5 < |z| < 2.0: 35% regression to mean
   - 1.0 < |z| < 1.5: 20% regression to mean
   - |z| < 1.0: 10% regression to mean
3. Apply position-specific regression rates
4. Account for player age and consistency

### 3.5 Fill Player System

The model includes automatic reconciliation players:

1. Calculate team total stats (per position) for the full season
2. Calculate sum of all player stats by position group
3. Fill Player Stats = Team Total - Sum of Player Stats
4. When Fill Player values are large or negative, this indicates needed adjustments

## 4. Manual Override Implementation

### 4.1 Direct Stat Overrides

```python
async def apply_stat_override(
    self, player_id: str, stat_name: str, manual_value: float
) -> Projection:
    """Override a specific statistical value for a player."""
    # Get current projection
    projection = await self.projection_service.get_latest_projection(player_id)
    if not projection:
        raise ValueError(f"No projection found for player {player_id}")
    
    # Store original value
    calculated_value = getattr(projection, stat_name)
    
    # Create override record
    override = StatOverride(
        player_id=player_id,
        projection_id=projection.projection_id,
        stat_name=stat_name,
        calculated_value=calculated_value,
        manual_value=manual_value
    )
    self.db.add(override)
    
    # Apply override to projection
    setattr(projection, stat_name, manual_value)
    projection.has_overrides = True
    
    # Recalculate dependent values
    await self._recalculate_dependencies(projection, stat_name)
    
    self.db.commit()
    return projection
```

### 4.2 Efficiency Factor Overrides

```python
async def apply_efficiency_override(
    self, player_id: str, metric_name: str, modifier: float
) -> Dict[str, float]:
    """Apply an efficiency adjustment for a player."""
    # Get current projection
    projection = await self.projection_service.get_latest_projection(player_id)
    if not projection:
        raise ValueError(f"No projection found for player {player_id}")
    
    # Get current value
    current_value = getattr(projection, metric_name, None)
    if current_value is None:
        raise ValueError(f"Invalid efficiency metric: {metric_name}")
    
    # Calculate new value
    new_value = current_value * modifier
    
    # Create override record
    override = EfficiencyOverride(
        player_id=player_id,
        metric_name=metric_name,
        default_value=current_value,
        modifier=modifier,
        final_value=new_value
    )
    self.db.add(override)
    
    # Apply to projection
    setattr(projection, metric_name, new_value)
    projection.has_overrides = True
    
    # Recalculate dependent stats
    affected_stats = self._get_dependent_stats(metric_name)
    updated_stats = await self._recalculate_stats_from_efficiency(
        projection, metric_name, affected_stats
    )
    
    self.db.commit()
    return updated_stats
```

### 4.3 Contextual Adjustments

```python
async def apply_contextual_adjustment(
    self, adjustment_type: str, target_entities: Dict, 
    affected_stats: Dict, description: str, severity: float
) -> List[Projection]:
    """Apply contextual adjustment to one or more players."""
    # Create adjustment record
    adjustment = ContextualAdjustment(
        adjustment_type=adjustment_type,
        player_id=target_entities.get("player_id"),
        team=target_entities.get("team"),
        position=target_entities.get("position"),
        affected_stats=affected_stats,
        description=description,
        severity=severity
    )
    self.db.add(adjustment)
    self.db.flush()
    
    # Find all affected projections
    projections = await self._get_affected_projections(target_entities)
    
    # Apply adjustments to each projection
    updated_projections = []
    for proj in projections:
        # Apply each stat adjustment
        for stat, modifier in affected_stats.items():
            if hasattr(proj, stat):
                current_value = getattr(proj, stat)
                new_value = current_value * modifier
                setattr(proj, stat, new_value)
                
        # Mark as having overrides
        proj.has_overrides = True
        
        # Recalculate dependent values
        await self._recalculate_projection(proj)
        updated_projections.append(proj)
    
    self.db.commit()
    return updated_projections
```

### 4.4 Projection Scenarios

```python
async def create_scenario(
    self, name: str, description: str = None, 
    clone_from_id: str = None
) -> ProjectionScenario:
    """Create a new projection scenario."""
    scenario = ProjectionScenario(
        name=name,
        description=description,
        is_baseline=False
    )
    
    self.db.add(scenario)
    self.db.flush()
    
    # If cloning, copy all projections from source scenario
    if clone_from_id:
        await self._clone_scenario_projections(clone_from_id, scenario.scenario_id)
    
    self.db.commit()
    return scenario

async def generate_projection_with_overrides(
    self, player_id: str, scenario_id: Optional[str] = None
) -> Projection:
    """Generate a projection incorporating all applicable overrides."""
    # Start with base statistical projection
    base_projection = await self.create_base_projection(player_id)
    
    # Apply efficiency overrides
    efficiency_overrides = await self.override_service.get_efficiency_overrides(
        player_id, scenario_id
    )
    for metric, modifier in efficiency_overrides.items():
        if hasattr(base_projection, metric):
            original = getattr(base_projection, metric)
            setattr(base_projection, metric, original * modifier)
    
    # Apply direct stat overrides (these take precedence)
    stat_overrides = await self.override_service.get_stat_overrides(
        player_id, scenario_id
    )
    for stat, value in stat_overrides.items():
        if hasattr(base_projection, stat):
            setattr(base_projection, stat, value)
    
    # Apply contextual adjustments
    await self._apply_contextual_adjustments(base_projection, scenario_id)
    
    # Recalculate dependent values
    await self._recalculate_projection(base_projection)
    
    # Mark projection as including overrides
    base_projection.has_overrides = True
    
    return base_projection
```

## 5. Usage Scenarios

### 5.1 Baseline Projections

```python
# Generate base projections for all players
async def generate_all_base_projections(season: int) -> List[Projection]:
    players = await self.data_service.get_all_players()
    
    projections = []
    for player in players:
        projection = await self.create_base_projection(
            player_id=player.player_id,
            season=season
        )
        projections.append(projection)
    
    return projections
```

### 5.2 Player Overrides

```python
# Apply expert overrides to a player
async def apply_expert_overrides(
    player_id: str, overrides: Dict[str, float]
) -> Projection:
    projection = await self.get_latest_projection(player_id)
    
    for stat, value in overrides.items():
        await self.override_service.create_stat_override(
            player_id=player_id,
            projection_id=projection.projection_id,
            stat_name=stat,
            manual_value=value,
            notes="Expert override"
        )
    
    # Get updated projection with overrides applied
    return await self.override_service.get_projection_with_overrides(
        projection.projection_id
    )
```

### 5.3 Scenario Analysis

```python
# Create a "high usage" scenario for RBs
async def create_high_usage_rb_scenario() -> List[Projection]:
    # Create new scenario
    scenario = await self.scenario_service.create_scenario(
        name="High RB Usage",
        description="Increased rushing attempts for starting RBs"
    )
    
    # Get all starting RBs
    rbs = await self.data_service.get_players_by_position("RB")
    
    # Apply contextual adjustment
    adjustments = {
        "car_pct": 1.15,      # 15% more rush share
        "rush_attempts": 1.15,  # 15% more rushes
        "targets": 1.05       # 5% more targets
    }
    
    # Apply to all RBs
    await self.override_service.apply_contextual_adjustment(
        adjustment_type="usage",
        target_entities={"position": "RB"},
        affected_stats=adjustments,
        description="Increased RB usage scenario",
        severity=0.8
    )
    
    # Generate all projections with this scenario
    projections = []
    for rb in rbs:
        proj = await self.generate_projection_with_overrides(
            player_id=rb.player_id,
            scenario_id=scenario.scenario_id
        )
        projections.append(proj)
    
    return projections
```

## 6. Implementation Details

### 6.1 Database Models

```python
class Projection(Base):
    __tablename__ = "projections"
    
    projection_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    player_id = Column(String, ForeignKey("players.player_id"))
    scenario_id = Column(String, ForeignKey("projection_scenarios.scenario_id"), nullable=True)
    season = Column(Integer)
    games = Column(Integer)
    
    # Enhanced passing stats
    pass_attempts = Column(Float)
    completions = Column(Float)
    gross_pass_yards = Column(Float)
    sacks = Column(Float)
    sack_yards = Column(Float)
    net_pass_yards = Column(Float)
    pass_td = Column(Float)
    interceptions = Column(Float)
    
    # Efficiency metrics
    pass_att_pct = Column(Float)
    comp_pct = Column(Float)
    yards_per_att = Column(Float)
    net_yards_per_att = Column(Float)
    pass_td_rate = Column(Float)
    int_rate = Column(Float)
    sack_rate = Column(Float)
    
    # Enhanced rushing stats
    carries = Column(Float)
    gross_rush_yards = Column(Float)
    fumbles_lost = Column(Float)
    net_rush_yards = Column(Float)
    rush_td = Column(Float)
    
    # Rushing efficiency metrics
    car_pct = Column(Float)
    yards_per_carry = Column(Float)
    net_yards_per_carry = Column(Float)
    fumble_rate = Column(Float)
    rush_td_rate = Column(Float)
    
    # Receiving stats
    targets = Column(Float)
    receptions = Column(Float)
    rec_yards = Column(Float)
    rec_td = Column(Float)
    
    # Receiving efficiency metrics
    tar_pct = Column(Float)
    catch_pct = Column(Float)
    yards_per_target = Column(Float)
    rec_td_rate = Column(Float)
    
    # Fantasy points
    half_ppr = Column(Float)
    
    # Status flags
    has_overrides = Column(Boolean, default=False)
    is_fill_player = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    player = relationship("Player", back_populates="projections")
    scenario = relationship("ProjectionScenario", back_populates="projections")
    stat_overrides = relationship("StatOverride", back_populates="projection")
```

### 6.2 Services

```python
class ProjectionService:
    def __init__(self, db: Session):
        self.db = db
        self.data_service = DataService(db)
        self.team_stats_service = TeamStatsService(db)
        
    async def create_base_projection(self, player_id: str, season: int) -> Projection:
        """Create base projection from historical data."""
        # Implementation...
        
    async def update_projection(self, projection_id: str, adjustments: Dict[str, float]) -> Projection:
        """Update projection with adjustments."""
        # Implementation...
        
    async def calculate_fantasy_points(self, projection: Projection) -> float:
        """Calculate fantasy points with enhanced stats."""
        points = 0.0
        
        # Passing points using net yards
        if projection.net_pass_yards:
            points += (projection.net_pass_yards / 25.0)
        if projection.pass_td:
            points += (projection.pass_td * 4.0)
        if projection.interceptions:
            points -= (projection.interceptions * 2.0)
            
        # Rushing points using net yards
        if projection.net_rush_yards:
            points += (projection.net_rush_yards / 10.0)
        if projection.rush_td:
            points += (projection.rush_td * 6.0)
        
        # Fumble penalty
        if projection.fumbles_lost:
            points -= (projection.fumbles_lost * 2.0)
            
        # Receiving points
        if projection.receptions:
            points += (projection.receptions * 0.5)
        if projection.rec_yards:
            points += (projection.rec_yards / 10.0)
        if projection.rec_td:
            points += (projection.rec_td * 6.0)
            
        return points
```

## 7. User Interface

### 7.1 Projection Editor

The system includes a comprehensive UI for editing projections:

- Multi-tab interface (passing, rushing, receiving stats)
- Visual indicators for overridden values
- Comparison view (original vs. adjusted)
- Real-time recalculation of dependent values
- Notes field for override rationale

### 7.2 Scenario Management

The system includes a scenario management interface:

- Create, clone, and manage scenarios
- Apply scenario-specific adjustments
- Compare multiple scenarios
- Export scenario data

### 7.3 Batch Operations

The system supports batch operations:

- Apply the same adjustment to multiple players
- Position-based adjustments
- Team-based adjustments
- Template-based contextual adjustments

## 8. Model Validation

The model's accuracy is validated through:

1. Historical backtesting against actual performance
2. Mathematical consistency checks (team totals match player sums)
3. Comparison with public projections from major fantasy sites
4. Fill player analysis to identify model inconsistencies
5. Expert review and adjustment

## 9. Projection Uncertainty and Confidence Intervals

The model now incorporates statistical uncertainty and confidence intervals:

### 9.1 Variance Calculation

Each projected stat has an associated variance calculated using:

1. Historical game-to-game variance when available
2. Position-specific baseline variance coefficients
3. Years of historical data (more years = lower variance)
4. Position-specific consistency factors

### 9.2 Confidence Intervals

The system provides multiple confidence interval levels:

- 50% intervals: Values with moderate likelihood
- 80% intervals: Values with high likelihood (default)
- 90% intervals: Values with very high likelihood
- 95% intervals: Values with extremely high likelihood

### 9.3 Rookie Projection Methodology

Rookie projections use a specialized methodology combining:

1. Historical comparisons with similar draft profile players
2. Draft position adjustment factor
3. Team context and opportunity assessment
4. Position-specific model (QB, RB, WR, TE)
5. Three-tiered projection system (high, medium, low)

## 10. Future Enhancements

Planned improvements include:

1. Advanced machine learning integration for baseline projections
2. Strength of schedule adjustment factors
3. Game script dependency modeling
4. Player archetype classification for more accurate projections
5. Injury impact modeling
6. Additional scoring format support
7. Time-series based uncertainty analysis

## 11. Conclusion

This enhanced projection model combines statistical rigor with expert judgment through its sophisticated override system. The model maintains mathematical consistency while allowing for flexible adjustments based on changing circumstances, news, and expert analysis. By supporting multiple projection scenarios, statistical uncertainty modeling, and team-level adjustments, the system enables comprehensive fantasy football analysis and decision-making.

## Appendix A: Statistical Formulas

### A.1 Enhanced Efficiency Metrics
- Net Yards per Attempt = (Passing Yards - Sack Yards) / (Pass Attempts + Sacks)
- Net Yards per Carry = (Rushing Yards - [Fumbles × Avg Yards Lost per Fumble]) / Carries
- Adjusted Touchdown Rate = TDs / (Opportunities × League Average Modifier)

### A.2 Advanced Usage Metrics
- Weighted Opportunity Share = (Rush Share × 0.7) + (Target Share × 1.0) + (Red Zone Share × 1.3)
- Expected Fantasy Points = Σ (Opportunity × Average Fantasy Value per Opportunity Type)
- Fantasy Points Over Expected (FPOE) = Actual Fantasy Points - Expected Fantasy Points
# Fantasy Football Statistical Projection Model

## Overview

This document provides a comprehensive explanation of the statistical methodology and implementation details of the Fantasy Football Projections system. The model incorporates team-level offensive metrics, individual player efficiency patterns, and a sophisticated system for manual overrides to generate accurate fantasy point projections.

## Model Architecture

The projection system is built on several foundational principles:

1. **Team-level constraint envelopes** - Overall offensive production boundaries
2. **Historical player efficiency metrics** - Individual performance patterns
3. **Statistical regression** - Prevention of unrealistic projections
4. **Manual override system** - Expert adjustments with mathematical consistency
5. **Scenario planning** - Alternative projection situations
6. **Projection uncertainty** - Statistical variance and confidence intervals
7. **Rookie projection system** - Specialized methodology for first-year players

## Data Structure

### Team-Level Statistics (Per Game)

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

### Player Statistics (Season Totals)

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

### Player Efficiency Metrics

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

## Calculation Methodology

### Team Projection Formulas

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

### Player Projection Formulas

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

## Advanced Projection Components

### Statistical Regression System

To prevent unrealistic projections, especially for players with limited sample sizes or extreme performance metrics, the system applies statistical regression based on z-scores.

**Regression Approach:**
- Calculate mean and standard deviation for each metric by position
- Calculate z-score for player's efficiency metric
- Apply regression to mean based on z-score magnitude:
  - |z| > 2.0: 50% regression to mean
  - 1.5 < |z| < 2.0: 35% regression to mean
  - 1.0 < |z| < 1.5: 20% regression to mean
  - |z| < 1.0: 10% regression to mean

**Example Calculation:**
```
Position Average YPC: 4.3
Position Std Dev: 0.5
Player YPC: 5.2
Z-score: (5.2 - 4.3) / 0.5 = 1.8
Regression Factor: 35%
Regressed YPC: 4.3 + (5.2 - 4.3) × (1 - 0.35) = 4.89
```

### Manual Override System

The system includes a comprehensive override tracking system that allows analysts to modify projections while maintaining mathematical consistency.

**Types of Overrides:**
- **Direct Stat Overrides**: Change specific statistical values directly
- **Efficiency Overrides**: Modify efficiency metrics with percentage adjustments
- **Contextual Adjustments**: Apply modifications based on specific contexts (injuries, coaching changes, etc.)

**Mathematical Consistency:**
When an override is applied, dependent statistics are automatically recalculated. For example:
- If pass attempts are manually increased, completions and passing yards are adjusted accordingly
- If target share is adjusted, receptions and receiving yards are updated
- Team total constraints are preserved through fill player adjustments

### Projection Scenarios

The system supports multiple projection scenarios to model different potential outcomes.

**Scenario Management:**
- Baseline scenario represents the most likely outcome
- Alternative scenarios can model different situations:
  - High passing volume
  - Run-heavy approach
  - Rookie-focused usage
  - Injury replacement situations

**Scenario Cloning:**
Scenarios can be cloned to create variations with specific adjustments, while preserving the baseline statistical foundation.

### Projection Uncertainty

Each projection includes statistical variance and confidence intervals.

**Variance Calculation:**
- Historical game-to-game variance when available
- Position-specific variance coefficients
- Years of historical data (more years = lower variance)
- Consistency factor based on player history

**Confidence Intervals:**
The system provides multiple confidence intervals:
- 50% intervals: Values with moderate likelihood
- 80% intervals: Values with high likelihood (default)
- 90% intervals: Values with very high likelihood
- 95% intervals: Values with extremely high likelihood

### Rookie Projections

Rookies are projected using a specialized methodology that combines:

**Rookie Projection Inputs:**
- Draft position and draft capital
- College production and efficiency metrics
- Athletic testing results (combine data)
- Team context and expected opportunity
- Historical comparisons with similar player profiles

**Three-Tiered Projections:**
- Low projection (25th percentile outcome)
- Medium projection (50th percentile outcome)
- High projection (75th percentile outcome)

### Fill Player System

To maintain mathematical consistency between team projections and the sum of all player projections, the system includes an automatic fill player generation mechanism.

**Fill Player Process:**
1. Calculate team total stats (per position) for the full season
2. Calculate sum of all player stats by position group
3. Fill Player Stats = Team Total - Sum of Player Stats
4. When Fill Player values are large or negative, this indicates needed adjustments

**Example:**
```
Team Total Pass Attempts: 650
Sum of QB Pass Attempts: 550
Fill QB Pass Attempts: 650 - 550 = 100
```

## Implementation Details

### Database Models

The core projection system is implemented through several database models:

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

### Core Service Classes

The projection system is implemented through several interconnected service classes:

1. **ProjectionService**: Core projection calculations
2. **TeamStatService**: Team-level statistics management
3. **OverrideService**: Manual override handling
4. **ScenarioService**: Scenario management
5. **RookieProjectionService**: Specialized rookie projections
6. **ProjectionVarianceService**: Uncertainty and confidence intervals

### Override Implementation

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

### Dependency Recalculation

When a statistical value is modified through an override, dependent values are automatically recalculated using a dependency graph. Examples:

- If pass attempts are modified, completions, passing yards, and passing TDs are recalculated
- If target share is modified, targets, receptions, receiving yards, and receiving TDs are recalculated
- If efficiency metrics are modified, the corresponding volume stats are recalculated

## Model Validation

The projection system's accuracy is validated through:

1. **Historical backtesting** against actual performance
2. **Mathematical consistency checks** (team totals match player sums)
3. **Comparison with external projections** from major fantasy sites
4. **Fill player analysis** to identify model inconsistencies
5. **Expert review and adjustment**

## Future Enhancements

Planned improvements to the projection methodology include:

1. **Machine learning integration** for baseline projections
2. **Strength of schedule adjustments**
3. **Game script dependency modeling**
4. **Player archetype classification**
5. **Injury impact modeling**
6. **Additional scoring format support**
7. **Time-series based uncertainty analysis**

## Conclusion

This enhanced projection model combines statistical rigor with expert judgment through its sophisticated override system. The model maintains mathematical consistency while allowing for flexible adjustments based on changing circumstances, news, and expert analysis. By supporting multiple projection scenarios, statistical uncertainty modeling, and team-level adjustments, the system enables comprehensive fantasy football analysis and decision-making.
# Fantasy Football Statistical Projection Model: Technical Implementation and Methodology

## Abstract

This paper presents a comprehensive statistical model for projecting fantasy football player performance. The model incorporates team-level offensive metrics, individual player statistics, and adjustable parameters to generate accurate fantasy point projections. By leveraging historical data and allowing for scenario-based adjustments, the system provides a flexible framework for fantasy football analysis and decision-making.

## 1. Introduction

Fantasy football projections traditionally rely on a combination of historical data, team context, and expected usage patterns. Our model formalizes these relationships through a structured approach that maintains mathematical consistency while allowing for user-defined adjustments based on new information or changed circumstances.

## 2. Data Structure

### 2.1 Team-Level Statistics

The model begins with team-level offensive statistics that establish the baseline context for player projections. Key metrics include:

- Total offensive plays
- Pass/run ratio
- Scoring rates (TD%)
- Efficiency metrics (YPC, YPA)
- Target distribution

These team-level metrics create a "constraint envelope" within which individual player projections must operate to maintain mathematical consistency.

### 2.2 Player Statistics

Player projections are segmented by position, with distinct statistical categories for each:

#### Quarterbacks
- Pass attempts and completions
- Passing yards and touchdowns
- Interceptions
- Rushing attempts and yards
- Rushing touchdowns

#### Running Backs
- Rushing attempts and yards
- Rushing touchdowns
- Targets and receptions
- Receiving yards
- Receiving touchdowns

#### Wide Receivers and Tight Ends
- Targets and receptions
- Receiving yards
- Receiving touchdowns
- Route participation
- Rushing attempts and yards
- Rushing touchdowns

## 3. Calculation Methodology

### 3.1 Base Projections

The model establishes base projections through the following process:

1. Team play volume baseline
2. Play type distribution (pass/run)
3. Position-specific usage rates
4. Efficiency metrics application
5. Touchdown rate calculation


### 3.2 Adjustment Factors

The model supports several types of adjustments:

```python
adjustment_factors = {
    'snap_share': 1.0,    # % of offensive plays
    'target_share': 1.0,  # % of team targets
    'rush_share': 1.0,    # % of team rushes
    'td_rate': 1.0,       # Touchdown rate modifier
    'efficiency': 1.0     # Yards per opportunity
}
```

These adjustments can be applied at both team and player levels, with the model maintaining internal consistency through:

1. Recalculation of team totals
2. Reallocation of opportunities
3. Efficiency metric updates
4. Fantasy point recalculation

### 3.3 Position-Specific Calculations

#### Quarterback Projections
```
Pass Attempts = Team Pass Plays × QB Play Share
Completions = Pass Attempts × Completion Rate
Passing Yards = Completions × Yards per Completion
Passing TDs = Pass Attempts × TD Rate
Rush Attempts = Team Rush Plays × QB Rush Share
Rush Yards = Rush Attempts × Yards per Carry
Rush TDs = Rush Attempts × Rush TD Rate
```

#### Running Back Projections
```
Rush Attempts = Team Rush Plays × RB Rush Share
Rush Yards = Rush Attempts × Yards per Carry
Rush TDs = Rush Attempts × Rush TD Rate
Targets = Team Targets × RB Target Share
Receptions = Targets × Catch Rate
Receiving Yards = Receptions × Yards per Reception
Receiving TDs = Targets × Receiving TD Rate
```

#### Receiver Projections
```
Targets = Team Targets × Target Share
Receptions = Targets × Catch Rate
Receiving Yards = Receptions × Yards per Reception
Receiving TDs = Targets × TD Rate
Rush Attempts = Team Rush Plays × WR/TE Rush Share
Rush Yards = Rush Attempts × Yards per Carry
Rush TDs = Rush Attempts × Rush TD Rate
```

## 4. Fantasy Point Calculation

The model calculates fantasy points using standard half-PPR scoring:

```python
def calculate_fantasy_points(stats):
    points = 0.0
    
    # Passing
    points += (stats.pass_yards / 25.0)  # 0.04 per yard
    points += (stats.pass_td * 4.0)
    points -= (stats.interceptions * 2.0)
    
    # Rushing
    points += (stats.rush_yards / 10.0)  # 0.1 per yard
    points += (stats.rush_td * 6.0)
    
    # Receiving
    points += (stats.receptions * 0.5)   # Half PPR
    points += (stats.rec_yards / 10.0)   # 0.1 per yard
    points += (stats.rec_td * 6.0)
    
    return points
```

## 5. Implementation Details

### 5.1 Data Models

The system uses strongly-typed data classes to ensure data integrity:

```python
@dataclass
class TeamStats:
    team: str
    plays: float
    pass_percentage: float
    pass_attempts: float
    # Additional fields...

@dataclass
class PlayerProjection:
    player: str
    team: str
    position: str
    rank: int
    # Common stats for all positions
    carries: Optional[float] = None
    rush_yards: Optional[float] = None
    rush_td: Optional[float] = None
    # Position-specific stats...
```

### 5.2 Adjustment Processing

Adjustments are processed through a hierarchical system:

1. Team-level adjustments
2. Position group adjustments
3. Individual player adjustments

Each adjustment maintains mathematical consistency by:

- Preserving team total plays
- Maintaining valid target/touch shares (including rushing attempts for all positions)
- Adjusting related metrics proportionally
- Ensuring consistent touchdown distribution across play types

### 5.1 Data Models

The system uses strongly-typed data classes to ensure data integrity:

```python
@dataclass
class TeamStats:
    team: str
    plays: float
    pass_percentage: float
    pass_attempts: float
    # Additional fields...

@dataclass
class PlayerProjection:
    player: str
    team: str
    position: str
    rank: int
    # Position-specific stats...
```

## 6. Usage Scenarios

### 6.1 Baseline Projections

```python
model = ProjectionModel()
model.load_baseline_data(team_data, player_data)
projections = model.get_base_projections()
```

### 6.2 Scenario Analysis

```python
adjustments = {
    'snap_share': 1.15,    # 15% increase
    'target_share': 1.10,  # 10% increase
    'td_rate': 0.95        # 5% decrease
}

new_projection = model.adjust_player_projection(
    player_name='Travis Kelce',
    adjustments=adjustments
)
```

## 7. Model Validation

The model's accuracy is validated through:

1. Historical backtesting
2. Mathematical consistency checks
3. Comparison with public projections
4. Expert review

## 8. Future Enhancements

Planned improvements include:

1. Advanced efficiency metrics integration
2. Machine learning for baseline projections
3. Improved strength of schedule adjustments
4. Additional scoring format support

## 9. Conclusion

This projection model provides a robust framework for fantasy football analysis while maintaining the flexibility needed for scenario planning and adjustment. By combining rigorous mathematical foundations with practical usability features, it serves as both an analytical tool and a decision support system for fantasy football players.

## References

1. Pro Football Reference Statistical Database
2. Historical Fantasy Football Performance Data
3. NFL Play-by-Play Data
4. Team Offensive Schema Analysis

## Appendix A: Statistical Formulas

### A.1 Efficiency Metrics
- Yards per Attempt = Total Yards / Total Attempts
- Touchdown Rate = Touchdowns / Opportunities
- Target Share = Player Targets / Team Targets
- Rush Share = Player Rush Attempts / Team Rush Attempts (all positions)

### A.2 Usage Metrics
- Snap Share = Player Snaps / Team Offensive Snaps
- Rush Share = Player Rush Attempts / Team Rush Attempts
- Route Participation = Routes Run / Team Pass Plays
- Designed Rush Rate = Designed Rushes / Total Plays (for WR/TE)


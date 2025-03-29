# Fantasy Football Projection Methodology

This document explains the statistical methodology and algorithms used in the Fantasy Football Projections system. It's intended for developers and analysts who want to understand how projections are calculated and how the various components of the system work together.

## Overview

The Fantasy Football Projections system uses a sophisticated statistical model that incorporates:

1. **Team-level constraint envelopes** - Overall offensive production boundaries
2. **Historical player efficiency metrics** - Individual performance patterns
3. **Statistical regression** - Prevention of unrealistic projections
4. **Manual override system** - Expert adjustments with mathematical consistency
5. **Scenario planning** - Alternative projection situations
6. **Projection uncertainty** - Statistical variance and confidence intervals
7. **Rookie projection system** - Specialized methodology for first-year players

## Core Projection Process

### 1. Team-Level Projections

The foundation of all player projections is the team-level offensive projection, which establishes the total "pie" of statistics that will be distributed among players.

**Key Team-Level Metrics:**
- **Plays**: Total offensive plays per game
- **Pass %**: Percentage of plays that are pass attempts
- **Pass Attempts**: Derived from Plays × Pass %
- **Pass Yards**: Total passing yards (both gross and net after sacks)
- **Pass TDs**: Total passing touchdowns
- **Rush Attempts**: Derived from plays not used for passing
- **Rush Yards**: Total rushing yards (both gross and net accounting for fumbles)
- **Rush TDs**: Total rushing touchdowns
- **Targets**: Usually closely aligned with pass attempts
- **Receptions**: Derived from Targets × Completion %

**Example Calculation:**
```
Team Plays: 65 per game
Pass %: 60%
Pass Attempts: 65 × 0.6 = 39 per game
Rush Attempts: 65 - 39 = 26 per game
```

### 2. Player Efficiency Metrics

Each player's projected statistics are calculated based on their historical efficiency metrics applied to their expected volume.

**Key Player Efficiency Metrics:**
- **Passing**: Completion %, Yards per Attempt, TD Rate, Interception Rate, Sack Rate
- **Rushing**: Yards per Carry, TD Rate, Fumble Rate
- **Receiving**: Target Share, Catch Rate, Yards per Target, TD Rate

**Example Calculation:**
```
QB Completion %: 67%
QB Pass Attempts: 550
QB Completions: 550 × 0.67 = 368.5
```

### 3. Statistical Regression

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

## Advanced Projection Components

### 1. Manual Override System

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

### 2. Projection Scenarios

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

### 3. Projection Uncertainty

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

### 4. Rookie Projections

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

## Detailed Calculation Formulas

### Team Projection Formulas

1. **Pass Attempts** = Plays × Pass%
2. **Gross Pass Yards** = Pass Attempts × Y/A (Gross)
3. **Total Sack Yards** = Sacks × Sack Yards
4. **Net Pass Yards** = Gross Pass Yards - Total Sack Yards
5. **Pass TDs** = Pass Attempts × TD% (passing)
6. **Rush Attempts** = Plays - Pass Attempts - Sacks
7. **Gross Rush Yards** = Rush Attempts × YPC (Gross)
8. **Net Rush Yards** = Gross Rush Yards × (1 - Fumble Rate)
9. **Rush TDs** = Rush Attempts × Rush TD%
10. **Targets** ≈ Pass Attempts (usually within 1-2%)
11. **Receptions** = Targets × Comp%
12. **Receiving Yards** = Net Pass Yards (matches net passing yards)
13. **Receiving TDs** = Pass TDs (matches passing TDs)
14. **Total Yards** = Net Pass Yards + Net Rush Yards
15. **Total TDs** = Pass TDs + Rush TDs

### Player Projection Formulas

1. **Pass Attempts** = (Team Pass Attempts × 17) × Att%
2. **Completions** = Pass Attempts × Comp%
3. **Gross Pass Yards** = Pass Attempts × YPA (Gross)
4. **Sacks** = (Pass Attempts / (1 - Sack%)) × Sack%
5. **Sack Yards Lost** = Sacks × Yards/Sack
6. **Net Pass Yards** = Gross Pass Yards - Sack Yards Lost
7. **Pass TDs** = Pass Attempts × TD% (passing)
8. **INTs** = Pass Attempts × INT%
9. **Rush Attempts** = (Team Rush Attempts × 17) × Rush Att%
10. **Gross Rush Yards** = Rush Attempts × YPC (Gross)
11. **Fumbles Lost** = Rush Attempts × Fumble%
12. **Net Rush Yards** = Gross Rush Yards - (Fumble impact adjustment)
13. **Rush TDs** = Rush Attempts × Rush TD%
14. **Targets** = (Team Targets × 17) × Tar%
15. **Receptions** = Targets × Catch%
16. **Receiving Yards** = Targets × YPT
17. **Receiving TDs** = Targets × Rec TD%
18. **Half-PPR Points** = (Net Pass Yards × 0.04) + (Pass TDs × 4) + (INTs × -2) + (Fumbles Lost × -2) + (Net Rush Yards × 0.1) + (Rush TDs × 6) + (Receptions × 0.5) + (Receiving Yards × 0.1) + (Receiving TDs × 6)

## Fill Player System

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

### Core Service Classes

The projection system is implemented through several interconnected service classes:

1. **ProjectionService**: Core projection calculations
2. **TeamStatService**: Team-level statistics management
3. **OverrideService**: Manual override handling
4. **ScenarioService**: Scenario management
5. **RookieProjectionService**: Specialized rookie projections
6. **ProjectionVarianceService**: Uncertainty and confidence intervals

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
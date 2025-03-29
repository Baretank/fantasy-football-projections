# Fantasy Football Projections User Guide

This guide provides detailed instructions for using the Fantasy Football Projections application, with a focus on creating and managing projection scenarios, making manual adjustments, and analyzing results.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Navigating the Interface](#navigating-the-interface)
3. [Viewing Player Projections](#viewing-player-projections)
4. [Making Manual Adjustments](#making-manual-adjustments)
5. [Creating and Managing Scenarios](#creating-and-managing-scenarios)
6. [Comparing Players](#comparing-players)
7. [Dashboard Analytics](#dashboard-analytics)
8. [Batch Operations](#batch-operations)
9. [Exporting Data](#exporting-data)
10. [Tips and Best Practices](#tips-and-best-practices)

## Getting Started

### Accessing the Application

1. Open your web browser and navigate to `http://localhost:5173` (development) or the deployed URL for your installation.
2. The application will load the dashboard view by default.

### Initial Setup

1. When using the application for the first time, verify that the baseline data is loaded.
2. Navigate to the Players section to ensure player data is available.
3. If needed, upload historical data using the administration tools.

## Navigating the Interface

### Main Navigation

The application has several primary sections:

- **Dashboard**: Overview of projections with key metrics and insights
- **Players**: Browse and search for players with filtering options
- **Projections**: View and edit detailed player projections
- **Scenarios**: Create and manage projection scenarios
- **Compare**: Side-by-side player comparison tool
- **Team Stats**: Team-level statistical projections

### Search and Filters

On most screens, you can filter data by:

- **Position**: QB, RB, WR, TE
- **Team**: NFL team abbreviation
- **Name**: Player name search
- **Scenario**: Currently active projection scenario

## Viewing Player Projections

### Player List View

1. Navigate to the Players section.
2. Use filters to narrow down the list of players.
3. Click on a player to view their detailed projection.

### Detailed Projection View

The detailed view includes:

- **Player Info**: Name, team, position, status
- **Projection Summary**: Key fantasy stats and points
- **Statistical Breakdown**: Tabs for passing, rushing, and receiving stats
- **Efficiency Metrics**: Performance efficiency indicators
- **Projection Range**: Statistical variance and confidence intervals
- **Historical Comparison**: Comparison with previous seasons

### Understanding Projection Ranges

Each projection includes:

- **Mean Projection**: The expected average outcome
- **Range**: 80% confidence interval (default)
- **Low/High**: Reasonable best and worst-case scenarios

## Making Manual Adjustments

### Types of Adjustments

You can make several types of adjustments:

1. **Direct Stat Overrides**: Change specific statistical values
2. **Efficiency Adjustments**: Modify efficiency metrics with percentage changes
3. **Game Count Adjustments**: Change projected games played
4. **Usage Adjustments**: Modify player usage patterns

### Making a Direct Stat Override

1. Navigate to a player's detailed projection.
2. Click the edit icon next to the stat you want to adjust.
3. Enter the new value.
4. Click "Save" to apply the change.
5. Note that dependent stats will automatically recalculate.

### Making an Efficiency Adjustment

1. Navigate to the Efficiency tab in a player's detailed projection.
2. Use the slider or input field to adjust the efficiency metric.
3. The adjustment will be displayed as a percentage change from baseline.
4. Click "Apply" to save the adjustment.

### Understanding Dependency Recalculation

When you adjust one statistic, related statistics will automatically update:

- Changing pass attempts affects completions, yards, and touchdowns
- Adjusting target share impacts targets, receptions, and receiving yards
- Modifying efficiency metrics updates volume projections

## Creating and Managing Scenarios

### What Are Scenarios?

Scenarios are alternative projection sets that allow you to explore different possibilities:

- **Baseline Scenario**: The default, most likely projections
- **Alternative Scenarios**: "What-if" situations with specific assumptions

### Creating a New Scenario

1. Navigate to the Scenarios section.
2. Click "Create New Scenario".
3. Enter a name and description for the scenario.
4. Choose whether to clone from an existing scenario or start fresh.
5. Click "Create".

### Scenario Types and Examples

Common scenario types include:

- **Injury Scenarios**: Project team stats with a key player injured
- **Role Change Scenarios**: Adjust player usage roles within a team
- **Scheme Scenarios**: Model different offensive approaches (pass-heavy, run-heavy)
- **Breakout Scenarios**: Project potential breakout performances
- **Rookie Impact Scenarios**: Model different rookie integration approaches

### Step-by-Step: Creating a Pass-Heavy Scenario

1. Navigate to the Scenarios section.
2. Click "Create New Scenario".
3. Name it "Pass-Heavy Offense".
4. Choose to clone from the baseline scenario.
5. Once created, navigate to the Team Stats section.
6. Select your new scenario from the dropdown.
7. For each team you want to adjust:
   - Increase the Pass % by 5-10%
   - Click "Apply" to update team projections
8. The system will automatically recalculate all affected player projections.

### Managing Scenarios

1. **Edit Scenario**: Change name or description
2. **Clone Scenario**: Create a copy for further adjustments
3. **Delete Scenario**: Remove unwanted scenarios
4. **Set as Baseline**: Make a scenario the new baseline

## Comparing Players

### Side-by-Side Comparison

1. Navigate to the Compare section.
2. Select 2-4 players to compare.
3. Choose the scenario to use for comparison.
4. View the side-by-side statistical comparison.

### Radar Chart Comparison

The radar chart visualization shows relative strengths across multiple categories:

1. Select players to compare.
2. Choose metrics for the radar axes (default includes key fantasy stats).
3. Hover over points for detailed values.

### Cross-Scenario Player Comparison

To compare a player across different scenarios:

1. Select a player.
2. In the comparison dropdown, choose "Cross-Scenario".
3. Select the scenarios to compare.
4. View how the player's projections change under different scenarios.

## Dashboard Analytics

### Dashboard Overview

The dashboard provides:

- **League Overview**: Position-based fantasy point distributions
- **Top Players**: Highest projected players by position
- **Variance Analysis**: Players with highest uncertainty
- **Opportunity Analysis**: Players with best opportunities
- **Recent Changes**: Latest projection adjustments

### Custom Dashboard Views

Create custom dashboard views:

1. Click "Customize Dashboard".
2. Drag and drop widgets to rearrange.
3. Add or remove widgets as needed.
4. Save your custom layout.

## Batch Operations

### Batch Adjustments

Apply the same adjustment to multiple players:

1. Navigate to the Batch Operations section.
2. Select players using filters and checkboxes.
3. Choose the stat or efficiency metric to adjust.
4. Select adjustment type (absolute, percentage, incremental).
5. Enter the adjustment value.
6. Click "Apply to Selected" to make the changes.

### Batch Scenario Applications

Apply scenario-specific adjustments to player groups:

1. Navigate to the Scenarios section.
2. Select a scenario.
3. Click "Batch Adjustments".
4. Filter players by position, team, or other criteria.
5. Choose the adjustment to apply to the group.
6. Click "Apply" to update the scenario.

## Exporting Data

### Export Formats

The system supports exporting data in several formats:

- **CSV**: For spreadsheet analysis
- **JSON**: For programmatic use
- **PDF**: For reports and printouts

### Exporting Projections

1. Navigate to the section containing data you want to export.
2. Apply desired filters.
3. Click the "Export" button.
4. Select the export format.
5. Choose whether to include variance data.
6. Click "Download" to get the file.

### Scheduled Exports

For recurring exports:

1. Navigate to the Export section.
2. Click "Create Scheduled Export".
3. Configure the export parameters and schedule.
4. The system will automatically generate exports on schedule.

## Tips and Best Practices

### Effective Scenario Planning

1. **Start Specific**: Begin with clear, specific scenarios rather than general ones.
2. **Document Assumptions**: Add detailed notes to each scenario explaining the assumptions.
3. **Use Relative Adjustments**: Prefer percentage adjustments over absolute values.
4. **Check Team Totals**: Verify team totals remain reasonable after adjustments.
5. **Consider Dependencies**: Remember that changing one player affects others.

### Optimization Workflow

A recommended workflow for optimizing projections:

1. Start with the baseline scenario.
2. Review team-level projections for reasonableness.
3. Adjust key players based on latest news and insights.
4. Create alternative scenarios for different assumptions.
5. Compare scenario outcomes to identify robust strategies.

### Interpreting Projection Variance

1. **Wide Ranges**: Indicate higher uncertainty (rookies, role changes, etc.).
2. **Narrow Ranges**: Indicate more predictable outcomes (established veterans).
3. **Risk Assessment**: Higher variance players have more upside but also more risk.
4. **Portfolio Approach**: Balance high-variance and low-variance players.

### Collaborative Features

If multiple users have access:

1. Add notes to document your reasoning for adjustments.
2. Create personally named scenarios (e.g., "John's High-RB Scenario").
3. Use the change history to track adjustments made by different users.

## Conclusion

The Fantasy Football Projections system combines statistical modeling with your expert judgment through manual adjustments and scenario planning. By following this guide, you can create sophisticated projections that account for various possibilities and help you make better fantasy football decisions.

For technical details about the projection methodology, please refer to the [Projection Methodology](projection_methodology.md) document.
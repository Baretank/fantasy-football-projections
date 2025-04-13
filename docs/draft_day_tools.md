# Draft Day Tools

This document provides an overview of the Draft Day Tools functionality in the Fantasy Football Projections application.

## Overview

The Draft Day Tools provide a set of utilities to assist during a fantasy football draft. Key features include:

- Player draft board with filtering and sorting options
- Tracking drafted/available/watched players
- Draft status updates (mark players as drafted, watched, or available)
- Draft progress statistics
- Rookie projection generation based on draft position
- Undo last draft pick functionality
- Multiple draft board support

## API Endpoints

The Draft Day Tools are accessible through the following API endpoints:

### Draft Board Operations

```
GET /api/draft/board
```
Retrieve the current draft board with optional filters.

Parameters:
- `status`: Filter by draft status (available, drafted, watched)
- `position`: Filter by player position (QB, RB, WR, TE)
- `team`: Filter by NFL team
- `order_by`: Field to order by (ranking, name, position, team, points)
- `limit`: Maximum number of players to return
- `offset`: Number of players to skip

```
GET /api/draft/progress
```
Get overall draft progress statistics.

```
POST /api/draft/reset
```
Reset all players to 'available' status.

```
POST /api/draft/undo
```
Undo the last draft pick by reverting the player with the highest draft order back to 'available'.

### Player Status Updates

```
PUT /api/draft/status/{player_id}
```
Update a player's draft status.

Parameters:
- `status`: The new status (available, drafted, watched)
- `fantasy_team`: The fantasy team that drafted the player (for 'drafted' status)
- `draft_order`: The order in which the player was drafted (for 'drafted' status)
- `create_projection`: Whether to create a projection for rookie players (default: false)

```
POST /api/draft/status/batch
```
Update draft status for multiple players in one operation.

Request body:
```json
{
  "updates": [
    {
      "player_id": "123",
      "status": "drafted",
      "fantasy_team": "Team 1",
      "draft_order": 1,
      "create_projection": true
    },
    {
      "player_id": "456",
      "status": "watched"
    }
  ]
}
```

### Draft Boards Management

```
POST /api/draft/boards
```
Create a new draft board.

Request body:
```json
{
  "name": "My Draft Board",
  "description": "2024 Draft",
  "season": 2024,
  "settings": {
    "number_of_teams": 12,
    "roster_spots": 15,
    "scoring_type": "half_ppr"
  }
}
```

```
GET /api/draft/boards
```
Get all draft boards.

Parameters:
- `active_only`: If true, only return active draft boards (default: true)

## Frontend Integration

The Draft Day Tools are integrated with the frontend through a dedicated module:

### Components

1. **DraftBoard Component**
   - Displays available, drafted, and watched players
   - Supports filtering by position, team, and status
   - Provides sorting functionality 
   - Includes search capability

2. **DraftControls Component**
   - Buttons for marking players as drafted/watched/available
   - Draft reset functionality
   - Undo last pick button

3. **DraftStats Component**
   - Shows draft progress statistics
   - Displays counts by position
   - Shows percentage of draft complete

### Usage Flow

1. **Preparation**
   - Ensure the database is properly populated with players and projections
   - Create baseline scenarios using the `create_baseline_scenario.py` script
   - Import rookie data if needed

2. **Start Draft**
   - Navigate to the Draft Board in the frontend
   - Use filters to focus on specific positions or teams
   - Sort by projected points to see top available players

3. **During Draft**
   - Mark players as drafted when they're selected by fantasy teams
   - Add fantasy team name and draft order position
   - Use the "watch" feature to track players of interest
   - Monitor draft statistics to track position trends

4. **Post-Draft**
   - Export draft results for analysis
   - Compare drafted players with projections from different scenarios
   - Analyze rookie draft positions and projected performance

## Technical Implementation

The Draft Day Tools are implemented using the following components:

### Backend

The core functionality is provided by the `DraftService` class, which handles:

- Player filtering and retrieval
- Draft status updates
- Draft progress tracking
- Integration with rookie projection services

Key models:
- `Player`: Contains draft_status, fantasy_team, and draft_order fields
- `DraftStatus`: Enum with AVAILABLE, DRAFTED, and WATCHED states 
- `DraftBoard`: Configuration for different draft sessions

### Frontend

The frontend implementation uses:
- React components for the UI
- Redux for state management
- API service for backend communication

## Rookie Projections

One of the key features of the Draft Day Tools is the ability to generate projections for rookie players based on their draft position:

1. When a rookie is marked as drafted, an optional parameter `create_projection=true` can be passed
2. The system uses the `RookieProjectionService` to generate a projection based on:
   - Player's position
   - Draft position
   - Position-specific rookie templates

The rookie projections are based on historical data patterns and account for the correlation between draft position and rookie performance.

## Example Usage

### Retrieving the Draft Board

```typescript
// Frontend API call
const fetchDraftBoard = async (filters = {}) => {
  const queryParams = new URLSearchParams(filters);
  const result = await fetchApi(`/draft/board?${queryParams.toString()}`);
  return result;
};

// Example with filters
const draftBoard = await fetchDraftBoard({
  position: 'QB',
  status: 'available',
  order_by: 'points'
});
```

### Marking a Player as Drafted

```typescript
// Frontend API call
const draftPlayer = async (playerId, teamName, draftPosition) => {
  const result = await fetchApi(`/draft/status/${playerId}`, 'PUT', {
    status: 'drafted',
    fantasy_team: teamName,
    draft_order: draftPosition,
    create_projection: true
  });
  return result;
};

// Example usage
await draftPlayer('player-123', 'Fantasy Team 1', 12);
```

## Troubleshooting

### Common Issues

1. **Players not appearing in draft board**
   - Check database population (run check_import.py)
   - Verify filters aren't too restrictive
   - Check browser console for API errors

2. **Draft status not updating**
   - Verify player_id is correct
   - Check for valid status values (available, drafted, watched)
   - Look for detailed error messages in response

3. **Rookie projections not generating**
   - Ensure player is marked as a rookie in the database
   - Verify rookie templates are initialized
   - Check backend logs for projection generation errors

## Future Enhancements

Planned enhancements for the Draft Day Tools include:

1. **Mock Draft Functionality**
   - Simulate drafts with AI-powered team selections
   - Generate mock draft analysis reports

2. **Value-Based Drafting (VBD)**
   - Implement VBD scoring to recommend optimal draft picks
   - Display positional scarcity metrics

3. **Live Draft Synchronization**
   - Integration with popular fantasy platforms like ESPN, Yahoo, etc.
   - Automatic tracking of draft picks from external sources

4. **Auction Draft Support**
   - Track player values and budget
   - Implement auction draft strategies
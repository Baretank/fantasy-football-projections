# Fantasy Football Projections API Documentation

## Overview

The Fantasy Football Projections API provides endpoints for managing player data, statistics, and projections. This API supports the creation, retrieval, and modification of fantasy football projections with support for scenario planning, statistical analysis, and manual overrides.

## Base URL

```
http://localhost:8000/api
```

## Authentication

Currently, the API does not require authentication. This will be implemented in future versions.

## Common Response Formats

### Success Response
```json
{
  "status": "success",
  "message": "Optional success message",
  "data": {
    // Response data
  }
}
```

### Error Response
```json
{
  "detail": "Error description",
  "code": "Optional error code"
}
```

## Endpoints

### Players

#### GET /players
Retrieve a list of players with optional filters.

Query Parameters:
- `position` (optional): Filter by position (QB, RB, WR, TE)
- `team` (optional): Filter by team abbreviation
- `status` (optional): Filter by status (active, injured, rookie)

Example Request:
```bash
curl -X GET "http://localhost:8000/api/players?position=QB&team=KC"
```

#### GET /players/{player_id}
Retrieve detailed information for a specific player.

Example Request:
```bash
curl -X GET "http://localhost:8000/api/players/123e4567-e89b-12d3-a456-426614174000"
```

#### GET /players/{player_id}/stats
Retrieve historical statistics for a player.

Query Parameters:
- `season` (optional): Filter by season year
- `include_games` (optional): Include game-by-game stats (boolean)

Example Request:
```bash
curl -X GET "http://localhost:8000/api/players/123e4567-e89b-12d3-a456-426614174000/stats?season=2023&include_games=true"
```

### Projections

#### GET /projections/player/{player_id}
Retrieve projections for a specific player.

Query Parameters:
- `scenario_id` (optional): Filter by scenario
- `include_variance` (optional): Include projection variance data (boolean)

Example Request:
```bash
curl -X GET "http://localhost:8000/api/projections/player/123e4567-e89b-12d3-a456-426614174000?include_variance=true"
```

#### POST /projections/player/{player_id}/base
Create a new baseline projection for a player.

Query Parameters:
- `season`: Season year to project
- `games` (optional): Projected games to play

Example Request:
```bash
curl -X POST "http://localhost:8000/api/projections/player/123e4567-e89b-12d3-a456-426614174000/base?season=2024&games=17"
```

#### PUT /projections/{projection_id}
Update a projection with adjustments.

Request Body:
```json
{
  "adjustments": {
    "snap_share": 1.1,
    "target_share": 0.95,
    "td_rate": 1.05
  }
}
```

Example Request:
```bash
curl -X PUT "http://localhost:8000/api/projections/456e7890-f12d-34e5-b678-426614174000" \
  -H "Content-Type: application/json" \
  -d '{"adjustments":{"snap_share":1.1,"target_share":0.95,"td_rate":1.05}}'
```

### Overrides

#### POST /overrides
Create a manual override for a specific stat.

Request Body:
```json
{
  "player_id": "123e4567-e89b-12d3-a456-426614174000",
  "projection_id": "456e7890-f12d-34e5-b678-426614174000",
  "stat_name": "pass_attempts",
  "manual_value": 550,
  "notes": "Adjusted based on new offensive coordinator"
}
```

Example Request:
```bash
curl -X POST "http://localhost:8000/api/overrides" \
  -H "Content-Type: application/json" \
  -d '{"player_id":"123e4567-e89b-12d3-a456-426614174000","projection_id":"456e7890-f12d-34e5-b678-426614174000","stat_name":"pass_attempts","manual_value":550,"notes":"Adjusted based on new offensive coordinator"}'
```

#### GET /overrides/player/{player_id}
Retrieve all overrides for a specific player.

Query Parameters:
- `scenario_id` (optional): Filter by scenario

Example Request:
```bash
curl -X GET "http://localhost:8000/api/overrides/player/123e4567-e89b-12d3-a456-426614174000"
```

#### DELETE /overrides/{override_id}
Remove a specific override.

Example Request:
```bash
curl -X DELETE "http://localhost:8000/api/overrides/789e0123-f45d-67e8-b901-426614174000"
```

### Scenarios

#### GET /scenarios
Retrieve all available projection scenarios.

Example Request:
```bash
curl -X GET "http://localhost:8000/api/scenarios"
```

#### POST /scenarios
Create a new projection scenario.

Request Body:
```json
{
  "name": "High Usage RBs",
  "description": "Scenario with increased workload for running backs",
  "clone_from_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

Example Request:
```bash
curl -X POST "http://localhost:8000/api/scenarios" \
  -H "Content-Type: application/json" \
  -d '{"name":"High Usage RBs","description":"Scenario with increased workload for running backs","clone_from_id":"123e4567-e89b-12d3-a456-426614174000"}'
```

#### GET /scenarios/{scenario_id}/projections
Retrieve all projections for a specific scenario.

Query Parameters:
- `position` (optional): Filter by position
- `team` (optional): Filter by team

Example Request:
```bash
curl -X GET "http://localhost:8000/api/scenarios/123e4567-e89b-12d3-a456-426614174000/projections?position=RB"
```

### Batch Operations

#### POST /batch/overrides
Apply the same override to multiple players.

Request Body:
```json
{
  "player_ids": [
    "123e4567-e89b-12d3-a456-426614174000",
    "456e7890-f12d-34e5-b678-426614174000"
  ],
  "stat_name": "pass_attempts",
  "value": 550,
  "notes": "Adjusted based on new offensive coordinator"
}
```

Example Request:
```bash
curl -X POST "http://localhost:8000/api/batch/overrides" \
  -H "Content-Type: application/json" \
  -d '{"player_ids":["123e4567-e89b-12d3-a456-426614174000","456e7890-f12d-34e5-b678-426614174000"],"stat_name":"pass_attempts","value":550,"notes":"Adjusted based on new offensive coordinator"}'
```

#### POST /batch/export
Export projection data for multiple players.

Request Body:
```json
{
  "player_ids": [
    "123e4567-e89b-12d3-a456-426614174000",
    "456e7890-f12d-34e5-b678-426614174000"
  ],
  "scenario_id": "789e0123-f45d-67e8-b901-426614174000",
  "format": "csv"
}
```

Example Request:
```bash
curl -X POST "http://localhost:8000/api/batch/export" \
  -H "Content-Type: application/json" \
  -d '{"player_ids":["123e4567-e89b-12d3-a456-426614174000","456e7890-f12d-34e5-b678-426614174000"],"scenario_id":"789e0123-f45d-67e8-b901-426614174000","format":"csv"}'
```

## Status Codes

- 200: Success
- 201: Created
- 204: No Content (successful deletion)
- 400: Bad Request
- 404: Not Found
- 422: Unprocessable Entity
- 500: Internal Server Error

## Rate Limiting

Currently, there are no rate limits implemented. This will be added in future versions.

## Data Models

### Player
```typescript
{
  player_id: string;
  name: string;
  team: string;
  position: string;
  status: string;
  rookie: boolean;
  created_at: string;
  updated_at: string;
}
```

### Projection
```typescript
{
  projection_id: string;
  player_id: string;
  scenario_id?: string;
  season: number;
  games: number;
  half_ppr: number;
  
  // Enhanced passing stats
  pass_attempts?: number;
  completions?: number;
  gross_pass_yards?: number;
  sacks?: number;
  sack_yards?: number;
  net_pass_yards?: number;
  pass_td?: number;
  interceptions?: number;
  
  // Efficiency metrics
  pass_att_pct?: number;
  comp_pct?: number;
  yards_per_att?: number;
  net_yards_per_att?: number;
  pass_td_rate?: number;
  int_rate?: number;
  sack_rate?: number;
  
  // Enhanced rushing stats
  carries?: number;
  gross_rush_yards?: number;
  fumbles_lost?: number;
  net_rush_yards?: number;
  rush_td?: number;
  
  // Rushing efficiency metrics
  car_pct?: number;
  yards_per_carry?: number;
  net_yards_per_carry?: number;
  fumble_rate?: number;
  rush_td_rate?: number;
  
  // Receiving stats
  targets?: number;
  receptions?: number;
  rec_yards?: number;
  rec_td?: number;
  
  // Receiving efficiency metrics
  tar_pct?: number;
  catch_pct?: number;
  yards_per_target?: number;
  rec_td_rate?: number;
  
  // Status flags
  has_overrides: boolean;
  is_fill_player: boolean;
  
  // Additional data
  variance?: ProjectionVariance;
  created_at: string;
  updated_at: string;
}
```

### ProjectionVariance
```typescript
{
  projection_id: string;
  variance_id: string;
  
  // Lower bounds (80% confidence interval)
  lower_pass_attempts?: number;
  lower_completions?: number;
  lower_pass_yards?: number;
  lower_pass_td?: number;
  lower_interceptions?: number;
  lower_carries?: number;
  lower_rush_yards?: number;
  lower_rush_td?: number;
  lower_targets?: number;
  lower_receptions?: number;
  lower_rec_yards?: number;
  lower_rec_td?: number;
  lower_half_ppr?: number;
  
  // Upper bounds (80% confidence interval)
  upper_pass_attempts?: number;
  upper_completions?: number;
  upper_pass_yards?: number;
  upper_pass_td?: number;
  upper_interceptions?: number;
  upper_carries?: number;
  upper_rush_yards?: number;
  upper_rush_td?: number;
  upper_targets?: number;
  upper_receptions?: number;
  upper_rec_yards?: number;
  upper_rec_td?: number;
  upper_half_ppr?: number;
}
```

### StatOverride
```typescript
{
  override_id: string;
  player_id: string;
  projection_id: string;
  stat_name: string;
  calculated_value: number;
  manual_value: number;
  notes?: string;
  created_at: string;
}
```

### PlayerStats
```typescript
{
  player_id: string;
  name: string;
  team: string;
  position: string;
  stats: {
    [season: number]: {
      weeks?: {
        [week: number]: {
          [stat_type: string]: number;
        };
      };
      [stat_type: string]: number;
    };
  };
}
```

### Scenario
```typescript
{
  scenario_id: string;
  name: string;
  description?: string;
  is_baseline: boolean;
  base_scenario_id?: string;
  created_at: string;
  updated_at: string;
}
```

## Error Handling

### Error Codes

The API uses standard HTTP status codes and includes detailed error messages in the response:

- `400 Bad Request`: Invalid input parameters or request body
- `404 Not Found`: Requested resource does not exist
- `422 Unprocessable Entity`: Request validation failed
- `500 Internal Server Error`: Server-side error

### Error Response Format

```json
{
  "detail": "Detailed error message",
  "code": "ERROR_CODE",
  "fields": {
    "field_name": "Field-specific error message"
  }
}
```

## Best Practices

### Request Rate

While there are currently no rate limits, clients should:
- Implement exponential backoff for failed requests
- Cache responses when appropriate
- Batch requests when possible

### Data Validation

Before submitting:
- Ensure all required fields are provided
- Validate data types match the schema
- Check value ranges for numerical fields

### Response Handling

Clients should:
- Handle all possible HTTP status codes
- Parse error responses for detailed messages
- Implement proper error recovery

## Pagination

For endpoints returning lists, the API supports pagination using:

Query Parameters:
- `skip`: Number of items to skip (default: 0)
- `limit`: Maximum number of items to return (default: 100, max: 1000)

Response Headers:
- `X-Total-Count`: Total number of items
- `X-Page-Count`: Total number of pages
- `X-Current-Page`: Current page number

Example:
```bash
curl -X GET "http://localhost:8000/api/players?skip=20&limit=10"
```

## Caching

The API supports ETag-based caching. Clients should:
- Store the ETag header from responses
- Include If-None-Match header in subsequent requests
- Handle 304 Not Modified responses appropriately

## Versioning

The API version is included in the response headers:
- `X-API-Version`: Current API version

Future breaking changes will be introduced with a new major version number in the URL:
```
/api/v2/players
```

## Security Recommendations

While authentication is not currently required, clients should:
- Use HTTPS for all requests
- Sanitize all user inputs
- Implement request timeouts
- Monitor for suspicious activity

## Support

For API support:
- Email: api-support@example.com
- Documentation: http://localhost:8000/docs
- OpenAPI Spec: http://localhost:8000/openapi.json

## Changelog

### Version 0.3.0 (Current)
- Added projection variance endpoints
- Added rookie projection support
- Enhanced batch operations
- Implemented override tracking system
- Added scenario management endpoints
- Added data export capabilities
- Improved caching for performance optimization

### Version 0.2.0
- Enhanced data models with net yardage calculations
- Added manual override system
- Implemented scenario planning functionality
- Added fill player generation
- Expanded statistical metrics

### Version 0.1.0
- Initial API release
- Basic CRUD operations for players and projections
- Statistical analysis endpoints
- Basic scenario support

### Planned Features
- Authentication and authorization
- Rate limiting
- Webhooks for data updates
- Advanced statistical analysis
- Real-time updates
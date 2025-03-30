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

### Rookies

#### POST /rookies/from-draft
Create rookie projections based on draft position.

Request Body:
```json
{
  "name": "Trevor Lawrence",
  "team": "JAX",
  "position": "QB",
  "draft_position": 1,
  "draft_round": 1,
  "college": "Clemson",
  "height": 78,
  "weight": 220,
  "season": 2024
}
```

Example Request:
```bash
curl -X POST "http://localhost:8000/api/rookies/from-draft" \
  -H "Content-Type: application/json" \
  -d '{"name":"Trevor Lawrence","team":"JAX","position":"QB","draft_position":1,"draft_round":1,"college":"Clemson","height":78,"weight":220,"season":2024}'
```

#### GET /rookies/templates
Retrieve rookie projection templates.

Query Parameters:
- `position` (optional): Filter by position

Example Request:
```bash
curl -X GET "http://localhost:8000/api/rookies/templates?position=WR"
```

## New Features (v0.3.0)

### Projection Variance

#### GET /projections/variance/{projection_id}
Retrieve variance data for a specific projection.

Query Parameters:
- `confidence_level` (optional): Confidence interval level (50, 80, 90, 95)

Example Request:
```bash
curl -X GET "http://localhost:8000/api/projections/variance/456e7890-f12d-34e5-b678-426614174000?confidence_level=80"
```

### Team Statistics

#### GET /teams/stats
Retrieve team-level offensive statistics.

Query Parameters:
- `team` (optional): Filter by team abbreviation
- `season` (optional): Filter by season

Example Request:
```bash
curl -X GET "http://localhost:8000/api/teams/stats?team=KC&season=2024"
```

#### PUT /teams/stats/{team_stat_id}
Update team-level offensive statistics.

Request Body:
```json
{
  "adjustments": {
    "plays_per_game": 68,
    "pass_percentage": 0.62,
    "yards_per_attempt": 7.8
  }
}
```

Example Request:
```bash
curl -X PUT "http://localhost:8000/api/teams/stats/456e7890-f12d-34e5-b678-426614174000" \
  -H "Content-Type: application/json" \
  -d '{"adjustments":{"plays_per_game":68,"pass_percentage":0.62,"yards_per_attempt":7.8}}'
```

## Current Status and Progress

The Fantasy Football Projections API has been significantly enhanced through several development cycles. Current implementation status:

### Completed Features
- ✅ Core CRUD operations for players, projections, and statistics
- ✅ Advanced projection engine with efficiency metrics
- ✅ Statistical variance and confidence intervals
- ✅ Scenario planning system
- ✅ Manual override tracking
- ✅ Batch operations
- ✅ Data export capabilities
- ✅ Rookie projection system with draft-based templates
- ✅ Team-level constraint management
- ✅ Response caching for improved performance
- ✅ Enhanced error handling and validation

### In Progress
- 🔄 Starter/Backup and Status Tags UI components
- 🔄 OAuth-based authentication system
- 🔄 Enhanced audit logging
- 🔄 Automated test suite for API endpoints

### Future Roadmap
- ⏳ Real-time notification system using WebSockets
- ⏳ Webhook support for external integrations
- ⏳ Advanced rate limiting
- ⏳ User role-based permissions
- ⏳ Data visualization endpoints

## Status Codes

- 200: Success
- 201: Created
- 204: No Content (successful deletion)
- 400: Bad Request
- 404: Not Found
- 422: Unprocessable Entity
- 500: Internal Server Error

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
- Added team-level adjustment endpoints
- Enhanced data validation

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
# Fantasy Football Projections API Documentation

## Overview

The Fantasy Football Projections API provides endpoints for managing player data, statistics, and projections. This API supports the creation, retrieval, and modification of fantasy football projections with support for scenario planning and statistical analysis.

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

Example Request:
```bash
curl -X GET "http://localhost:8000/api/players/123e4567-e89b-12d3-a456-426614174000/stats?season=2023"
```

### Projections

#### GET /projections/player/{player_id}
Retrieve projections for a specific player.

Query Parameters:
- `scenario_id` (optional): Filter by scenario

Example Request:
```bash
curl -X GET "http://localhost:8000/api/projections/player/123e4567-e89b-12d3-a456-426614174000"
```

#### POST /projections/player/{player_id}/base
Create a new baseline projection for a player.

Query Parameters:
- `season`: Season year to project

Example Request:
```bash
curl -X POST "http://localhost:8000/api/projections/player/123e4567-e89b-12d3-a456-426614174000/base?season=2024"
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

## Status Codes

- 200: Success
- 400: Bad Request
- 404: Not Found
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
  
  // Position-specific stats
  pass_attempts?: number;
  completions?: number;
  pass_yards?: number;
  pass_td?: number;
  interceptions?: number;
  carries?: number;
  rush_yards?: number;
  rush_td?: number;
  targets?: number;
  receptions?: number;
  rec_yards?: number;
  rec_td?: number;
  
  // Usage metrics
  snap_share?: number;
  target_share?: number;
  rush_share?: number;
  redzone_share?: number;
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

### Version 0.1.0 (Current)
- Initial API release
- Basic CRUD operations for players and projections
- Statistical analysis endpoints
- Scenario planning support

### Planned Features
- Authentication and authorization
- Rate limiting
- Webhooks for data updates
- Advanced statistical analysis
- Bulk operations
- Real-time updates
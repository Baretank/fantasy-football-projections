# Rate Limiting for PFR Web Scraping

This document explains the rate limiting mechanisms implemented in the Fantasy Football Projections application to ensure responsible web scraping from Pro Football Reference (PFR).

## Overview

Web scraping must be done responsibly to:
1. Avoid overloading the target website's servers
2. Prevent IP address blocking or throttling
3. Ensure reliable data collection
4. Be a good internet citizen

## Rate Limiting Implementation

The application implements multiple layers of rate limiting:

### 1. Randomized Request Delays

- Each request includes a random delay between requests (configurable)
- Default: 0.8s to 1.2s between individual requests

### 2. Concurrency Control

- Limits the number of concurrent requests using a semaphore
- Default: Maximum 3 concurrent requests
- Prevents overwhelming the server with parallel connections

### 3. Exponential Backoff

- When rate limiting is detected (HTTP 429 responses), implements exponential backoff
- Wait time increases with each retry: `wait_time = (2^attempt) * min_delay`
- Maximum 3 retry attempts by default

### 4. Circuit Breaker Pattern

- Monitors for rate limiting events
- Temporarily stops all requests if too many rate limiting errors occur
- Opens circuit (pause all scraping) after 5 rate limit events
- Automatically resets after 2 minutes (configurable)

### 5. Batch Processing

- Players are processed in batches with delays between batches
- Default: 5 players per batch
- Default: 3s delay between batches
- Allows controlled bursts of activity with rest periods

## Configuration

All rate limiting parameters are configurable via command-line arguments:

```
python -m backend.scripts.upload_season --season 2024 [options]

Options:
  --batch-size INT        Number of players per batch (default: 5)
  --batch-delay FLOAT     Seconds between batches (default: 3.0)
  --min-delay FLOAT       Minimum seconds between requests (default: 0.8)
  --max-delay FLOAT       Maximum seconds between requests (default: 1.2)
  --max-concurrent INT    Maximum concurrent requests (default: 3)
```

## Best Practices

1. **Start Conservative**: Begin with conservative rate limiting and gradually increase if needed
2. **Monitor Responses**: Watch for rate limiting responses and adjust parameters
3. **Off-Peak Hours**: Run large imports during off-peak hours
4. **Cache Results**: Cache responses when possible to reduce duplicate requests
5. **Respect robots.txt**: Always check and follow the site's robots.txt file

## Example Usage

For very conservative scraping:
```
python -m backend.scripts.upload_season --season 2024 --batch-size 3 --batch-delay 5.0 --min-delay 1.0 --max-delay 2.0 --max-concurrent 2
```

For slightly faster scraping (use cautiously):
```
python -m backend.scripts.upload_season --season 2024 --batch-size 10 --batch-delay 2.0 --min-delay 0.5 --max-delay 1.0 --max-concurrent 5
```
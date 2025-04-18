# Fantasy Football Services

This directory contains all the service modules for the Fantasy Football Projections application.

## Services Structure

- **adapters/**: External data source adapters
- **batch_service.py**: Handles batch operations
- **cache_service.py**: Caching functionality
- **data_import_service.py**: Data import operations
- **data_service.py**: Core data operations
- **data_validation.py**: Data validation utilities
- **draft_service.py**: Draft day functionality
- **nfl_data_import_service.py**: NFL data import operations
- **override_service.py**: Projection override functionality
- **player_import_service.py**: Player import operations
- **projection_service.py**: Core projection calculations
- **projection_variance_service.py**: Projection variance calculations
- **query_service.py**: Database query utilities
- **rookie_import_service.py**: Rookie import operations
- **rookie_projection_service.py**: Rookie projection calculations
- **scenario_service.py**: Scenario management
- **team_stat_service.py**: Team statistics operations
- **typing.py**: Common type definitions and utilities

## Type System

The `typing.py` module provides centralized type definitions for consistent type safety across the application. This includes:

- Common type aliases
- TypedDict definitions for complex structures
- Utility functions for safe type operations

### Using the Type Definitions

Import types from the typing module:

```python
from backend.services.typing import (
    StatsDict, 
    AdjustmentDict, 
    PlayerDict,
    safe_float,
    safe_dict_get
)

# Use in function signatures
def update_projection(
    self, 
    player_id: str, 
    adjustments: AdjustmentDict
) -> Optional[Projection]:
    # Function implementation
    pass
```

### Type Safety Helpers

The typing module provides helper functions for safe type operations:

- `safe_float(value)`: Safely convert a value to float
- `safe_dict_get(dict, key, default)`: Safely access dictionary values
- `safe_calculate(numerator, denominator, default)`: Safely perform division

### TypedDict Definitions

The module includes TypedDict definitions for complex structures:

```python
# For player statistics
class StatsDict(TypedDict, total=False):
    pass_attempts: float
    completions: float
    pass_yards: float
    # ... more fields

# For projection adjustments
class AdjustmentDict(TypedDict, total=False):
    pass_volume: float
    rush_volume: float
    # ... more fields

# For team statistics
class TeamStatsDict(TypedDict, total=False):
    pass_attempts: float
    rush_attempts: float
    # ... more fields
```

## Type Safety Patterns

Throughout the codebase, we use consistent patterns for type safety:

### 1. None Checking Before Operations

Always check for None before performing operations:

```python
if value is not None:
    result = value * factor
else:
    result = default_value
```

### 2. Safe Dictionary Access

Use safe dictionary access patterns:

```python
# Use safe_dict_get helper
value = safe_dict_get(data, "key", default=0.0)

# Or use dict.get() with default
value = data.get("key", 0.0)
```

### 3. Explicit Type Casting

Use explicit type casting to ensure correct types:

```python
# Cast to float for numeric operations
value = float(input_value) * multiplier

# Use safe_float for values that might be None
value = safe_float(input_value, default=0.0) * multiplier
```

### 4. TypedDict for Complex Structures

Use TypedDict for complex nested structures:

```python
from backend.services.typing import BatchResultDict

def process_batch(items: List[str]) -> BatchResultDict:
    result: BatchResultDict = {
        "success": 0,
        "failure": 0,
        "failed_items": []
    }
    # Process items...
    return result
```

## Best Practices

1. **Use the centralized types**: Import from `typing.py` rather than redefining types
2. **Check for None values**: Always check for None before arithmetic operations
3. **Use explicit casting**: Use `float()` or `safe_float()` for values used in calculations
4. **Type annotations**: Add type annotations to all function parameters and return values
5. **Defensive programming**: Use dictionary safe access patterns with proper defaults
6. **Local variable typing**: Add type annotations to local variables for clarity
7. **TypedDict for dictionaries**: Use TypedDict for dictionaries with consistent structure
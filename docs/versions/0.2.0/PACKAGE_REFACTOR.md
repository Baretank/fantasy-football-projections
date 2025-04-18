# Package Structure Refactoring Plan

## Overview

This document tracks our progress in improving the package structure and type safety of the codebase.

## Current Status (April 2025)

We've made significant progress in implementing a robust type safety system:

1. ✅ Created a centralized typing system with TypedDict definitions
2. ✅ Implemented TypedDataFrame wrapper for safer pandas operations
3. ✅ Updated core service modules with type-safe implementations
4. ✅ Fixed module resolution issues for mypy type checking
5. ✅ Added proper error handling and null safety throughout the codebase

**Next priority:** Address TypedDict compatibility issues and fix the remaining type errors in team_stat_service.py and projection_service.py.

## Achievements

### 1. Import Standardization
- ✅ Standardized on absolute imports (`from backend.x import y`) throughout the codebase
- ✅ Added/enhanced all required `__init__.py` files
- ✅ Created analysis and refactoring tools
- ✅ Updated mypy configuration for proper module resolution

### 2. Centralized Typing System
- ✅ Created `backend/services/typing.py` with common type definitions
- ✅ Defined TypedDict classes for complex nested structures
- ✅ Added utility functions for safe type operations:
  - `safe_float()`: Safely converts values to float with default handling
  - `safe_dict_get()`: Safely gets values from dictionaries with None checking
  - `safe_calculate()`: Safely performs division with zero denominators handling

### 3. Pandas Type Safety
- ✅ Created comprehensive `typing_pandas.py` module with:
  - TypedDataFrame wrapper class for safe DataFrame access
  - Safe accessor methods (get_float, get_int, get_str)
  - Series conversion utilities (series_to_float, series_to_int, series_to_str)
  - convert_to_typed_dict for DataFrame to TypedDict conversion
- ✅ Updated adapter modules to use TypedDataFrame
- ✅ Enhanced data_validation.py with ValidationResultDict TypedDict
- ✅ Refactored data_import_service.py to use TypedDataFrame
- ✅ Enhanced rookie_import_service.py with comprehensive type safety
- ✅ Updated player_import_service.py with robust type safety patterns

### 4. Service Module Improvements
- ✅ Fixed key service modules with proper typing:
  - projection_service.py, team_stat_service.py, batch_service.py
  - cache_service.py, override_service.py, draft_service.py
  - data_service.py, query_service.py, scenario_service.py
  - nfl_data_import_service.py, projection_variance_service.py

### 5. Error Handling Enhancements
- ✅ Added robust error handling for all pandas operations
- ✅ Implemented proper null safety with pd.isna() checks
- ✅ Added default value handling throughout the codebase
- ✅ Fixed potential division by zero issues in calculations

## Typing Patterns Established

- **Safe numerics**: Using `safe_float()` for consistent numeric conversion
- **Dictionary access**: Using `safe_dict_get()` with default values
- **Type casting**: Using explicit `cast()` for type inference assistance
- **Defensive property access**: Checking for `hasattr()` before accessing attributes
- **TypedDict hierarchies**: Creating related TypedDict classes matching domain model
- **Return type annotation**: Explicitly typing method returns
- **Null safety**: Consistently handling None values throughout the codebase
- **Pandas operations**: Using wrapper functions for safer DataFrame/Series operations

## Remaining Issues

### 1. Inconsistent TypedDict Usage
- Need to standardize when TypedDict should be used vs. Dict[str, Type]

### 2. Service Modules Requiring Updates
- ✅ Updated player_import_service.py with centralized typing system

### 3. Type Checking Improvements
- ✅ Fixed module resolution issues:
  - Run mypy from project root using Python module mechanism:
    ```
    cd /path/to/fantasy-football-projections && python -m mypy backend/services/...
    ```
  - Installed missing stub packages (types-python-dateutil)
- ✅ Fixed no_implicit_optional issues:
  - Updated TypedDataFrame utilities to use Optional type annotations
  - Made None defaults compatible with type system
- ✅ Enhanced TypedDict compatibility:
  - Updated safe_dict_get to handle both Dict and TypedDict objects
  - Added Union type for better compatibility
- ❌ Remaining type issues:
  - TypedDict key access using string literals
  - TypedDataFrame specific attributes and methods
  - Complex type conversion issues

## Type Checking Guidelines

### Running mypy correctly
To properly run mypy on this codebase:

```bash
# Always run from project root (not from backend directory)
cd /path/to/fantasy-football-projections

# Check specific files
python -m mypy backend/services/specific_file.py

# Check entire services directory
python -m mypy backend/services/

# Check entire backend
python -m mypy backend/
```

### Common Type Errors and How to Fix Them

1. **TypedDict with safe_dict_get**:
   - Error: `Argument 1 to "safe_dict_get" has incompatible type "SomeTypedDict"; expected "dict[str, Any]"`
   - Fix: Either use type casting with `cast(Dict[str, Any], typed_dict_var)` or pass raw dictionaries
   - Note: Our safe_dict_get now accepts both Dict and dict types for better compatibility

2. **No implicit optional**:
   - Error: `Incompatible default for argument "x" (default has type "None", argument has type "T")`
   - Fix: Use `Optional[T]` as the parameter type when a parameter can be None
   - Example: `def function(param: Optional[int] = None)` instead of `def function(param: int = None)`

3. **Pandas object attribute access**:
   - Error: `"TypedDataFrame[Any]" has no attribute "x"`
   - Fix: Access the underlying DataFrame with `.df.x`
   - Example: `typed_df.df.iloc[0]` instead of `typed_df.iloc[0]`

4. **TypedDict as variable error**:
   - Error: `Variable "typing.TypedDict" is not valid as a type`
   - Fix: TypedDict can't be used directly as a type - use Dict or specific TypedDict classes

5. **TypedDict key must be a string literal**:
   - Error: `TypedDict key must be a string literal; expected one of...`
   - Fix: Use known string literals when accessing TypedDict keys
   - For dynamic access, try using Dict[str, Any] instead of TypedDict

## Completed Type Safety Improvements

1. **Refactored service modules with TypedDataFrame**:
   - ✅ Enhanced player_import_service.py with TypedDataFrame and safe accessors
   - ✅ Implemented proper error handling for CSV file imports
   - ✅ Added robust type conversion with defensive programming
   - ✅ Fixed type annotations throughout the module

2. **Enhanced TypedDataFrame implementation**:
   - ✅ Fixed TypedDataFrame to implement Sized protocol for len() support
   - ✅ Added iterrows() method to TypedDataFrame for compatibility with pandas
   - ✅ Added proper Optional type annotations to prevent implicit optional warnings
   - ✅ Added runtime_checkable protocols for better type safety

3. **Fixed module resolution issues**:
   - ✅ Established correct pattern for running mypy: `cd project_root && python -m mypy backend/...`
   - ✅ Added missing type stubs (types-python-dateutil)
   - ✅ Fixed imports in typing.py to remove unused imports

## Remaining Type Safety Tasks

1. **Fix TypedDict compatibility issues**:
   - Use cast(Dict[str, Any], typed_dict) when passing TypedDict to safe_dict_get
   - Replace dynamic key access with string literals where possible
   - Create functions to safely convert between TypedDict and Dict

2. **Update team_stat_service.py with TypedDataFrame**:
   - Fix TypedDict key string literal issues
   - Address "object" has no attribute "items" errors
   - Correct incompatible assignment types for PositionUsageDict
   - Use proper TypedDataFrame operations throughout

3. **Update projection_service.py with safer type handling**:
   - Fix float() conversion on complex union types 
   - Use safe_float() instead of direct float() calls
   - Fix numeric operations on Optional values

4. **General code quality improvements**:
   - Fix widespread linting issues across the codebase:
     - Remove unused imports (many F401 violations)
     - Fix whitespace issues (W291, W293 violations)
     - Address bare except clauses (E722 violations)
     - Fix line length issues and formatting
     - Address function and class spacing (E302, E305 violations)

## Next Steps

1. ❌ Create clear guidelines for when TypedDict should be used
2. ❌ Add test cases for edge conditions in TypedDataFrame
3. ❌ Create a comprehensive typing guide with examples
4. ❌ Implement SQLAlchemy ORM type hints for database operations
5. ❌ Add automated linting and formatting to pre-commit hooks

## Future Work

1. **Implement comprehensive type checking**:
   - Create a script to run mypy in the correct context across all modules
   - Add type checking to CI/CD pipeline
   - Create a type safety scoring system to track progress

2. **Develop comprehensive safe utility functions**:
   - Create TypedDict utility functions to safely convert between formats
   - Add runtime type validation helpers for critical operations
   - Extend TypedDataFrame with more pandas-compatible methods

3. **Database and ORM type safety**:
   - Create type-safe wrapper for SQLAlchemy operations
   - Add transaction safety patterns with proper typing
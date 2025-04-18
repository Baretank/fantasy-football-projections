"""
Pandas Type Safety Utilities

Type-safe utilities for working with pandas DataFrame and Series objects.
This module improves type safety and error handling when working with pandas
objects throughout the fantasy football projections system.
"""

from typing import Any, TypeVar, Dict, Union, Generic, List, Optional, Protocol, runtime_checkable
import pandas as pd
from pandas import Series, DataFrame

from backend.services.typing import safe_float

# Type variables for generic pandas operations
T = TypeVar("T")
U = TypeVar("U")


def safe_series_get(series: Series, key: str, default: Optional[T] = None) -> Union[Any, T]:
    """Safely get a value from a pandas Series with proper typing.

    Args:
        series: The pandas Series to extract data from
        key: The column/key to access
        default: Default value to return if key doesn't exist or value is NaN

    Returns:
        The value from the Series or the default value
    """
    if series is None:
        return default

    if key not in series or pd.isna(series[key]):
        return default
    return series[key]


def series_to_float(series: Series, key: str, default: float = 0.0) -> float:
    """Convert a pandas Series value to float with proper error handling.

    Args:
        series: The pandas Series to extract data from
        key: The column/key to access
        default: Default value to return if conversion fails

    Returns:
        The value as float or the default value
    """
    value = safe_series_get(series, key)
    return safe_float(value, default)


def series_to_int(series: Series, key: str, default: int = 0) -> int:
    """Convert a pandas Series value to int with proper error handling.

    Args:
        series: The pandas Series to extract data from
        key: The column/key to access
        default: Default value to return if conversion fails

    Returns:
        The value as int or the default value
    """
    value = safe_series_get(series, key)
    try:
        if value is None or pd.isna(value):
            return default
        return int(float(value))
    except (ValueError, TypeError):
        return default


def series_to_str(series: Series, key: str, default: str = "") -> str:
    """Convert a pandas Series value to string with proper error handling.

    Args:
        series: The pandas Series to extract data from
        key: The column/key to access
        default: Default value to return if conversion fails

    Returns:
        The value as string or the default value
    """
    value = safe_series_get(series, key)
    if value is None or pd.isna(value):
        return default
    return str(value)


@runtime_checkable
class Sized(Protocol):
    """Protocol for objects that have a __len__ method."""

    def __len__(self) -> int: ...


class TypedDataFrame(Generic[T], Sized):
    """A wrapper for pandas DataFrame with typed column access methods."""

    def __init__(self, df: DataFrame):
        """Initialize with a pandas DataFrame."""
        self.df = df

    def __len__(self) -> int:
        """Implement the Sized protocol for len() support."""
        return len(self.df)

    def iterrows(self):
        """Implement iterrows to match pandas DataFrame interface."""
        return self.df.iterrows()

    def get_float(self, row_idx: int, col: str, default: float = 0.0) -> float:
        """Get a float value from the DataFrame with proper type handling."""
        try:
            value = self.df.iloc[row_idx][col]
            if pd.isna(value):
                return default
            return float(value)
        except (KeyError, ValueError, TypeError, IndexError):
            return default

    def get_int(self, row_idx: int, col: str, default: int = 0) -> int:
        """Get an int value from the DataFrame with proper type handling."""
        try:
            value = self.df.iloc[row_idx][col]
            if pd.isna(value):
                return default
            return int(float(value))
        except (KeyError, ValueError, TypeError, IndexError):
            return default

    def get_str(self, row_idx: int, col: str, default: str = "") -> str:
        """Get a string value from the DataFrame with proper type handling."""
        try:
            value = self.df.iloc[row_idx][col]
            if pd.isna(value):
                return default
            return str(value)
        except (KeyError, ValueError, TypeError, IndexError):
            return default

    def filter_rows(self, condition: Series) -> "TypedDataFrame[T]":
        """Filter rows with proper type preservation."""
        return TypedDataFrame(self.df[condition])

    def is_empty(self) -> bool:
        """Check if the DataFrame is empty."""
        return len(self.df) == 0

    def row_count(self) -> int:
        """Get the number of rows in the DataFrame."""
        return len(self.df)

    def has_column(self, col: str) -> bool:
        """Check if a column exists in the DataFrame."""
        return col in self.df.columns

    def get_row_as_dict(self, row_idx: int, columns: List[str]) -> Dict[str, Any]:
        """Get a row as a dictionary with only the specified columns."""
        try:
            row = self.df.iloc[row_idx]
            return {col: safe_series_get(row, col) for col in columns if col in row.index}
        except IndexError:
            return {}


def convert_to_typed_dict(
    row: Series, mapping: Dict[str, str], converters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convert a pandas Series row to a typed dictionary using a mapping.

    Args:
        row: The pandas Series row
        mapping: Dict mapping output keys to input column names
        converters: Dict of converter functions for specific output keys

    Returns:
        A typed dictionary with converted values
    """
    if converters is None:
        converters = {}

    result: Dict[str, Any] = {}

    for out_key, in_key in mapping.items():
        # Skip if input column doesn't exist
        if in_key not in row:
            continue

        value = row[in_key]

        # Apply converter if exists for this key
        if out_key in converters and callable(converters[out_key]):
            try:
                result[out_key] = converters[out_key](value)
            except Exception:
                # Use default conversion on failure
                if pd.isna(value):
                    result[out_key] = None
                else:
                    result[out_key] = value
        else:
            # Default conversion
            if pd.isna(value):
                result[out_key] = None
            else:
                result[out_key] = value

    return result

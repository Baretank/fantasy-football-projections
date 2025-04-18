"""
NFL Data adapters package.
"""

from backend.services.adapters.nfl_api_adapter import NFLApiAdapter
from backend.services.adapters.nfl_data_py_adapter import NFLDataPyAdapter
from backend.services.adapters.web_data_adapter import WebDataAdapter

__all__ = [
    "NFLApiAdapter",
    "NFLDataPyAdapter",
    "WebDataAdapter",
]

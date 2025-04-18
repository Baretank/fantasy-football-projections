#!/usr/bin/env python3
"""Setup script for the backend package."""

from setuptools import setup, find_packages

setup(
    name="fantasy-football-backend",
    version="0.1.0",
    description="Fantasy Football Projections Backend",
    author="Fantasy Football Team",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pandas",
        "numpy",
        "psutil",
        "tabulate",
    ],
    extras_require={
        "dev": [
            "black",
            "flake8",
            "mypy",
            "pytest",
            "pytest-asyncio",
            "isort",
        ],
    },
)
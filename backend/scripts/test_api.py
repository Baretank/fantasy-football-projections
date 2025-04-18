#!/usr/bin/env python
import requests
import json
import argparse
from pathlib import Path


def test_api_endpoints():
    parser = argparse.ArgumentParser(description="Test Fantasy Football API endpoints")
    parser.add_argument("--host", default="localhost", help="API host (default: localhost)")
    parser.add_argument("--port", default="8000", help="API port (default: 8000)")
    parser.add_argument(
        "--endpoint",
        default="players/rookies",
        help="API endpoint to test (default: players/rookies)",
    )
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}/api"
    endpoint_url = f"{base_url}/{args.endpoint}"

    print(f"Testing API endpoint: {endpoint_url}")

    try:
        response = requests.get(endpoint_url)
        print(f"Status code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"Found {len(data)} items")
                if data:
                    if "name" in data[0]:
                        print(f"First item: {data[0]['name']}")
                    else:
                        print(f"First item: {json.dumps(data[0], indent=2)[:200]}...")
            else:
                print(f"Response data: {json.dumps(data, indent=2)[:200]}...")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")


if __name__ == "__main__":
    test_api_endpoints()

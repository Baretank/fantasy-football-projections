#!/usr/bin/env python
import requests


def test_explicit():
    """Direct test of the rookies endpoint with explicit URL construction"""
    # Try different URL constructions
    urls = [
        "http://localhost:8000/api/players/rookies",
        "http://localhost:8000/api/players/rookies/",
        "http://localhost:8000/api/players?status=Rookie",
        "http://127.0.0.1:8000/api/players/rookies",
    ]

    print("Testing multiple URL formats:")
    for url in urls:
        print(f"\nTesting URL: {url}")
        try:
            response = requests.get(url)
            print(f"Status code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    print(f"Found {len(data)} items")
                    if data:
                        print(f"First item: {data[0]['name'] if 'name' in data[0] else data[0]}")
                else:
                    print(f"Response: {data}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Exception: {e}")

    # Test other endpoints to see if they're working
    print("\nTesting main players endpoint:")
    try:
        response = requests.get("http://localhost:8000/api/players")
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Players found: {data['pagination']['total_count']}")
    except Exception as e:
        print(f"Exception: {e}")


if __name__ == "__main__":
    test_explicit()

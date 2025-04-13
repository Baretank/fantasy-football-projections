"""Test script to check API endpoints directly."""
import requests
import sys
import json

def test_scenarios_endpoint():
    """Test the scenarios endpoint directly."""
    try:
        print("Testing scenarios endpoint: http://127.0.0.1:8000/api/scenarios")
        response = requests.get("http://127.0.0.1:8000/api/scenarios")
        
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Success! Found {len(data)} scenarios")
                for scenario in data:
                    print(f"- {scenario.get('name')} (ID: {scenario.get('scenario_id')})")
            except json.JSONDecodeError:
                print("Error: Could not parse JSON response")
                print("Raw response:", response.text[:200], "..." if len(response.text) > 200 else "")
        else:
            print(f"Error: Status code {response.status_code}")
            print("Response:", response.text[:200], "..." if len(response.text) > 200 else "")
    except Exception as e:
        print(f"Connection error: {str(e)}")

if __name__ == "__main__":
    print("API Endpoint Tester")
    test_scenarios_endpoint()
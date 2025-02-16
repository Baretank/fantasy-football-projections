import pandas as pd
import json
from datetime import datetime
from pathlib import Path
import argparse
import sys

def convert_excel_to_json(excel_file: str, output_file: str, force: bool = False):
    """
    Convert rookie projections Excel file to rookies.json format.
    """
    # Check if output file exists
    output_path = Path(output_file)
    if output_path.exists() and not force:
        print(f"Warning: {output_file} already exists!")
        response = input("Do you want to overwrite it? (y/N): ").lower()
        if response != 'y':
            print("Aborting conversion.")
            return
    
    try:
        # Read Excel file
        df = pd.read_excel(excel_file)
        print("Available columns:", df.columns.tolist())
        
    except Exception as e:
        print(f"Error reading Excel file: {str(e)}")
        return
    
    # Initialize rookies list
    rookies = []
    
    # Process each row
    for _, row in df.iterrows():
        rookie = {
            "name": row["Name"],
            "position": row["Pos"],
            "team": row["Team"],
            "draft_position": int(float(row["ADP"])) if pd.notna(row["ADP"]) else 0,
            "projected_stats": {
                "games": int(row["Gm"]) if pd.notna(row["Gm"]) else 17
            }
        }
        
        try:
            # Add position-specific stats based on position
            if row["Pos"] == "QB":
                rookie["projected_stats"].update({
                    "pass_attempts": int(row["PaATT"]) if pd.notna(row["PaATT"]) else 0,
                    "completions": int(row["Comp"]) if pd.notna(row["Comp"]) else 0,
                    "pass_yards": int(row["PaYD"]) if pd.notna(row["PaYD"]) else 0,
                    "pass_td": int(row["PaTD"]) if pd.notna(row["PaTD"]) else 0,
                    "interceptions": int(row["INT"]) if pd.notna(row["INT"]) else 0,
                    "rush_attempts": int(row["Car"]) if pd.notna(row["Car"]) else 0,
                    "rush_yards": int(row["RuYD"]) if pd.notna(row["RuYD"]) else 0,
                    "rush_td": int(row["RuTD"]) if pd.notna(row["RuTD"]) else 0
                })
            elif row["Pos"] in ["WR", "TE"]:
                rookie["projected_stats"].update({
                    "targets": int(row["Tar"]) if pd.notna(row["Tar"]) else 0,
                    "receptions": int(row["Rec"]) if pd.notna(row["Rec"]) else 0,
                    "rec_yards": int(row["ReYD"]) if pd.notna(row["ReYD"]) else 0,
                    "rec_td": int(row["ReTD"]) if pd.notna(row["ReTD"]) else 0,
                    "rush_attempts": int(row["Car"]) if pd.notna(row["Car"]) else 0,
                    "rush_yards": int(row["RuYD"]) if pd.notna(row["RuYD"]) else 0,
                    "rush_td": int(row["RuTD"]) if pd.notna(row["RuTD"]) else 0
                })
            elif row["Pos"] == "RB":
                rookie["projected_stats"].update({
                    "carries": int(row["Car"]) if pd.notna(row["Car"]) else 0,
                    "rush_yards": int(row["RuYD"]) if pd.notna(row["RuYD"]) else 0,
                    "rush_td": int(row["RuTD"]) if pd.notna(row["RuTD"]) else 0,
                    "targets": int(row["Tar"]) if pd.notna(row["Tar"]) else 0,
                    "receptions": int(row["Rec"]) if pd.notna(row["Rec"]) else 0,
                    "rec_yards": int(row["ReYD"]) if pd.notna(row["ReYD"]) else 0,
                    "rec_td": int(row["ReTD"]) if pd.notna(row["ReTD"]) else 0
                })
                
            rookies.append(rookie)  # Only append if no exception occurred
                
        except Exception as e:
            print(f"Warning: Error processing {row['Name']}: {str(e)}")
            continue
    
    if not rookies:
        print("Error: No valid rookie data was processed!")
        return
    
    # Create final JSON structure
    json_data = {
        "version": "1.0",
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "rookies": rookies
    }
    
    # Write to file
    try:
        with open(output_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        print(f"Successfully converted {len(rookies)} rookies to {output_file}")
    except Exception as e:
        print(f"Error writing JSON file: {str(e)}")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert rookie projections Excel to JSON')
    parser.add_argument('-f', '--force', action='store_true', 
                        help='Force overwrite of existing rookies.json')
    args = parser.parse_args()
    
    # Get project root directory (3 levels up from script)
    project_root = Path(__file__).parent.parent.parent
    
    # Define input and output paths
    excel_file = project_root / "data" / "rookie_projections.xlsx"
    output_file = project_root / "data" / "rookies.json"
    
    # Check if input file exists
    if not excel_file.exists():
        print(f"Error: Input file not found at {excel_file}")
        sys.exit(1)
        
    # Ensure data directory exists
    output_file.parent.mkdir(exist_ok=True)
    
    # Convert the file
    convert_excel_to_json(str(excel_file), str(output_file), args.force)
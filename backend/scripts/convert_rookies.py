import pandas as pd
import json
import logging
from datetime import datetime
from pathlib import Path
import argparse
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def convert_to_json(input_file: str, output_file: str, force: bool = False):
    """
    Convert rookie projections file to rookies.json format.
    Supports both Excel (.xlsx) and CSV (.csv) formats.
    """
    # Check if output file exists
    output_path = Path(output_file)
    if output_path.exists() and not force:
        logger.warning(f"Warning: {output_file} already exists!")
        response = input("Do you want to overwrite it? (y/N): ").lower()
        if response != 'y':
            logger.info("Aborting conversion.")
            return False
    
    try:
        # Determine file type and read accordingly
        if input_file.endswith('.xlsx'):
            logger.info(f"Reading Excel file: {input_file}")
            df = pd.read_excel(input_file)
        elif input_file.endswith('.csv'):
            logger.info(f"Reading CSV file: {input_file}")
            df = pd.read_csv(input_file)
        else:
            logger.error(f"Unsupported file type: {input_file}. Must be .xlsx or .csv")
            return False
            
        logger.info(f"Available columns: {df.columns.tolist()}")
        
    except Exception as e:
        logger.error(f"Error reading input file: {str(e)}")
        return False
    
    # Initialize rookies list
    rookies = []
    
    # Process each row
    for _, row in df.iterrows():
        rookie = {
            "name": row["Name"] if "Name" in df.columns else row["name"],
            "position": row["Pos"] if "Pos" in df.columns else row["position"],
            "team": row["Team"] if "Team" in df.columns else row["team"],
            "draft_position": int(float(row["ADP"])) if "ADP" in df.columns and pd.notna(row["ADP"]) else 0,
            "projected_stats": {
                "games": int(row["Gm"]) if "Gm" in df.columns and pd.notna(row["Gm"]) else 17
            }
        }
        
        # Add height if available
        height_field = next((f for f in ["Height", "height"] if f in df.columns), None)
        if height_field and pd.notna(row[height_field]):
            # Check if height is already in inches
            if isinstance(row[height_field], (int, float)):
                rookie["height"] = int(row[height_field])
            # Check if height is in ft-in format (e.g., "6-2")
            elif isinstance(row[height_field], str) and "-" in row[height_field]:
                try:
                    feet, inches = row[height_field].split("-")
                    rookie["height"] = int(feet) * 12 + int(inches)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid height format for {rookie['name']}: {row[height_field]}")
        
        # Add weight if available
        weight_field = next((f for f in ["Weight", "weight"] if f in df.columns), None)
        if weight_field and pd.notna(row[weight_field]):
            try:
                rookie["weight"] = int(row[weight_field])
            except (ValueError, TypeError):
                logger.warning(f"Invalid weight for {rookie['name']}: {row[weight_field]}")
        
        # Add date of birth if available
        dob_field = next((f for f in ["DOB", "date_of_birth"] if f in df.columns), None)
        if dob_field and pd.notna(row[dob_field]):
            try:
                # Convert to ISO format date string (YYYY-MM-DD)
                dob = pd.to_datetime(row[dob_field])
                rookie["date_of_birth"] = dob.strftime("%Y-%m-%d")
            except:
                logger.warning(f"Invalid date of birth for {rookie['name']}: {row[dob_field]}")
        
        try:
            # Add position-specific stats based on position
            pos = rookie["position"]
            if pos == "QB":
                stats = {}
                for field, excel_field in [
                    ("pass_attempts", "PaATT"), 
                    ("completions", "Comp"),
                    ("pass_yards", "PaYD"),
                    ("pass_td", "PaTD"),
                    ("interceptions", "INT"),
                    ("rush_attempts", "Car"),
                    ("rush_yards", "RuYD"),
                    ("rush_td", "RuTD")
                ]:
                    if excel_field in df.columns and pd.notna(row[excel_field]):
                        stats[field] = int(row[excel_field])
                rookie["projected_stats"].update(stats)
                
            elif pos in ["WR", "TE"]:
                stats = {}
                for field, excel_field in [
                    ("targets", "Tar"),
                    ("receptions", "Rec"),
                    ("rec_yards", "ReYD"),
                    ("rec_td", "ReTD"),
                    ("rush_attempts", "Car"),
                    ("rush_yards", "RuYD"),
                    ("rush_td", "RuTD")
                ]:
                    if excel_field in df.columns and pd.notna(row[excel_field]):
                        stats[field] = int(row[excel_field])
                rookie["projected_stats"].update(stats)
                
            elif pos == "RB":
                stats = {}
                for field, excel_field in [
                    ("carries", "Car"),
                    ("rush_yards", "RuYD"),
                    ("rush_td", "RuTD"),
                    ("targets", "Tar"),
                    ("receptions", "Rec"),
                    ("rec_yards", "ReYD"),
                    ("rec_td", "ReTD")
                ]:
                    if excel_field in df.columns and pd.notna(row[excel_field]):
                        stats[field] = int(row[excel_field])
                rookie["projected_stats"].update(stats)
                
            # Add draft information if available
            for field, excel_field in [
                ("draft_team", "draft_team"),
                ("draft_round", "draft_round"),
                ("draft_pick", "draft_pick")
            ]:
                if excel_field in df.columns and pd.notna(row[excel_field]):
                    if field in ["draft_round", "draft_pick"]:
                        rookie[field] = int(row[excel_field])
                    else:
                        rookie[field] = row[excel_field]
                        
            rookies.append(rookie)  # Only append if no exception occurred
                
        except Exception as e:
            logger.warning(f"Warning: Error processing {rookie['name']}: {str(e)}")
            continue
    
    if not rookies:
        logger.error("Error: No valid rookie data was processed!")
        return False
    
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
        logger.info(f"Successfully converted {len(rookies)} rookies to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error writing JSON file: {str(e)}")
        return False
    
def main():
    parser = argparse.ArgumentParser(description='Convert rookie projections to JSON')
    parser.add_argument('-i', '--input', type=str, help='Input file path (.xlsx or .csv)')
    parser.add_argument('-o', '--output', type=str, help='Output JSON file path')
    parser.add_argument('-f', '--force', action='store_true', help='Force overwrite of existing output file')
    args = parser.parse_args()
    
    # Get project root directory (3 levels up from script)
    project_root = Path(__file__).parent.parent.parent
    
    # Define input and output paths
    input_file = args.input if args.input else project_root / "data" / "rookie_baseline.xlsx"
    output_file = args.output if args.output else project_root / "data" / "rookies.json"
    
    # Convert paths to strings
    input_file = str(input_file)
    output_file = str(output_file)
    
    # Check if input file exists
    if not Path(input_file).exists():
        logger.error(f"Error: Input file not found at {input_file}")
        sys.exit(1)
        
    # Ensure data directory exists
    Path(output_file).parent.mkdir(exist_ok=True)
    
    # Convert the file
    success = convert_to_json(input_file, output_file, args.force)
    if not success:
        logger.error("Conversion failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
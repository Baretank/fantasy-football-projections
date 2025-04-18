#!/usr/bin/env python3
"""
Fix Implicit Optional Types Script

This script helps identify and fix common type errors related to 
missing Optional[T] annotations where default values of None are used.
"""

import os
import re
import argparse
import sys
from typing import Dict, List, Tuple, Optional, Any, Set

def find_python_files(root_dir: str) -> List[str]:
    """Find all Python files in the directory tree."""
    python_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.py'):
                python_files.append(os.path.join(dirpath, filename))
    return python_files

def fix_optional_types(file_path: str, dry_run: bool = True) -> Dict[str, Any]:
    """
    Fix implicit Optional types in a Python file.
    
    Args:
        file_path: Path to the Python file
        dry_run: True to print changes without modifying files
        
    Returns:
        Dict with statistics and changes
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Regular expressions for function parameter detection with default None
    # Matches patterns like "def func(param: type = None):" without Optional
    param_pattern = r'def\s+\w+\(([^)]*)\)'
    
    # Extract function parameters
    changes = []
    updated_content = content
    
    # Check if typing.Optional is imported
    if 'Optional' not in content:
        if 'from typing import ' in content:
            # Add Optional to existing import
            updated_content = re.sub(
                r'from typing import (.*?)(?=\n)',
                r'from typing import \1, Optional',
                updated_content
            )
            changes.append(("Added Optional to typing imports", ""))
        else:
            # Add new import
            updated_content = re.sub(
                r'(.*?)(?=\nimport|\nfrom|\ndef|\nclass)',
                r'\1\n\nfrom typing import Optional\n',
                updated_content,
                count=1
            )
            changes.append(("Added typing import for Optional", ""))
    
    # Find function definitions and fix parameter types
    for match in re.finditer(param_pattern, content):
        params_str = match.group(1)
        
        # Look for typed parameters with default None but missing Optional
        type_default_pattern = r'(\w+):\s*([^=\s]+)\s*=\s*None\b'
        
        # Find all positions where we need to make changes
        param_positions = []
        for param_match in re.finditer(type_default_pattern, params_str):
            param_name = param_match.group(1)
            param_type = param_match.group(2)
            
            # Skip if it's already Optional
            if param_type.startswith('Optional[') or 'Union[' in param_type:
                continue
                
            # Calculate positions
            start_pos = match.start(1) + param_match.start(2)
            end_pos = match.start(1) + param_match.end(2)
            param_positions.append((start_pos, end_pos, param_type, param_name))
        
        # Sort by position in reverse order to avoid affecting earlier positions
        for start_pos, end_pos, param_type, param_name in sorted(param_positions, reverse=True):
            old_type = param_type
            new_type = f"Optional[{param_type}]"
            old_snippet = content[max(0, start_pos-10):min(len(content), end_pos+10)]
            
            # Replace the type with Optional[type]
            updated_content = updated_content[:start_pos] + new_type + updated_content[end_pos:]
            
            changes.append((f"Parameter {param_name}: {old_type} -> {new_type}", old_snippet))
    
    # Fix return type annotations with None
    return_pattern = r'def\s+\w+\([^)]*\)\s*->\s*([^:]+):'
    for match in re.finditer(return_pattern, content):
        return_type = match.group(1).strip()
        
        # Skip if already using Optional or Union
        if return_type.startswith('Optional[') or 'Union[' in return_type or return_type == 'None':
            continue
            
        # Look for "-> type" where the function can actually return None
        if ' return None' in content or '\nreturn None' in content:
            start_pos = match.start(1)
            end_pos = match.end(1)
            
            # Replace with Optional[type]
            old_type = return_type
            new_type = f"Optional[{return_type}]"
            
            old_snippet = content[max(0, start_pos-15):min(len(content), end_pos+15)]
            
            # Replace the return type with Optional[type]
            updated_content = updated_content[:start_pos] + new_type + updated_content[end_pos:]
            
            changes.append((f"Return type: {old_type} -> {new_type}", old_snippet))
    
    if not dry_run and updated_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
    
    result = {
        'file': file_path,
        'changes': len(changes),
        'details': changes,
        'content_changed': updated_content != content
    }
    
    return result

def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Fix implicit Optional types in Python code")
    parser.add_argument("--root", default=".", help="Root directory of the project")
    parser.add_argument("--path", help="Specific file or directory to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't modify files, just show what would change")
    args = parser.parse_args()
    
    # Determine files to process
    if args.path:
        if os.path.isfile(args.path) and args.path.endswith('.py'):
            python_files = [args.path]
        elif os.path.isdir(args.path):
            python_files = find_python_files(args.path)
        else:
            print(f"Error: {args.path} is not a Python file or directory")
            sys.exit(1)
    else:
        python_files = find_python_files(args.root)
    
    # Process each file
    total_changes = 0
    modified_files = 0
    
    for file_path in python_files:
        result = fix_optional_types(
            file_path=file_path,
            dry_run=args.dry_run
        )
        
        if result['changes'] > 0:
            print(f"{'[DRY RUN] ' if args.dry_run else ''}File: {result['file']}")
            print(f"Changes: {result['changes']}")
            
            for i, (change, context) in enumerate(result['details'], 1):
                print(f"  {i}. {change}")
                if context:
                    print(f"     Context: ...{context}...")
            
            print()
            total_changes += result['changes']
            
            if result['content_changed']:
                modified_files += 1
    
    # Summary
    print("=" * 80)
    print(f"Summary {'(DRY RUN)' if args.dry_run else ''}")
    print("=" * 80)
    print(f"Files processed: {len(python_files)}")
    print(f"Files with changes: {modified_files}")
    print(f"Total type annotations fixed: {total_changes}")
    
    if args.dry_run:
        print("\nRun without --dry-run to apply these changes")

if __name__ == "__main__":
    main()
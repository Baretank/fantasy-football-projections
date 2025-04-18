#!/usr/bin/env python3
"""
Import Standardization Script

This script helps standardize imports across the codebase to follow a consistent pattern.
It can convert between relative imports (.module) and absolute imports (backend.module).
"""

import os
import re
import argparse
import sys
from typing import Dict, List, Set, Tuple, Optional, Any

def find_python_files(root_dir: str) -> List[str]:
    """Find all Python files in the directory tree."""
    python_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.py'):
                python_files.append(os.path.join(dirpath, filename))
    return python_files

def standardize_imports(file_path: str, root_dir: str, use_absolute: bool = True, dry_run: bool = True) -> Dict[str, Any]:
    """
    Standardize imports in a Python file to either absolute or relative style.
    
    Args:
        file_path: Path to the Python file
        root_dir: Root directory of the project
        use_absolute: True to use absolute imports, False for relative
        dry_run: True to print changes without modifying files
        
    Returns:
        Dict with statistics and changes
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Get the module path relative to root
    rel_module_path = os.path.relpath(file_path, root_dir).replace('/', '.').replace('\\', '.').replace('.py', '')
    
    # Regular expressions for import detection
    # Matches "from X.Y.Z import A, B" or "from .X.Y import A, B"
    from_import_pattern = r'^(from\s+)([.\w]+)(\s+import\s+.*)$'
    
    # Process each line
    lines = content.split('\n')
    updated_lines = []
    changes = []
    
    for line in lines:
        match = re.match(from_import_pattern, line.strip())
        if match:
            prefix, module, suffix = match.groups()
            
            # Skip if not from backend or relative import
            if not (module.startswith('backend.') or module.startswith('.')):
                updated_lines.append(line)
                continue
            
            if use_absolute and module.startswith('.'):
                # Convert relative to absolute
                module_parts = rel_module_path.split('.')
                level = 0
                
                for char in module:
                    if char == '.':
                        level += 1
                    else:
                        break
                
                # Adjust path based on level of relative import
                if level <= len(module_parts):
                    base_path = '.'.join(module_parts[:-level]) if level > 0 else module_parts[:]
                    if level < len(module):
                        remaining = module[level:]
                        if base_path:
                            new_module = f"backend.{base_path}.{remaining}" if base_path != "backend" else f"backend.{remaining}"
                        else:
                            new_module = f"backend.{remaining}"
                    else:
                        new_module = f"backend.{base_path}" if base_path != "backend" else "backend"
                    
                    new_line = f"{prefix}{new_module}{suffix}"
                    updated_lines.append(new_line)
                    changes.append((line, new_line))
                else:
                    # Too deep for relative import
                    updated_lines.append(line)
            
            elif not use_absolute and module.startswith('backend.'):
                # Convert absolute to relative
                abs_module = module[len('backend.'):]
                module_parts = rel_module_path.split('.')
                target_parts = abs_module.split('.')
                
                # Find common prefix
                common_length = 0
                for i in range(min(len(module_parts), len(target_parts))):
                    if module_parts[i] == target_parts[i]:
                        common_length += 1
                    else:
                        break
                
                # Calculate dots needed
                dots = '.' * (len(module_parts) - common_length)
                
                if common_length == 0:
                    # No common path, use absolute
                    updated_lines.append(line)
                else:
                    # Calculate relative path
                    if common_length == len(target_parts):
                        # Import from parent package
                        new_module = dots
                    else:
                        # Import from sibling package
                        remaining = '.'.join(target_parts[common_length:])
                        new_module = f"{dots}{remaining}"
                    
                    new_line = f"{prefix}{new_module}{suffix}"
                    updated_lines.append(new_line)
                    changes.append((line, new_line))
            else:
                # No change needed
                updated_lines.append(line)
        else:
            # Not an import line
            updated_lines.append(line)
    
    new_content = '\n'.join(updated_lines)
    
    if not dry_run and new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
    
    result = {
        'file': file_path,
        'changes': len(changes),
        'details': changes,
        'content_changed': new_content != content
    }
    
    return result

def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Standardize import styles in Python codebase")
    parser.add_argument("--root", default=".", help="Root directory of the project")
    parser.add_argument("--style", choices=["absolute", "relative"], default="absolute", 
                        help="Import style to use (absolute=backend.module, relative=.module)")
    parser.add_argument("--path", help="Specific file or directory to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't modify files, just show what would change")
    args = parser.parse_args()
    
    use_absolute = args.style == "absolute"
    
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
        result = standardize_imports(
            file_path=file_path,
            root_dir=args.root,
            use_absolute=use_absolute,
            dry_run=args.dry_run
        )
        
        if result['changes'] > 0:
            print(f"{'[DRY RUN] ' if args.dry_run else ''}File: {result['file']}")
            print(f"Changes: {result['changes']}")
            
            for i, (old, new) in enumerate(result['details'], 1):
                print(f"  {i}. {old.strip()} -> {new.strip()}")
            
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
    print(f"Total import statements changed: {total_changes}")
    
    if args.dry_run:
        print("\nRun without --dry-run to apply these changes")

if __name__ == "__main__":
    main()
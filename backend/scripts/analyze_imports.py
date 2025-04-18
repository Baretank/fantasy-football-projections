#!/usr/bin/env python3
"""
Import Analysis Script

This script analyzes import patterns across the codebase to help identify issues
that may cause problems with mypy and module resolution.
"""

import os
import re
import argparse
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Any, DefaultDict

def find_python_files(root_dir: str) -> List[str]:
    """Find all Python files in the directory tree."""
    python_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.py'):
                python_files.append(os.path.join(dirpath, filename))
    return python_files

def extract_imports(file_path: str) -> Tuple[List[str], List[str]]:
    """Extract all import statements from a Python file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all import statements
    import_pattern = r'^(?:from\s+(\S+)\s+import\s+.*|import\s+(\S+))(?:\s+as\s+\S+)?$'
    
    absolute_imports = []
    relative_imports = []
    
    for line in content.split('\n'):
        match = re.match(import_pattern, line.strip())
        if match:
            # Either from X import Y or import X
            module = match.group(1) or match.group(2)
            
            # Skip standard library and third-party imports for clarity
            if module.startswith('.'):
                relative_imports.append(module)
            elif module.startswith('backend.'):
                absolute_imports.append(module)
    
    return absolute_imports, relative_imports

def analyze_imports(root_dir: str) -> Dict[str, Any]:
    """Analyze import patterns across the codebase."""
    python_files = find_python_files(root_dir)
    
    # Track various metrics
    results: Dict[str, Any] = {
        'file_count': len(python_files),
        'by_file': {},
        'absolute_import_counts': defaultdict(int),
        'relative_import_counts': defaultdict(int),
        'mixed_style_files': [],
        'import_network': defaultdict(set),
        'local_imports': defaultdict(set),
        'potential_circular': [],
    }
    
    # Analyze each file
    for file_path in python_files:
        rel_path = os.path.relpath(file_path, root_dir)
        absolute_imports, relative_imports = extract_imports(file_path)
        
        # Store imports by file
        results['by_file'][rel_path] = {
            'absolute_imports': absolute_imports,
            'relative_imports': relative_imports,
        }
        
        # Count occurrences of each import style
        for imp in absolute_imports:
            results['absolute_import_counts'][imp] += 1
        for imp in relative_imports:
            results['relative_import_counts'][imp] += 1
        
        # Find files with mixed import styles
        if absolute_imports and relative_imports:
            results['mixed_style_files'].append(rel_path)
        
        # Build import network for circular dependency detection
        file_module = rel_path.replace('/', '.').replace('\\', '.').replace('.py', '')
        for imp in absolute_imports:
            if imp.startswith('backend.'):
                # Convert absolute import path to relative file path
                imported_module = imp.replace('backend.', '', 1)
                results['import_network'][file_module].add(imported_module)
        
        for imp in relative_imports:
            # Convert relative import to absolute path
            current_parts = file_module.split('.')
            imp_parts = imp.split('.')
            
            # Handle relative imports
            if imp.startswith('.'):
                level = 0
                for c in imp:
                    if c == '.':
                        level += 1
                    else:
                        break
                
                # Calculate the target module
                if level <= len(current_parts):
                    target_parts = current_parts[:-level] if level > 0 else current_parts[:]
                    if len(imp) > level:
                        remaining = imp[level:]
                        target_parts.append(remaining)
                    
                    imported_module = '.'.join(target_parts)
                    results['import_network'][file_module].add(imported_module)
    
    # Identify potential circular dependencies
    visited: Set[str] = set()
    
    def detect_circular(node: str, path: List[str]) -> None:
        if node in path:
            # Found a cycle
            cycle_start = path.index(node)
            results['potential_circular'].append(path[cycle_start:] + [node])
            return
        
        if node in visited:
            return
        
        visited.add(node)
        for neighbor in results['import_network'].get(node, []):
            detect_circular(neighbor, path + [node])
    
    for module in results['import_network']:
        detect_circular(module, [])
    
    return results

def print_report(results: Dict[str, Any]) -> None:
    """Print analysis report."""
    print("=" * 80)
    print(f"Import Analysis Report - {results['file_count']} Python files analyzed")
    print("=" * 80)
    
    # Report on mixed style files
    if results['mixed_style_files']:
        print("\nFiles with mixed import styles:")
        for file in sorted(results['mixed_style_files']):
            print(f"  - {file}")
            abs_imports = results['by_file'][file]['absolute_imports']
            rel_imports = results['by_file'][file]['relative_imports']
            if abs_imports:
                print(f"      Absolute: {', '.join(abs_imports[:3])}{'...' if len(abs_imports) > 3 else ''}")
            if rel_imports:
                print(f"      Relative: {', '.join(rel_imports[:3])}{'...' if len(rel_imports) > 3 else ''}")
    
    # Report on potential circular dependencies
    if results['potential_circular']:
        print("\nPotential circular dependencies:")
        for i, cycle in enumerate(results['potential_circular'], 1):
            print(f"  {i}. {' -> '.join(cycle)}")
    
    # Summary statistics
    abs_count = sum(results['absolute_import_counts'].values())
    rel_count = sum(results['relative_import_counts'].values())
    total = abs_count + rel_count if abs_count + rel_count > 0 else 1  # Avoid division by zero
    
    print("\nImport style statistics:")
    print(f"  Absolute imports: {abs_count} ({abs_count/total*100:.1f}%)")
    print(f"  Relative imports: {rel_count} ({rel_count/total*100:.1f}%)")
    print(f"  Files with mixed styles: {len(results['mixed_style_files'])} ({len(results['mixed_style_files'])/results['file_count']*100:.1f}%)")
    
    # Most common imports
    print("\nMost common absolute imports:")
    for imp, count in sorted(results['absolute_import_counts'].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  - {imp}: {count}")
    
    print("\nMost common relative imports:")
    for imp, count in sorted(results['relative_import_counts'].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  - {imp}: {count}")

def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Analyze import patterns in Python codebase")
    parser.add_argument("--root", default=".", help="Root directory to analyze")
    args = parser.parse_args()
    
    results = analyze_imports(args.root)
    print_report(results)

if __name__ == "__main__":
    main()
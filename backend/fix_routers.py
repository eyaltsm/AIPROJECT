#!/usr/bin/env python3
"""
Script to fix all router files by adding Request parameter to rate-limited functions.
"""

import os
import re
from pathlib import Path

def fix_router_file(file_path):
    """Fix a single router file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add Request import if not present
    if 'from fastapi import' in content and 'Request' not in content:
        content = re.sub(
            r'(from fastapi import [^)]+)',
            r'\1, Request',
            content
        )
    
    # Fix function definitions that use @limiter.limit but don't have request parameter
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this line has @limiter.limit
        if '@limiter.limit(' in line:
            # Look for the function definition in the next few lines
            j = i + 1
            while j < len(lines) and j < i + 10:  # Look within next 10 lines
                func_line = lines[j]
                if 'async def ' in func_line or 'def ' in func_line:
                    # Check if request parameter is missing
                    if 'request: Request' not in func_line and 'Request' in content:
                        # Add request parameter
                        if '(' in func_line and ')' in func_line:
                            # Find the opening parenthesis and add request parameter
                            paren_pos = func_line.find('(')
                            if paren_pos != -1:
                                # Check if there are already parameters
                                if func_line[paren_pos + 1:].strip().startswith(')'):
                                    # No parameters, add request
                                    func_line = func_line[:paren_pos + 1] + 'request: Request' + func_line[paren_pos + 1:]
                                else:
                                    # Has parameters, add request at the beginning
                                    func_line = func_line[:paren_pos + 1] + 'request: Request, ' + func_line[paren_pos + 1:]
                        lines[j] = func_line
                    break
                j += 1
        
        fixed_lines.append(line)
        i += 1
    
    return '\n'.join(fixed_lines)

def main():
    """Fix all router files."""
    routers_dir = Path('app/routers')
    
    for py_file in routers_dir.glob('*.py'):
        if py_file.name == '__init__.py':
            continue
            
        print(f"Fixing {py_file}")
        try:
            fixed_content = fix_router_file(py_file)
            
            with open(py_file, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
                
            print(f"✓ Fixed {py_file}")
        except Exception as e:
            print(f"✗ Error fixing {py_file}: {e}")

if __name__ == '__main__':
    main()



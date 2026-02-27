"""Fix all garbled emoji characters across JSX files."""
import os
import glob

# Map of garbled emoji bytes -> clean replacement text
REPLACEMENTS = {
    # Shield emoji
    "\u00f0\u0178\u203a\u00a1\u00ef\u00b8\u008f": "\u{1F6E1}\u{FE0F}",
    # Warning emoji  
    "\u00e2\u0178\u0160\u00ef\u00b8\u008f": "\u26A0",
    # Siren/rotating light emoji
    "\u00f0\u0178\u0161\u00a8": "\u{1F6A8}",
    # Magnifying glass
    "\u00f0\u0178\u201d\u0141": "\u{1F50D}",
    # Newspaper
    "\u00f0\u0178\u201c\u00b0": "\u{1F4F0}",
    # Checkbox/clipboard
    "\u00f0\u0178\u201c\u2039": "\u{1F4CB}",
    # Tag/label
    "\u00f0\u0178\u0178\u00b7\u00ef\u00b8\u008f": "\u{1F3F7}\u{FE0F}",
}

SRC_DIR = os.path.join(os.path.dirname(__file__), "src")

def fix_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    original = content
    
    # Replace garbled emojis with simple text/symbol alternatives
    # These are the double-encoded UTF-8 sequences
    
    # Header shield: ð¡ï¸ -> SVG shield icon text
    content = content.replace('ð\x9b¡ï¸\x8f', '\\u{1F6E1}')
    
    print(f"Checking {filepath}")
    print(f"  Changed: {content != original}")

fix_file(os.path.join(SRC_DIR, "App.jsx"))

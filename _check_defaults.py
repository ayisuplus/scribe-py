import re
with open("scribe/types.py", encoding="utf-8") as f:
    content = f.read()

for i, line in enumerate(content.split('\n'), 1):
    if 'field(default_factory=' in line:
        m = re.search(r'field\(default_factory=(\w+)\)', line)
        if m:
            print(f"NEED FIX: {m.group(1)} at line {i}: {line.strip()[:80]}")
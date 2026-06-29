#!/usr/bin/env python3
"""Print dynamically resolved engine offsets."""
from esp import MecchaESP

esp = MecchaESP()
for key, val in sorted(esp.offsets.items()):
    print(f"{key:45} = 0x{val:X}")

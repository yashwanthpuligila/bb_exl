import sys
import os
from pathlib import Path

# Add project root
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import desktop_app

print("Testing get_chromium_browser_path()...")
bin_path = desktop_app.get_chromium_browser_path()
print("Found Chromium Browser:", bin_path)
assert bin_path is not None, "A Chromium browser should be found"
assert os.path.exists(bin_path), "Browser path must exist"

print("Testing find_available_port()...")
port = desktop_app.find_available_port(5000)
print("Found available port:", port)
assert port >= 5000

print("Testing is_port_in_use()...")
in_use = desktop_app.is_port_in_use(port)
print(f"Port {port} in use:", in_use)
assert not in_use

print("All utility tests passed!")

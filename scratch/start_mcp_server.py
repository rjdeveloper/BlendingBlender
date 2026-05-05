import bpy
import os
import sys

# Ensure addon.py can be found
script_dir = r"c:\blundai"
if script_dir not in sys.path:
    sys.path.append(script_dir)

try:
    # Try to import as module
    import addon
    print("Addon module imported successfully.")
except ImportError:
    # Fallback: execute the file directly
    addon_path = os.path.join(script_dir, "addon.py")
    with open(addon_path, "r") as f:
        exec(f.read(), globals())
    print("Addon file executed successfully.")

# Start the server
# The addon.py usually registers a class BlenderMCPServer
try:
    server = addon.BlenderMCPServer()
    server.start()
    print("BlenderMCP server started on localhost:9876")
except NameError:
    # If exec was used, the class is in globals
    server = BlenderMCPServer()
    server.start()
    print("BlenderMCP server started on localhost:9876 (fallback)")

# Keep Blender alive for the server thread
import time
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    server.stop()

import requests
import json

url = "http://localhost:8000/chat/start"
payload = {
    "message": "DEBUG: Execute this script in Blender: import bpy; bpy.ops.mesh.primitive_cube_add(location=(0,0,5))",
    "history": [],
    "settings": {"mode": "cnc"}, # Use CNC mode for direct tool calling
    "mode": "cnc"
}

print(f"Sending debug request...")
try:
    response = requests.post(url, json=payload, timeout=5)
    print(f"Response: {response.status_code}")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")

import requests
import json
import time

url = "http://localhost:8000/chat/start"
payload = {
    "message": "Create a 60-second 2D Grease Pencil news anchor animation (1440 frames). The anchor should read a professional news script about the future of AI. Lip-sync should cycle through M_Closed, M_Open, M_Smile, and M_O. Ensure full green screen setup and final render to mp4.",
    "history": [],
    "settings": {"mode": "director"},
    "mode": "director"
}

print(f"Sending request to {url}...")
try:
    response = requests.post(url, json=payload, timeout=10)
    if response.status_code == 200:
        request_id = response.json().get("request_id")
        print(f"Job started successfully. Request ID: {request_id}")
        
        # Poll for status
        status_url = f"http://localhost:8000/chat/status/{request_id}"
        print("Polling for progress...")
        
        last_trace_len = 0
        while True:
            status_resp = requests.get(status_url)
            if status_resp.status_code == 200:
                data = status_resp.json()
                status = data.get("status")
                trace = data.get("trace", [])
                
                # Print new trace entries
                if len(trace) > last_trace_len:
                    for entry in trace[last_trace_len:]:
                        print(f"  [TRACE] {entry}")
                    last_trace_len = len(trace)
                
                if status == "completed":
                    print("\n[SUCCESS] Job completed!")
                    print(f"Response: {data.get('response')}")
                    break
                elif status == "failed":
                    print(f"\n[FAILED] Job failed: {data.get('error')}")
                    break
            else:
                print(f"Error polling status: {status_resp.status_code}")
                break
            
            time.sleep(5)
    else:
        print(f"Failed to start job: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Exception occurred: {e}")

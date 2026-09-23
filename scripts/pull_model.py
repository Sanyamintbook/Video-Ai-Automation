import httpx

url = "http://45.194.3.86:11434/api/pull"
payload = {"name": "qwen2.5:7b"}
print("Triggering model pull for qwen2.5:7b on 45.194.3.86...")

try:
    with httpx.Client(timeout=1800.0) as client:
        # Stream the response to keep connection alive
        with client.stream("POST", url, json=payload) as response:
            for line in response.iter_lines():
                print(line)
except Exception as e:
    print(f"Error: {e}")

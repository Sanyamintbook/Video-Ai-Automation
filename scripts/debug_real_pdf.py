import asyncio
import traceback
from fastapi.testclient import TestClient
from app.api.routes.upload import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)

client = TestClient(app)

def main():
    pdf_path = "test_data/input/Ch 3 Mineral and Power Resour.pdf"
    print(f"Testing with {pdf_path}")
    try:
        with open(pdf_path, "rb") as f:
            response = client.post("/upload", files={"file": ("test.pdf", f, "application/pdf")})
            print(f"Status Code: {response.status_code}")
            try:
                print(f"Response JSON: {response.json()}")
            except:
                print(f"Response Text[:500]: {response.text[:500]}")
    except Exception as e:
        print(traceback.format_exc())

if __name__ == "__main__":
    main()

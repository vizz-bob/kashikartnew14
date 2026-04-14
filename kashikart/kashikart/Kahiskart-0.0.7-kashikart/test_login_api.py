import requests
import json

def test_login():
    url = "http://127.0.0.1:8000/api/auth/login"
    data = {
        "email": "admin@gmail.com",
        "password": "Admin@123"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_login()

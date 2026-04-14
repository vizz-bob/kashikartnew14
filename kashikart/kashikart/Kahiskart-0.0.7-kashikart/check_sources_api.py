import requests
import json

def check_api():
    url = "http://127.0.0.1:8000/api/auth/login"
    login_data = {"email": "admin@gmail.com", "password": "Admin@123"}
    resp = requests.post(url, json=login_data)
    token = resp.json().get("access_token")
    
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get("http://127.0.0.1:8000/api/sources/?size=200", headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Text: {resp.text}")
    data = resp.json()
    print(f"Total in API: {data.get('total')}")
    print(f"Items in API: {len(data.get('items', []))}")

if __name__ == "__main__":
    check_api()

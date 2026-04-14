import asyncio
import httpx

async def test_login():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "http://127.0.0.1:8000/api/auth/login",
                json={"email": "admin@gmail.com", "password": "password123"}
            )
            print(f"Status: {resp.status_code}")
            print(f"Body: {resp.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    # Ensure server is running or wait for it
    asyncio.run(test_login())

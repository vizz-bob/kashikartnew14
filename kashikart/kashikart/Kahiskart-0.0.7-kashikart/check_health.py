import asyncio
import httpx

async def check():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("http://127.0.0.1:8000/api/health")
            print(f"Health: {resp.status_code} - {resp.json()}")
        except Exception as e:
            print(f"Health fail: {e}")

if __name__ == "__main__":
    asyncio.run(check())

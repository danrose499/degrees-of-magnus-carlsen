import httpx
import asyncio

lock = asyncio.Lock()

BASE = "https://api.chess.com/pub"

async def fetch(url):
    async with lock:
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()

async def get_recent_games(username, months=1):
    archives = await fetch(f"{BASE}/player/{username}/games/archives")
    urls = archives["archives"][-months:]

    games = []
    for url in urls:
        data = await fetch(url)
        games.extend(data["games"])

    return games

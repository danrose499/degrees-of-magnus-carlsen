from fastapi import FastAPI
from ingest import ingest_player
from graph import find_path

app = FastAPI()

@app.get("/path/{username}")
async def path_to_magnus(username: str):
    await ingest_player(username)
    return find_path(username)

@app.post("/ingest/magnus")
async def ingest_magnus():
    await ingest_player("magnuscarlsen")
    return {"status": "ok"}
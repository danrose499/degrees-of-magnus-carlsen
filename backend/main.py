from fastapi import FastAPI, Query
from ingest import ingest_player, driver
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

@app.get("/players/search")
async def search_players(q: str = Query(..., min_length=2)):
    """Search for players by username prefix"""
    with driver.session() as session:
        result = session.run("""
        MATCH (p:Player)
        WHERE p.username STARTS WITH $query
        RETURN p.username as username, p.avatar as avatar
        ORDER BY p.username
        LIMIT 10
        """, query=q.lower())
        
        suggestions = []
        for record in result:
            suggestions.append({
                "username": record["username"],
                "avatar": record["avatar"]
            })
        
        return suggestions
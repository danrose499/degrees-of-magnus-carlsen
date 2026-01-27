from fastapi import FastAPI, Query
from ingest import ingest_player, driver
from graph import find_path, get_data_metadata

app = FastAPI()

@app.get("/path/{username}")
async def path_to_magnus(username: str):
    await ingest_player(username)
    return find_path(username)

@app.post("/ingest/magnus")
async def ingest_magnus():
    await ingest_player("magnuscarlsen")
    return {"status": "ok"}

@app.get("/metadata")
async def get_metadata():
    """Get data ingestion metadata"""
    return get_data_metadata()

@app.get("/players/search")
async def search_players(q: str = Query(..., min_length=2)):
    """Search for players by username prefix"""
    try:
        with driver.session() as session:
            result = session.run("""
            MATCH (p:Player)
            WHERE toLower(p.username) STARTS WITH toLower($query)
            RETURN p.username as username, p.avatar as avatar
            ORDER BY p.username
            LIMIT 10
            """, query=q)
            
            suggestions = []
            for record in result:
                suggestions.append({
                    "username": record["username"],
                    "avatar": record["avatar"]
                })
            
            return suggestions
    except Exception as e:
        print(f"Database error: {e}")
        return []
from chess_api import get_recent_games, get_player_profile
from neo4j import GraphDatabase
from pydantic_settings import BaseSettings
import httpx

class Settings(BaseSettings):
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str

    class Config:
        env_file = ".env"

settings = Settings()

driver = GraphDatabase.driver(
    settings.neo4j_uri,
    auth=(settings.neo4j_user, settings.neo4j_password)
)

async def ingest_player(username):
    games = await get_recent_games(username)
    
    # Get unique player usernames from games
    players = set()
    for g in games:
        players.add(g["white"]["username"].lower())
        players.add(g["black"]["username"].lower())
    
    # Fetch profile data for all players
    profiles = {}
    for player in players:
        try:
            profile = await get_player_profile(player)
            profiles[player] = profile.get("avatar", "")
        except (Exception, httpx.HTTPStatusError):
            profiles[player] = ""

    with driver.session() as session:
        for g in games:
            white = g["white"]["username"].lower()
            black = g["black"]["username"].lower()
            url = g["url"]
            date = g.get("end_time", "")  # Unix timestamp or empty string

            session.run("""
            MERGE (w:Player {username: $white})
            SET w.avatar = $white_avatar
            MERGE (b:Player {username: $black})
            SET b.avatar = $black_avatar
            MERGE (w)-[:PLAYED {url: $url, date: $date}]->(b)
            MERGE (b)-[:PLAYED {url: $url, date: $date}]->(w)
            """, 
            white=white, 
            black=black, 
            url=url, 
            date=date,
            white_avatar=profiles.get(white, ""),
            black_avatar=profiles.get(black, "")
            )

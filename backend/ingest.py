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

async def ingest_player(username, months=12):
    games = await get_recent_games(username, months)
    
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
            profiles[player] = {
                "avatar": profile.get("avatar", ""),
                "title": profile.get("title", "")
            }
        except (Exception, httpx.HTTPStatusError):
            profiles[player] = {
                "avatar": "",
                "title": ""
            }

    # Group games by player pair and keep only the most recent for each pair
    recent_games = {}
    for g in games:
        white = g["white"]["username"].lower()
        black = g["black"]["username"].lower()
        pair_key = tuple(sorted([white, black]))
        
        date = g.get("end_time") or g.get("last_move_at") or g.get("start_time", "")
        
        if pair_key not in recent_games or date > recent_games[pair_key].get("date", ""):
            recent_games[pair_key] = {
                "white": white,
                "black": black,
                "url": g["url"],
                "date": date
            }

    with driver.session() as session:
        for game_data in recent_games.values():
            white = game_data["white"]
            black = game_data["black"]
            url = game_data["url"]
            date = game_data["date"]

            session.run("""
            MERGE (w:Player {username: $white})
            SET w.avatar = $white_avatar, w.title = $white_title
            MERGE (b:Player {username: $black})
            SET b.avatar = $black_avatar, b.title = $black_title
            MERGE (w)-[:PLAYED {url: $url, date: $date}]->(b)
            MERGE (b)-[:PLAYED {url: $url, date: $date}]->(w)
            """, 
            white=white, 
            black=black, 
            url=url, 
            date=date,
            white_avatar=profiles.get(white, {}).get("avatar", ""),
            white_title=profiles.get(white, {}).get("title", ""),
            black_avatar=profiles.get(black, {}).get("avatar", ""),
            black_title=profiles.get(black, {}).get("title", "")
            )

    # Store metadata about the data ingestion
    with driver.session() as session:
        from datetime import datetime, timedelta
        twelve_months_ago = datetime.now() - timedelta(days=365)
        
        session.run("""
        MERGE (meta:DataMetadata)
        SET meta.last_refreshed = datetime(),
            meta.storing_from = date($storing_from),
            meta.months_of_data = $months
        """, 
        storing_from=twelve_months_ago.date(),
        months=months
        )

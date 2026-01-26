from chess_api import get_recent_games
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASSWORD)
)

async def ingest_player(username):
    games = await get_recent_games(username)

    with driver.session() as session:
        for g in games:
            white = g["white"]["username"].lower()
            black = g["black"]["username"].lower()
            url = g["url"]

            session.run("""
            MERGE (w:Player {username: $white})
            MERGE (b:Player {username: $black})
            MERGE (w)-[:PLAYED {url: $url}]->(b)
            MERGE (b)-[:PLAYED {url: $url}]->(w)
            """, white=white, black=black, url=url)

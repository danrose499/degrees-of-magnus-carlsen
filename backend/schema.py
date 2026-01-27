from neo4j import GraphDatabase
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class SchemaManager:
    def __init__(self, driver):
        self.driver = driver
    
    def create_constraints_and_indexes(self):
        """Create database constraints and indexes for optimal performance"""
        with self.driver.session() as session:
            # Unique constraint on Player username
            session.run("""
            CREATE CONSTRAINT player_username_unique IF NOT EXISTS
            FOR (p:Player) REQUIRE p.username IS UNIQUE
            """)
            
            # Indexes for common queries
            session.run("""
            CREATE INDEX player_level_index IF NOT EXISTS
            FOR (p:Player) ON (p.distance_from_magnus)
            """)
            
            session.run("""
            CREATE INDEX game_date_index IF NOT EXISTS
            FOR ()-[r:PLAYED]-() ON (r.date)
            """)
            
            session.run("""
            CREATE INDEX player_last_updated IF NOT EXISTS
            FOR (p:Player) ON (p.last_updated)
            """)
    
    def get_database_stats(self) -> Dict:
        """Get current database usage statistics"""
        with self.driver.session() as session:
            result = session.run("""
            MATCH (p:Player)
            RETURN count(p) as player_count,
                   sum(p.games_played) as total_games_count
            """)
            
            player_stats = result.single()
            
            result = session.run("""
            MATCH ()-[r:PLAYED]-()
            RETURN count(DISTINCT r) as relationship_count
            """)
            
            rel_stats = result.single()
            
            return {
                "players": player_stats["player_count"],
                "relationships": rel_stats["relationship_count"],
                "total_games": player_stats["total_games_count"] or 0
            }
    
    def get_storage_breakdown(self) -> Dict:
        """Get detailed storage breakdown by player level and activity"""
        with self.driver.session() as session:
            result = session.run("""
            MATCH (p:Player)
            RETURN p.distance_from_magnus as level,
                   count(p) as player_count,
                   sum(p.games_played) as total_games,
                   avg(p.games_played) as avg_games
            ORDER BY level
            """)
            
            breakdown = {}
            for record in result:
                level = record["level"] or "unknown"
                breakdown[level] = {
                    "players": record["player_count"],
                    "total_games": record["total_games"] or 0,
                    "avg_games": round(record["avg_games"] or 0, 1)
                }
            
            return breakdown

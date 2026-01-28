from chess_api import get_recent_games, get_player_profile, fetch
from neo4j import GraphDatabase
from pydantic_settings import BaseSettings
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Set, Dict, List, Optional
import logging
from schema import SchemaManager

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    max_players_per_level: int = 5000   # Reduced for GitHub Actions
    max_total_players: int = 20000     # Reduced for GitHub Actions
    max_months_historical: int = 36    # 3 years instead of 10 for initial run
    github_actions_mode: bool = True   # Flag for GitHub Actions optimizations

    class Config:
        env_file = ".env"

settings = Settings()

driver = GraphDatabase.driver(
    settings.neo4j_uri,
    auth=(settings.neo4j_user, settings.neo4j_password)
)

schema_manager = SchemaManager(driver)

class EnhancedIngestion:
    def __init__(self):
        self.processed_players: Set[str] = set()
        self.level_players: Dict[int, Set[str]] = {}
        
    async def get_player_games_all_time(self, username: str) -> List[Dict]:
        """Get all available games for a player"""
        try:
            # Get player profile with archives
            profile = await get_player_profile(username)
            logger.info(f"Profile keys for {username}: {list(profile.keys())}")
            logger.info(f"Full profile data: {profile}")
            
            archives = profile.get("archives", [])
            
            if not archives:
                logger.warning(f"No archives found for {username}")
                # Try the archives endpoint directly
                try:
                    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
                    logger.info(f"Trying direct archives URL: {archives_url}")
                    archives_data = await fetch(archives_url)
                    archives = archives_data.get("archives", [])
                    logger.info(f"Direct archives result: {len(archives)} archives found")
                except Exception as e:
                    logger.error(f"Direct archives fetch failed: {e}")
                    return []
            
            if not archives:
                logger.warning(f"Still no archives found for {username}")
                return []
            
            logger.info(f"Found {len(archives)} archives for {username}")
            games = []
            
            # Process archives in batches to avoid rate limiting
            batch_size = 6 if settings.github_actions_mode else 12  # Smaller batches for GitHub Actions
            
            for i in range(0, len(archives), batch_size):
                batch_urls = archives[i:i+batch_size]
                logger.info(f"Processing batch {i//batch_size + 1} with {len(batch_urls)} archives")
                
                for url in batch_urls:
                    try:
                        data = await fetch(url)  # Fetch the specific archive URL
                        if data and "games" in data:
                            batch_games = data["games"]
                            games.extend(batch_games)
                            logger.info(f"Got {len(batch_games)} games from {url}")
                        else:
                            logger.warning(f"No games found in archive: {url}")
                    except Exception as e:
                        logger.warning(f"Failed to fetch games for {username} from {url}: {e}")
                        continue
                
                # Add delay between batches to be respectful to the API
                if i + batch_size < len(archives):
                    await asyncio.sleep(1)
            
            logger.info(f"Total games fetched for {username}: {len(games)}")
            return games
        except Exception as e:
            logger.error(f"Error fetching games for {username}: {e}")
            return []
    
    async def discover_players_recursive(self, start_username: str, max_level: int = 6) -> Dict[int, Set[str]]:
        """Discover players recursively up to max_level from start player"""
        discovered = {0: {start_username.lower()}}
        processed = {start_username.lower()}
        
        for level in range(1, max_level + 1):
            if not self._should_continue_discovery(discovered):
                break
                
            new_players = await self._discover_level_players(discovered[level - 1], processed)
            discovered[level] = new_players
            
            # Merge new players into processed set
            processed.update(new_players)
            logger.info(f"Level {level}: Discovered {len(new_players)} new players")
        
        return discovered
    
    def _should_continue_discovery(self, discovered: Dict[int, Set[str]]) -> bool:
        """Check if discovery should continue based on storage limits"""
        total_players = sum(len(players) for players in discovered.values())
        if total_players > settings.max_total_players:
            logger.warning(f"Approaching storage limit: {total_players} players")
            return False
        return True
    
    async def _discover_level_players(self, previous_level_players: Set[str], processed: Set[str]) -> Set[str]:
        """Discover new players from a given level"""
        new_players = set()
        
        for player in previous_level_players:
            try:
                games = await self.get_player_games_all_time(player)
                opponents = self._extract_opponents_from_games(games, player)
                
                for opponent in opponents:
                    if opponent not in processed:
                        new_players.add(opponent)
            
            except Exception as e:
                logger.warning(f"Failed to process games for {player}: {e}")
                continue
        
        return new_players
    
    def _extract_opponents_from_games(self, games: List[Dict], current_player: str) -> Set[str]:
        """Extract unique opponents from games list"""
        opponents = set()
        for game in games:
            white = game["white"]["username"].lower()
            black = game["black"]["username"].lower()
            
            for opponent in [white, black]:
                if opponent != current_player:
                    opponents.add(opponent)
        return opponents
    
    async def ingest_historical_data(self, start_username: str = "magnuscarlsen"):
        """One-time import of all historical data"""
        logger.info("Starting historical data import...")
        
        # Initialize schema
        schema_manager.create_constraints_and_indexes()
        
        # Discover all players within 6 levels
        logger.info(f"Discovering players from {start_username}...")
        discovered_players = await self.discover_players_recursive(start_username, 6)
        
        total_players = sum(len(players) for players in discovered_players.values())
        logger.info(f"Discovered {total_players} total players across 6 levels")
        
        # GitHub Actions optimization: limit processing time
        if settings.github_actions_mode and total_players > 1000:
            logger.warning("GitHub Actions mode: Limiting to 1000 players to avoid timeout")
            # Keep only the first few levels and limit players per level
            for level in discovered_players:
                if len(discovered_players[level]) > 200:
                    discovered_players[level] = set(list(discovered_players[level])[:200])
        
        # Ingest players level by level
        processed_count = 0
        for level, players in discovered_players.items():
            logger.info(f"Ingesting level {level} with {len(players)} players")
            
            for i, player in enumerate(players):
                try:
                    processed_count += 1
                    logger.info(f"Processing player {processed_count}/{total_players}: {player}")
                    await self.ingest_player_all_time(player, level)
                    
                    # GitHub Actions: add progress checkpoint
                    if settings.github_actions_mode and processed_count % 50 == 0:
                        logger.info(f"Progress checkpoint: {processed_count} players processed")
                        
                except Exception as e:
                    logger.error(f"Failed to ingest {player}: {e}")
                    continue
        
        # Update metadata
        self.update_ingestion_metadata("historical", datetime.now() - timedelta(days=settings.max_months_historical * 30))
        logger.info(f"Historical data import completed - processed {processed_count} players")
    
    async def ingest_player_all_time(self, username: str, distance_from_magnus: Optional[int] = None):
        """Ingest all-time data for a single player"""
        username = username.lower()
        
        # Get player profile
        try:
            profile = await get_player_profile(username)
            logger.info(f"Got profile for {username}: {profile.get('name', username)}")
        except Exception as e:
            logger.warning(f"Failed to get profile for {username}: {e}")
            profile = {}
        
        # Get all games
        logger.info(f"Fetching all games for {username}...")
        games = await self.get_player_games_all_time(username)
        logger.info(f"Found {len(games)} games for {username}")
        
        if not games:
            logger.warning(f"No games found for {username}")
            return
        
        # Process games and create relationships
        with driver.session() as session:
            # Create/update player node
            session.run("""
            MERGE (p:Player {username: $username})
            SET p.avatar = $avatar,
                p.title = $title,
                p.name = $name,
                p.country = $country,
                p.join_date = $join_date,
                p.last_updated = datetime(),
                p.games_played = $games_count,
                p.distance_from_magnus = $distance
            """, 
            username=username,
            avatar=profile.get("avatar", ""),
            title=profile.get("title", ""),
            name=profile.get("name", ""),
            country=profile.get("country", ""),
            join_date=profile.get("joined", ""),
            games_count=len(games),
            distance=distance_from_magnus
            )
            
            # Process games in batches
            processed_count = 0
            for game in games:
                white = game["white"]["username"].lower()
                black = game["black"]["username"].lower()
                
                if white == username or black == username:
                    self._create_game_relationship(session, game, username)
                    processed_count += 1
            
            logger.info(f"Processed {processed_count} games for {username}")
    
    def _create_game_relationship(self, session, game: Dict, current_player: str):
        """Create game relationship between two players"""
        white = game["white"]["username"].lower()
        black = game["black"]["username"].lower()
        
        # Create opponent node if it doesn't exist
        opponent = black if white == current_player else white
        
        session.run("""
        MERGE (o:Player {username: $opponent})
        SET o.last_updated = datetime()
        """, opponent=opponent)
        
        # Create game relationship
        game_data = {
            "url": game.get("url", ""),
            "date": datetime.fromtimestamp(game.get("end_time", 0)) if game.get("end_time") else None,
            "white": game["white"]["username"].lower(),
            "black": game["black"]["username"].lower(),
            "result": game.get("white", {}).get("result", ""),
            "time_control": game.get("time_control", ""),
            "rated": game.get("rated", False)
        }
        
        session.run("""
        MATCH (w:Player {username: $white}), (b:Player {username: $black})
        MERGE (w)-[r:PLAYED]->(b)
        SET r.url = $url,
            r.date = $date,
            r.result = $result,
            r.time_control = $time_control,
            r.rated = $rated
        """, **game_data)
    
    async def incremental_update(self, months: int = 1):
        """Monthly incremental update of recent games"""
        logger.info(f"Starting incremental update for {months} months")
        
        # Get all players that need updating
        with driver.session() as session:
            result = session.run("""
            MATCH (p:Player)
            WHERE p.last_updated < date() - duration({days: 30})
            RETURN p.username as username
            ORDER BY p.distance_from_magnus ASC
            LIMIT 1000
            """)
            
            players_to_update = [record["username"] for record in result]
        
        # Update each player's recent games
        for player in players_to_update:
            try:
                await self.ingest_recent_games(player, months)
            except Exception as e:
                logger.error(f"Failed to update {player}: {e}")
        
        self.update_ingestion_metadata("incremental", datetime.now() - timedelta(days=30*months))
        logger.info("Incremental update completed")
    
    async def ingest_recent_games(self, username: str, months: int):
        """Ingest only recent games for a player"""
        username = username.lower()
        
        try:
            games = await get_recent_games(username, months)
            
            with driver.session() as session:
                for game in games:
                    self._create_game_relationship(session, game, username)
                
                # Update last_updated timestamp
                session.run("""
                MATCH (p:Player {username: $username})
                SET p.last_updated = datetime()
                """, username=username)
        
        except Exception as e:
            logger.error(f"Failed to ingest recent games for {username}: {e}")
    
    def update_ingestion_metadata(self, ingestion_type: str, from_date: datetime):
        """Update metadata about the ingestion process"""
        with driver.session() as session:
            # Get counts first
            player_count = session.run("MATCH (p:Player) RETURN count(p) as count").single()["count"]
            rel_count = session.run("MATCH ()-[r:PLAYED]-() RETURN count(DISTINCT r) as count").single()["count"]
            
            # Update metadata
            session.run("""
            MERGE (meta:DataMetadata)
            SET meta.last_refreshed = datetime(),
                meta.storing_from = date($from_date),
                meta.ingestion_type = $type,
                meta.total_players = $player_count,
                meta.total_relationships = $rel_count
            """, from_date=from_date, type=ingestion_type, player_count=player_count, rel_count=rel_count)
    
    def cleanup_old_data(self, max_age_years: int = 5):
        """Remove players and games older than specified age"""
        cutoff_date = datetime.now() - timedelta(days=max_age_years * 365)
        
        with driver.session() as session:
            # Remove old game relationships
            result = session.run("""
            MATCH ()-[r:PLAYED]-()
            WHERE r.date < date($cutoff_date)
            DELETE r
            RETURN count(r) as deleted_games
            """, cutoff_date=cutoff_date.date())
            
            deleted_games = result.single()["deleted_games"]
            
            # Remove players with no games
            result = session.run("""
            MATCH (p:Player)
            WHERE NOT (p)-[:PLAYED]-()
            DELETE p
            RETURN count(p) as deleted_players
            """)
            
            deleted_players = result.single()["deleted_players"]
            
            logger.info(f"Cleanup completed: {deleted_games} games, {deleted_players} players removed")
            
            return {"deleted_games": deleted_games, "deleted_players": deleted_players}
    
    def monitor_storage_usage(self) -> Dict:
        """Monitor current storage usage and recommendations"""
        stats = schema_manager.get_database_stats()
        breakdown = schema_manager.get_storage_breakdown()
        
        # Calculate usage percentage (assuming AuraDB Free limits)
        player_usage_pct = (stats["players"] / 1023) * 100
        rel_usage_pct = (stats["relationships"] / 3298) * 100
        
        recommendations = []
        if player_usage_pct > 80:
            recommendations.append("Approaching player limit - consider cleanup or upgrade")
        if rel_usage_pct > 80:
            recommendations.append("Approaching relationship limit - consider cleanup or upgrade")
        
        # Identify heavy storage users
        heavy_users = []
        for level, data in breakdown.items():
            if data["players"] > settings.max_players_per_level:
                heavy_users.append({"level": level, "count": data["players"]})
        
        if heavy_users:
            recommendations.append(f"Consider limiting players in levels: {[u['level'] for u in heavy_users]}")
        
        return {
            "current_stats": stats,
            "usage_percentages": {
                "players": round(player_usage_pct, 1),
                "relationships": round(rel_usage_pct, 1)
            },
            "breakdown": breakdown,
            "recommendations": recommendations,
            "heavy_users": heavy_users
        }

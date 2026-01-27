import asyncio
import logging
from datetime import datetime, timedelta
from enhanced_ingest import EnhancedIngestion
from schema import SchemaManager
from ingest import driver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/chess_update.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ChessDataScheduler:
    def __init__(self):
        self.ingestion = EnhancedIngestion()
        self.schema_manager = SchemaManager(driver)
        
    async def run_monthly_update(self):
        """Run monthly incremental update"""
        logger.info("Starting monthly data update")
        try:
            await self.ingestion.incremental_update(months=1)
            
            # Monitor storage usage
            usage = self.ingestion.monitor_storage_usage()
            logger.info(f"Storage usage: {usage['usage_percentages']}")
            
            # Auto-cleanup if needed
            if usage['usage_percentages']['players'] > 85:
                logger.warning("High storage usage detected, running cleanup")
                self.ingestion.cleanup_old_data(max_age_years=3)
                
        except Exception as e:
            logger.error(f"Monthly update failed: {e}")
    
    async def run_weekly_check(self):
        """Weekly check for new players and storage monitoring"""
        logger.info("Starting weekly check")
        try:
            # Check for new players around Magnus
            await self.ingestion.ingest_recent_games("magnuscarlsen", 1)
            
            # Monitor storage
            usage = self.ingestion.monitor_storage_usage()
            if usage['recommendations']:
                logger.warning(f"Storage recommendations: {usage['recommendations']}")
                
        except Exception as e:
            logger.error(f"Weekly check failed: {e}")
    
    def setup_cron_jobs(self):
        """Setup cron job strings for system scheduling"""
        return {
            "monthly": "0 2 1 * *",  # 2 AM on 1st of each month
            "weekly": "0 3 * * 0",   # 3 AM every Sunday
            "daily_monitor": "0 4 * * *"  # 4 AM daily for monitoring
        }

# CLI interface for manual execution
async def main():
    import sys
    
    scheduler = ChessDataScheduler()
    
    if len(sys.argv) < 2:
        print("Usage: python scheduler.py [historical|monthly|weekly|monitor|cleanup]")
        return
    
    command = sys.argv[1]
    
    if command == "historical":
        await scheduler.ingestion.ingest_historical_data()
    elif command == "monthly":
        await scheduler.run_monthly_update()
    elif command == "weekly":
        await scheduler.run_weekly_check()
    elif command == "monitor":
        usage = scheduler.ingestion.monitor_storage_usage()
        print(f"Storage Usage: {usage}")
    elif command == "cleanup":
        result = scheduler.ingestion.cleanup_old_data()
        print(f"Cleanup result: {result}")
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    asyncio.run(main())

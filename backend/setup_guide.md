# Enhanced Chess Database System Setup Guide

## Overview

This enhanced system provides:
- **All-time historical data storage** with intelligent optimization
- **Recursive player discovery** (6 levels from Magnus)
- **Automated incremental updates** (monthly/weekly)
- **Storage monitoring** and automatic cleanup
- **Rate-limit aware API usage**

## Installation

```bash
pip install -r requirements.txt
```

## Environment Variables

Update your `.env` file with the new settings:

```env
NEO4J_URI=your_neo4j_uri_here
NEO4J_USER=your_neo4j_user_here
NEO4J_PASSWORD=your_neo4j_password_here

# New optional settings
MAX_PLAYERS_PER_LEVEL=10000
MAX_TOTAL_PLAYERS=50000
MAX_MONTHS_HISTORICAL=120
```

## One-Time Historical Setup

Run this once to import all historical data:

```bash
python scheduler.py historical
```

This will:
1. Discover all players within 6 levels of Magnus
2. Import all their historical games
3. Set up database indexes and constraints
4. Store metadata about the import

## Scheduled Updates

### Monthly Updates (Recommended)
```bash
# Add to crontab: 0 2 1 * * (2 AM on 1st of each month)
python scheduler.py monthly
```

### Weekly Updates
```bash
# Add to crontab: 0 3 * * 0 (3 AM every Sunday)
python scheduler.py weekly
```

### Daily Monitoring
```bash
# Add to crontab: 0 4 * * * (4 AM daily)
python scheduler.py monitor
```

## Storage Management

### Monitor Current Usage
```bash
python scheduler.py monitor
```

### Manual Cleanup
```bash
# Remove data older than 5 years
python scheduler.py cleanup
```

## Data Model Enhancements

### Player Nodes
```cypher
(:Player {
  username: string,           // Unique identifier
  avatar: string,             // Profile picture URL
  title: string,              // GM, IM, etc.
  name: string,               // Real name
  country: string,            // Country code
  join_date: date,            // Chess.com join date
  last_updated: datetime,     // Last data refresh
  games_played: integer,      // Total games in database
  distance_from_magnus: integer // Degrees from Magnus (0-6)
})
```

### Game Relationships
```cypher
(:Player)-[:PLAYED {
  url: string,               // Game URL
  date: date,                // Game date
  result: string,            // Game result
  time_control: string,      // Time class
  rated: boolean             // Rated game flag
}]->(:Player)
```

## Storage Optimization Features

1. **Deduplication**: Only one game per player pair (most recent)
2. **Level-based limits**: Configurable limits per discovery level
3. **Automatic cleanup**: Removes old data when limits approached
4. **Incremental updates**: Only fetches recent data for updates

## Monitoring Dashboard

The system provides detailed storage analytics:
- Current player/relationship counts
- Usage percentages vs AuraDB limits
- Breakdown by discovery level
- Automated recommendations

## Rate Limiting

The system includes built-in rate limiting:
- Batch processing of API calls
- Delays between archive requests
- Error handling for API limits

## Expected Storage Usage

Based on current data:
- **1,023 players** (1% of AuraDB limit)
- **3,298 relationships** (1% of AuraDB limit)
- **Estimated final**: ~15,000 players, ~45,000 relationships

This leaves significant room for growth within AuraDB Free tier.

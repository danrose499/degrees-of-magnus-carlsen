# Deployment Guide - Automated Chess Data Updates

## GitHub Actions Setup (Recommended)

### 1. Repository Secrets

Add these secrets to your GitHub repository:

**Required:**
- `NEO4J_URI` - Your Neo4j database URI
- `NEO4J_USER` - Database username  
- `NEO4J_PASSWORD` - Database password

**Optional:**
- `MAX_PLAYERS_PER_LEVEL` - Player limit per discovery level (default: 10000)
- `MAX_TOTAL_PLAYERS` - Total player limit (default: 50000)

### 2. Automated Schedule

The workflow runs on three schedules:

| Schedule | Time (UTC) | Purpose |
|----------|------------|---------|
| Monthly | 2nd day, 02:00 | Full incremental update |
| Weekly | Sunday, 03:00 | Quick check for new players |
| Daily | 04:00 | Storage monitoring |

### 3. Manual Triggers

You can also trigger jobs manually from GitHub Actions tab:
- **Historical** - One-time full import
- **Monthly** - Incremental update
- **Weekly** - Quick check
- **Monitor** - Storage usage report
- **Cleanup** - Remove old data

## Alternative: Local Cron Jobs

If you prefer local execution:

### Setup crontab:
```bash
crontab -e
```

### Add these lines:
```bash
# Monthly update - 2 AM on 2nd of each month
0 2 2 * * cd /path/to/degrees-of-magnus-carlsen/backend && python scheduler.py monthly

# Weekly check - 3 AM every Sunday  
0 3 * * 0 cd /path/to/degrees-of-magnus-carlsen/backend && python scheduler.py weekly

# Daily monitoring - 4 AM every day
0 4 * * * cd /path/to/degrees-of-magnus-carlsen/backend && python scheduler.py monitor
```

## Environment Setup

### For GitHub Actions:
Configure repository secrets as mentioned above.

### For Local Cron:
Create `.env` file in backend directory:
```env
NEO4J_URI=your_neo4j_uri_here
NEO4J_USER=your_neo4j_user_here  
NEO4J_PASSWORD=your_neo4j_password_here
MAX_PLAYERS_PER_LEVEL=10000
MAX_TOTAL_PLAYERS=50000
```

## Monitoring

### GitHub Actions:
- Check Actions tab in GitHub for job status
- Download log artifacts for debugging
- Set up notifications in repository settings

### Local Cron:
```bash
# Check cron logs
tail -f /var/log/cron.log

# Check application logs
tail -f backend/logs/chess_update.log
```

## First Run

1. **Setup secrets/environment**
2. **Run historical import:**
   - GitHub Actions: Trigger "historical" job manually
   - Local: `python scheduler.py historical`
3. **Verify data:**
   ```bash
   python scheduler.py monitor
   ```

## Troubleshooting

### Common Issues:
- **API Rate Limits**: Jobs include delays, but may need adjustment
- **Database Connection**: Verify Neo4j credentials and network access
- **Storage Limits**: Monitor usage and adjust cleanup thresholds

### Debug Mode:
Add logging to see detailed progress:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Recommendations

**Use GitHub Actions** because:
- ✅ No server maintenance required
- ✅ Built-in logging and monitoring
- ✅ Easy manual triggers
- ✅ Secure secret management
- ✅ Free for public repositories

**Use Local Cron** only if:
- You need immediate control over execution
- You have specific network requirements
- You prefer keeping data processing local

import asyncio
import logging
from chess_api import get_player_profile, get_recent_games

logging.basicConfig(level=logging.INFO)

async def test_chess_api():
    """Test the Chess.com API to verify it's working"""
    
    # Test 1: Get Magnus profile
    print("Testing Magnus profile...")
    try:
        profile = await get_player_profile("magnuscarlsen")
        print(f"✅ Got profile: {profile.get('name', 'Unknown')} ({profile.get('username', 'Unknown')})")
        print(f"   Archives: {len(profile.get('archives', []))} months available")
    except Exception as e:
        print(f"❌ Profile failed: {e}")
        return
    
    # Test 2: Get recent games
    print("\nTesting recent games...")
    try:
        games = await get_recent_games("magnuscarlsen", 1)
        print(f"✅ Got {len(games)} recent games")
        if games:
            print(f"   Latest game: {games[0].get('url', 'No URL')}")
    except Exception as e:
        print(f"❌ Games failed: {e}")
        return
    
    print("\n✅ API tests passed!")

if __name__ == "__main__":
    asyncio.run(test_chess_api())

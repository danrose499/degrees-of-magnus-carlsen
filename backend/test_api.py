import asyncio
import logging
import json
from chess_api import get_player_profile, get_recent_games, fetch

logging.basicConfig(level=logging.INFO)

async def test_chess_api():
    """Test the Chess.com API to verify it's working"""
    
    # Test 1: Get Magnus profile
    print("Testing Magnus profile...")
    try:
        profile = await get_player_profile("magnuscarlsen")
        print(f"✅ Got profile: {profile.get('name', 'Unknown')} ({profile.get('username', 'Unknown')})")
        print(f"   Archives: {len(profile.get('archives', []))} months available")
        
        if profile.get('archives'):
            print(f"   First archive: {profile['archives'][0]}")
            print(f"   Last archive: {profile['archives'][-1]}")
            
            # Test fetching one archive
            print("\nTesting archive fetch...")
            archive_data = await fetch(profile['archives'][0])
            print(f"✅ Archive data keys: {list(archive_data.keys())}")
            if 'games' in archive_data:
                print(f"   Games in first archive: {len(archive_data['games'])}")
                if archive_data['games']:
                    print(f"   First game: {archive_data['games'][0].get('url', 'No URL')}")
        else:
            print("❌ No archives found!")
            
    except Exception as e:
        print(f"❌ Profile failed: {e}")
        return
    
    print("\n✅ API tests passed!")

if __name__ == "__main__":
    asyncio.run(test_chess_api())

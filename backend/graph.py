from ingest import driver

def find_path(username):
    with driver.session() as session:
        result = session.run("""
        MATCH (me:Player {username: $username}),
              (magnus:Player {username: "magnuscarlsen"})
        MATCH p = shortestPath((me)-[:PLAYED*..6]-(magnus))
        RETURN [n IN nodes(p) | {username: n.username, avatar: n.avatar, title: n.title}] AS path,
               [r IN relationships(p) | {url: r.url, date: r.date}] AS games
        """, username=username)

        record = result.single()
        return {
            "path": record["path"] if record else None,
            "games": record["games"] if record else None
        }

def get_data_metadata():
    with driver.session() as session:
        result = session.run("""
        MATCH (meta:DataMetadata)
        RETURN meta.last_refreshed AS last_refreshed,
               meta.storing_from AS storing_from,
               meta.months_of_data AS months_of_data
        """)
        
        record = result.single()
        if record:
            return {
                "last_refreshed": record["last_refreshed"],
                "storing_from": record["storing_from"], 
                "months_of_data": record["months_of_data"]
            }
        return None

from ingest import driver

def find_path(username):
    with driver.session() as session:
        result = session.run("""
        MATCH (me:Player {username: $username}),
              (magnus:Player {username: "magnuscarlsen"})
        MATCH p = shortestPath((me)-[:PLAYED*..6]-(magnus))
        RETURN [n IN nodes(p) | {username: n.username, avatar: n.avatar}] AS path,
               [r IN relationships(p) | {url: r.url, date: r.date}] AS games
        """, username=username)

        record = result.single()
        return {
            "path": record["path"] if record else None,
            "games": record["games"] if record else None
        }

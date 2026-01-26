def find_path(username):
    with driver.session() as session:
        result = session.run("""
        MATCH (me:Player {username: $username}),
              (magnus:Player {username: "magnuscarlsen"})
        MATCH p = shortestPath((me)-[:PLAYED*..6]-(magnus))
        RETURN [n IN nodes(p) | n.username] AS path
        """, username=username)

        record = result.single()
        return {"path": record["path"] if record else None}

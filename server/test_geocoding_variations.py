import osmnx as ox

locations = ["美麗華", "美麗華百樂園", "台北101", "象山"]

def try_geocode(name):
    print(f"\nTesting '{name}':")
    
    queries = [
        name,
        f"{name}, Taiwan",
        f"{name}, Taipei",
        f"台灣 {name}"
    ]
    
    for q in queries:
        try:
            res = ox.geocode(q)
            print(f"  Query '{q}' -> SUCCESS: {res}")
            return # Stop after first success
        except Exception as e:
            print(f"  Query '{q}' -> FAILED")

for loc in locations:
    try_geocode(loc)

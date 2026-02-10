import osmnx as ox
import networkx as nx

class OSMnxService:
    @staticmethod
    def get_travel_estimate(lat1, lon1, lat2, lon2, mode="car"):
        # Mode config
        configs = {
            "car": {"network_type": "drive", "speed": 40},
            "motorcycle": {"network_type": "drive", "speed": 45},
            "bike": {"network_type": "bike", "speed": 15},
            "walk": {"network_type": "walk", "speed": 5},
        }
        
        config = configs.get(mode, configs["car"])
        
        try:
            # Get nearby graph
            center_lat = (lat1 + lat2) / 2
            center_lon = (lon1 + lon2) / 2
            dist = ox.distance.great_circle_vec(lat1, lon1, lat2, lon2) + 2000
            
            G = ox.graph_from_point((center_lat, center_lon), dist=dist, network_type=config["network_type"])
            
            orig_node = ox.distance.nearest_nodes(G, lon1, lat1)
            dest_node = ox.distance.nearest_nodes(G, lon2, lat2)
            
            distance = nx.shortest_path_length(G, orig_node, dest_node, weight='length')
            duration = (distance / 1000) / config["speed"] * 60 # minutes
            
            return {
                "distance": distance,
                "duration": duration,
                "mode": mode
            }
        except Exception as e:
            print(f"OSMnx calculation error: {e}")
            return None

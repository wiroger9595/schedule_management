import osmnx as ox
import networkx as nx
import math

class OSMnxService:
    @staticmethod
    def _haversine_distance(lat1, lon1, lat2, lon2):
        """Calculate the great circle distance between two points on the earth (specified in decimal degrees)"""
        R = 6371000  # radius of Earth in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

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
            # Calculate straight line distance first
            # Use custom haversine implementation
            distance = OSMnxService._haversine_distance(lat1, lon1, lat2, lon2)
            
            # Guard clause: If distance > 2km (2000 meters), return simple estimate
            # This prevents trying to download huge graphs which crashes the server
            if distance > 2000:
                print(f"Distance {distance}m is too large for graph routing. Returning linear estimate.")
                # Estimation: distance / speed * 60 (minutes)
                # Apply a tortuosity factor of 1.5 since roads aren't straight
                duration = (distance / 1000) * 1.5 / config["speed"] * 60
                return {
                    "distance": distance,
                    "duration": duration,
                    "mode": mode,
                    "note": "Estimated (Too far for detailed routing)"
                }

            # Configure OSMnx to be less aggressive and fail faster
            ox.settings.timeout = 10
            # ox.settings.requests_kwargs = {'timeout': 10} # CONFLICTS with ox.settings.timeout
            ox.settings.requests_kwargs = {}
            
            # Get nearby graph for short distances
            center_lat = (lat1 + lat2) / 2
            center_lon = (lon1 + lon2) / 2
            dist_graph = distance + 1000 # Reduced buffer to 1km to be faster
            
            G = ox.graph_from_point(
                (center_lat, center_lon), 
                dist=dist_graph, 
                network_type=config["network_type"]
            )
            
            orig_node = ox.distance.nearest_nodes(G, lon1, lat1)
            dest_node = ox.distance.nearest_nodes(G, lon2, lat2)
            
            route_distance = nx.shortest_path_length(G, orig_node, dest_node, weight='length')
            duration = (route_distance / 1000) / config["speed"] * 60 # minutes
            
            return {
                "distance": route_distance,
                "duration": duration,
                "mode": mode
            }
        except Exception as e:
            print(f"OSMnx calculation error: {e}")
            # Fallback to linear estimate on error
            try:
                distance = OSMnxService._haversine_distance(lat1, lon1, lat2, lon2)
                duration = (distance / 1000) * 1.5 / config["speed"] * 60
                return {
                    "distance": distance,
                    "duration": duration,
                    "mode": mode,
                    "note": "Estimated (Error in routing)"
                }
            except:
                return None

    @staticmethod
    def get_travel_estimate_all(lat1, lon1, lat2, lon2):
        """Get estimates for all modes at once, optimizing graph usage"""
        modes = ["car", "motorcycle", "bus", "walk"]
        results = {}
        
        # Base configs
        configs = {
            "car": {"network_type": "drive", "speed": 40},
            "motorcycle": {"network_type": "drive", "speed": 45},
            "bus": {"network_type": "drive", "speed": 25}, # Bus is slower due to stops
            "walk": {"network_type": "walk", "speed": 5},
        }

        try:
            # 1. Calculate straight line distance
            distance = OSMnxService._haversine_distance(lat1, lon1, lat2, lon2)
            
            # center/radius
            center_lat = (lat1 + lat2) / 2
            center_lon = (lon1 + lon2) / 2
            dist_graph = distance + 1000
            
            # 2. Prepare Graphs (optimized to download once per network type)
            graphs = {}
            
            if distance <= 2000:
                # Configure timeouts
                ox.settings.timeout = 10
                # ox.settings.requests_kwargs = {'timeout': 10}
                ox.settings.requests_kwargs = {}

                # Download Drive Graph (for Car, Moto, Bus)
                try:
                    graphs['drive'] = ox.graph_from_point(
                        (center_lat, center_lon), 
                        dist=dist_graph, 
                        network_type="drive"
                    )
                except Exception as e:
                    print(f"Failed to download drive graph: {e}")
                
                # Download Walk Graph
                try:
                    graphs['walk'] = ox.graph_from_point(
                        (center_lat, center_lon), 
                        dist=dist_graph, 
                        network_type="walk"
                    )
                except Exception as e:
                    print(f"Failed to download walk graph: {e}")

            # 3. Calculate for each mode
            for mode in modes:
                config = configs[mode]
                network_type = config["network_type"]
                speed = config["speed"]
                
                G = graphs.get(network_type)
                
                if G:
                    try:
                        orig_node = ox.distance.nearest_nodes(G, lon1, lat1)
                        dest_node = ox.distance.nearest_nodes(G, lon2, lat2)
                        route_distance = nx.shortest_path_length(G, orig_node, dest_node, weight='length')
                        duration = (route_distance / 1000) / speed * 60
                        
                        results[mode] = {
                            "distance": route_distance,
                            "duration": duration,
                            "mode": mode,
                            "type": "exact"
                        }
                        continue
                    except Exception as e:
                        print(f"Routing failed for {mode}: {e}")
                
                # Fallback
                duration = (distance / 1000) * 1.5 / speed * 60
                results[mode] = {
                    "distance": distance,
                    "duration": duration,
                    "mode": mode,
                    "type": "estimated",
                    "note": "Linear estimate"
                }
                
        except Exception as e:
            print(f"Critical error in estimate_all: {e}")
            # Global fallback
            for mode in modes:
                speed = configs[mode]["speed"]
                dist = OSMnxService._haversine_distance(lat1, lon1, lat2, lon2)
                duration = (dist / 1000) * 1.5 / speed * 60
                results[mode] = {
                    "distance": dist,
                    "duration": duration,
                    "mode": mode,
                    "type": "estimated_fallback"
                }

        return results

    @staticmethod
    def get_coordinates(location_name: str):
        """Geocode a location name to (lat, lon) with prioritization for Taiwan"""
        # Prioritize local search to avoid ambiguity (e.g. "象山" resolving to China)
        queries = [
            f"{location_name}, Taipei",
            f"{location_name}, Taiwan",
            location_name
        ]
        
        for query in queries:
            try:
                # diff log: Attempting geocode for {query}
                return ox.geocode(query)
            except Exception:
                continue
                
        print(f"Geocoding failed for '{location_name}' after trying variations.")
        return None

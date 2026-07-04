import math
import logging
logger = logging.getLogger(__name__)

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
            import osmnx as ox
            import networkx as nx
            # Calculate straight line distance first
            # Use custom haversine implementation
            distance = OSMnxService._haversine_distance(lat1, lon1, lat2, lon2)
            
            # Guard clause: If distance > 2km (2000 meters), return simple estimate
            # This prevents trying to download huge graphs which crashes the server
            if distance > 2000:
                logger.info(f"Distance {distance}m is too large for graph routing. Returning linear estimate.")
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
            logger.info(f"OSMnx calculation error: {e}")
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
                    logger.info(f"Failed to download drive graph: {e}")
                
                # Download Walk Graph
                try:
                    graphs['walk'] = ox.graph_from_point(
                        (center_lat, center_lon), 
                        dist=dist_graph, 
                        network_type="walk"
                    )
                except Exception as e:
                    logger.info(f"Failed to download walk graph: {e}")

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
                        logger.info(f"Routing failed for {mode}: {e}")
                
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
            logger.info(f"Critical error in estimate_all: {e}")
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
    def get_coordinates(location_name: str, lat: float = None, lon: float = None) -> tuple:
        """
        Geocode a location name to (lat, lon) with prioritization for Taiwan and local proximity.
        Uses search_places logic to benefit from existing bias/fallback mechanisms.
        """
        # Prioritize local search to avoid ambiguity (e.g. "象山" resolving to China)
        try:
            # We use an instance to call search_places
            service = OSMnxService()
            
            # 1. Try exact search with bias
            results = service.search_places(location_name, lat, lon, zoom=14.0) # Zoom 14 is roughly district/city level
            if results:
                return (results[0]['lat'], results[0]['lon'])

            # 2. If valid lat/lon provided, maybe we don't need "Taipei" suffix as much, 
            # but if it failed, maybe it's because the name is too generic.
            # Let's try appending city/country if not found, but only if we didn't have a strong local bias.
            
            # If we are in Taiwan (rough box), try appending Taiwan
            if lat and lon and 21 <= lat <= 26 and 119 <= lon <= 123:
                 # Already handled by search_places with countrycodes='tw'
                 pass
            
            # Fallback variations if the first search yielded nothing (e.g. strict name match failed)
            queries = []
            if "捷運" in location_name and not location_name.endswith("站"):
                 queries.append(f"{location_name}站")
            
            if not lat: # Only add these generic suffixes if we DON'T have a location bias (otherwise search_places handles it)
                queries.append(f"{location_name}, Taipei")
                queries.append(f"{location_name}, Taiwan")

            for q in queries:
                results = service.search_places(q, lat, lon)
                if results:
                    return (results[0]['lat'], results[0]['lon'])

            return None

        except Exception as e:
            logger.info(f"Geocoding failed for '{location_name}': {e}")
            return None

    @staticmethod
    def reverse_geocode(lat: float, lon: float):
        """Reverse geocode (lat, lon) to address string using Nominatim API directly"""
        try:
             # OSMnx 2.0 removed reverse_geocode. Use direct Nominatim API.
             import requests
             
             url = "https://nominatim.openstreetmap.org/reverse"
             params = {
                 "lat": lat,
                 "lon": lon,
                 "format": "json",
                 "accept-language": "zh-TW,zh;q=0.9,en;q=0.8", # Prioritize Traditional Chinese
                 "zoom": 18,
                 "addressdetails": 1
             }
             headers = {
                 "User-Agent": "ScheduleManagementApp/1.0" 
             }
             
             response = requests.get(url, params=params, headers=headers, timeout=10)
             if response.status_code == 200:
                 data = response.json()
                 address = data.get('address', {})
                 
                 # Prioritize specific tags for place name
                 # Nominatim returns keys like 'tourism', 'leisure', 'amenity', 'building', 'historic' if it's a specific place
                 place_name = None
                 priority_keys = [
                     'tourism', 'leisure', 'amenity', 'shop', 'historic', 
                     'building', 'office', 'aeroway', 'railway', 'highway'
                 ]
                 
                 for key in priority_keys:
                     if key in address:
                         place_name = address[key]
                         break
                 
                 if place_name:
                     # If we found a name, check if we should append road/area for context
                     # User specifically asked for "Place Name" (e.g. 故宮) instead of address (e.g. 至善路)
                     # So returning just the name is what they want.
                     # But maybe append city/district if needed? 
                     # For now, let's just return the Name, or Name + Road if road exists.
                     # "National Palace Museum" is better than "National Palace Museum, Zhishan Rd..."
                     return place_name
                 
                 # Fallback to road + house_number if no POI name
                 road = address.get('road')
                 house_number = address.get('house_number')
                 
                 if road:
                     if house_number:
                         return f"{road} {house_number}"
                     return road
                     
                 # Last resort: full display_name
                 return data.get('display_name')
                 
             logger.info(f"Nominatim API returned status {response.status_code}: {response.text}")
             return None
        except Exception as e:
            logger.info(f"Reverse geocode failed: {e}")
            return None


    @staticmethod
    def get_nearby_pois(lat: float, lon: float, radius: int = 300):
        """Get nearby Points of Interest (POIs) using OSMnx"""
        try:
            # Define tags for interesting places
            tags = {
                'amenity': True, 
                'tourism': True, 
                'leisure': True,
                'shop': ['convenience', 'supermarket', 'mall', 'department_store'],
                'historic': True,
                'building': ['train_station', 'transportation']
                # 'office': True # Maybe too many?
            }
            
            # Use features_from_point (OSMnx 1.0+)
            gdf = ox.features_from_point((lat, lon), tags, dist=radius)
            
            if gdf.empty:
                return []

            pois = []
            # Calculate distance and sort
            # CRS transform might be needed for accurate distance, but simple euclidean on lat/lon 
            # or haversine is better. OSMnx geometries are in (lat, lon).
            
            for index, row in gdf.iterrows():
                name = row.get('name')
                if not name or str(name) == 'nan':
                    continue
                
                # Get centroid for distance calc
                geometry = row.geometry
                centroid = geometry.centroid
                
                dist = OSMnxService._haversine_distance(lat, lon, centroid.y, centroid.x)
                
                # Determine type/category
                category = "Unknown"
                if 'amenity' in row and str(row['amenity']) != 'nan':
                     category = row['amenity']
                elif 'shop' in row and str(row['shop']) != 'nan':
                     category = row['shop']
                elif 'tourism' in row and str(row['tourism']) != 'nan':
                     category = row['tourism']
                elif 'leisure' in row and str(row['leisure']) != 'nan':
                     category = row['leisure']
                     
                pois.append({
                    "name": name,
                    "category": category,
                    "distance": int(dist),
                    "lat": centroid.y,
                    "lon": centroid.x
                })
                
            # Sort by distance
            pois.sort(key=lambda x: x['distance'])
            
            # Return top 20
            return pois[:20]
            
        except Exception as e:
            logger.info(f"Error fetching POIs: {e}")
            return []

    @staticmethod
    def search_places(query: str, lat: float = None, lon: float = None, zoom: float = None):
        """Search for places using Overpass API (nearby POIs) + Nominatim (general places)
        
        Args:
            query: Search query string
            lat: Latitude of map center
            lon: Longitude of map center  
            zoom: Map zoom level (higher = more zoomed in)
        """
        import requests
        import math
        
        headers = {
            "User-Agent": "ScheduleManagementApp/1.0"
        }
        
        places = []
        
        # Step 1: Try Overpass API for nearby POI search (best for chain stores)
        if lat and lon:
            try:
                places = OSMnxService._search_overpass(query, lat, lon, zoom, headers)
            except Exception as e:
                logger.info(f"Overpass search failed: {e}")
        
        # Step 2: If Overpass returned few results, supplement with Nominatim
        if len(places) < 3:
            try:
                # Primary search
                nominatim_places = OSMnxService._search_nominatim(query, lat, lon, zoom, headers)
                
                # Retry with variations if few results
                if len(nominatim_places) == 0:
                    variations = []
                    if "捷運" not in query and ("站" in query or "Station" in query):
                         variations.append(f"捷運{query}")
                    if "捷運" in query and "站" not in query:
                         variations.append(f"{query}站")
                    
                    for v in variations:
                        logger.info(f"Retrying search with variation: {v}")
                        more_places = OSMnxService._search_nominatim(v, lat, lon, zoom, headers)
                        for mp in more_places:
                             # dedup
                             is_duplicate = False
                             for np in nominatim_places:
                                 if mp['name'] == np['name']:
                                     is_duplicate = True
                                     break
                             if not is_duplicate:
                                 nominatim_places.append(mp)
                
                for np in nominatim_places:
                    is_duplicate = False
                    for ep in places:
                        dist = math.sqrt((np['lat'] - ep['lat'])**2 + (np['lon'] - ep['lon'])**2)
                        if dist < 0.0001:  # ~10m
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        places.append(np)
            except Exception as e:
                logger.info(f"Nominatim search failed: {e}")
        
        # Sort by distance from map center
        if lat and lon and places:
            places.sort(key=lambda p: math.sqrt((p['lat'] - lat)**2 + (p['lon'] - lon)**2))
        
        return places[:15]
    
    @staticmethod
    def _search_overpass(query: str, lat: float, lon: float, zoom: float, headers: dict):
        """Search for POIs using Overpass API (OpenStreetMap data)"""
        import requests
        import time
        
        # Calculate search radius based on zoom level
        if zoom is not None and zoom > 0:
            # zoom 13 ~ 2000m, zoom 15 ~ 500m, zoom 17 ~ 150m
            radius = max(200, min(5000, int(50000 / (2 ** (zoom - 10)))))
        else:
            radius = 1000  # Default 1km
        
        # Overpass QL query: search for nodes/ways with name matching the query
        overpass_url = "https://overpass-api.de/api/interpreter"
        # Increased timeout to 25s
        overpass_query = f"""
        [out:json][timeout:25];
        (
          node["name"~"{query}",i](around:{radius},{lat},{lon});
          way["name"~"{query}",i](around:{radius},{lat},{lon});
        );
        out center body;
        """
        
        places = []
        try:
            # increased timeout to 30s
            response = requests.post(overpass_url, data={"data": overpass_query}, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                for element in data.get('elements', []):
                    tags = element.get('tags', {})
                    name = tags.get('name', '')
                    if not name:
                        continue
                    
                    # Get coordinates
                    if element['type'] == 'node':
                        p_lat = element['lat']
                        p_lon = element['lon']
                    elif element['type'] == 'way' and 'center' in element:
                        p_lat = element['center']['lat']
                        p_lon = element['center']['lon']
                    else:
                        continue
                    
                    # Build address from tags
                    addr_parts = []
                    if tags.get('addr:city'):
                        addr_parts.append(tags['addr:city'])
                    if tags.get('addr:district'):
                        addr_parts.append(tags['addr:district'])
                    if tags.get('addr:street'):
                        addr_parts.append(tags['addr:street'])
                    if tags.get('addr:housenumber'):
                        addr_parts.append(tags['addr:housenumber'])
                    address = " ".join(addr_parts) if addr_parts else tags.get('addr:full', '')
                    
                    # Add branch info to name if available
                    branch = tags.get('branch', '')
                    if branch and branch not in name:
                        name = f"{name} ({branch})"
                    
                    places.append({
                        "name": name,
                        "address": address,
                        "lat": float(p_lat),
                        "lon": float(p_lon),
                        "type": tags.get('amenity', tags.get('shop', 'place'))
                    })
        except Exception as e:
            logger.info(f"Overpass search failed: {e}")
            
        return places
    
    @staticmethod
    def _search_nominatim(query: str, lat: float = None, lon: float = None, zoom: float = None, headers: dict = None):
        """Search for places using Nominatim API (geocoding fallback)"""
        import requests
        import time
        
        if headers is None:
            headers = {"User-Agent": "ScheduleManagementApp/1.0"}
        
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "format": "json",
            "limit": 50,
            "addressdetails": 1,
            "namedetails": 1, # Request name details to find alt_names
            "accept-language": "zh-TW,zh;q=0.9,en;q=0.8",
        }
        
        if lat and lon:
            # Check if in Taiwan (Lat 21-26, Lon 119-123)
            # If in Taiwan, strictly prioritize Taiwan results
            is_in_taiwan = 21 <= lat <= 26 and 119 <= lon <= 123
            if is_in_taiwan:
                params["countrycodes"] = "tw"

            if zoom is not None and zoom > 0:
                delta = 360.0 / (2 ** zoom) * 2.0 # Increased multiplier for broader local search
                delta = max(0.005, min(0.2, delta))
            else:
                delta = 0.05  # ~5km

            params["viewbox"] = f"{lon-delta},{lat+delta},{lon+delta},{lat-delta}"
            params["bounded"] = 1
        
        # Retry mechanism (up to 2 times)
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                # Increased timeout to 20s
                response = requests.get(url, params=params, headers=headers, timeout=20)
                places = []
                
                if response.status_code == 200:
                    results = response.json()
                    places = OSMnxService._parse_nominatim_results(results, query)
                    
                    # If bounded search returned nothing, try again without bounds immediately
                    if not places and lat and lon and params.get("bounded") == 1:
                         # Create a copy of params to avoid issues with viewbox
                        retry_params = params.copy()
                        retry_params["bounded"] = 0
                        # viewbox is still sent as bias, but bounded=0 allows outside results
                        
                        try:
                            logger.info(f"[OSMnx] Local search empty, retrying global search for: {query}")
                            response = requests.get(url, params=retry_params, headers=headers, timeout=20)
                            if response.status_code == 200:
                                results = response.json()
                                places = OSMnxService._parse_nominatim_results(results, query)
                        except Exception as e:
                            logger.info(f"[OSMnx] Global fallback failed: {e}")

                    return places
                
                # If non-200, maybe retry
                if response.status_code in [429, 502, 503, 504]:
                     logger.info(f"Nominatim returned {response.status_code}, retrying ({attempt+1}/{max_retries})...")
                     time.sleep(1) # wait briefly
                     continue
                
                break # Don't retry other errors
                
            except Exception as e:
                logger.info(f"Nominatim search error (attempt {attempt}): {e}")
                if attempt < max_retries:
                    time.sleep(1)
                else:
                    return []
        return []

    @staticmethod
    def _parse_nominatim_results(results, query):
        """Helper to parse Nominatim results with smart name selection"""
        places = []
        for item in results:
            display_name = item.get('display_name', '')
            parts = display_name.split(', ')
            
            # Default name from display_name
            name = parts[0]
            address = ", ".join(parts[1:]) if len(parts) > 1 else ""
            
            # Check namedetails for a better match
            namedetails = item.get('namedetails', {})
            query_lower = query.lower()
            
            best_name = name
            
            # If the default name doesn't contain the query, look for one that does in namedetails
            if query_lower not in name.lower():
                for key, val in namedetails.items():
                    if val and query_lower in val.lower():
                        best_name = val
                        # If we found an exact match, stop
                        if val.lower() == query_lower:
                            break
            
            # If we changed the name, maybe append the original name to address for context
            if best_name != name:
                address = f"{name}, {address}"
                name = best_name
            
            places.append({
                "name": name,
                "address": address,
                "lat": float(item['lat']),
                "lon": float(item['lon']),
                "type": item.get('type', 'unknown')
            })
        return places

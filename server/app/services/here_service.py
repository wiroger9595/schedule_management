import requests
import os
from typing import List, Optional

class HereService:
    @staticmethod
    def _get_api_key() -> str:
        key = os.getenv("HERE_API_KEY")
        if not key:
            print("WARNING: HERE_API_KEY environment variable is not set!")
        return key

    @staticmethod
    def search_places(query: str, lat: Optional[float] = None, lon: Optional[float] = None, zoom: Optional[float] = None) -> List[dict]:
        """Search for places using HERE Discover API"""
        api_key = HereService._get_api_key()
        if not api_key:
            return []

        url = "https://discover.search.hereapi.com/v1/discover"
        params = {
            "q": query,
            "apiKey": api_key,
            "limit": 15,
            "lang": "zh-TW"
        }

        # If we have coordinates, use them to bias the search
        # The 'at' parameter is perfect for this, as it prioritizes places near the location
        # but doesn't strictly boundary them if no results are found.
        if lat is not None and lon is not None:
            params["at"] = f"{lat},{lon}"

        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                places = []
                for item in data.get("items", []):
                    # For places, the 'title' usually contains the POI name
                    name = item.get("title", "")
                    
                    # Formatting address
                    address = item.get("address", {}).get("label", "")
                    # Remove the name from the beginning of the address label if it duplicates it
                    if address.startswith(name + ", "):
                        address = address[len(name) + 2:]
                        
                    places.append({
                        "name": name,
                        "address": address,
                        "lat": item.get("position", {}).get("lat"),
                        "lon": item.get("position", {}).get("lng"),
                        "type": item.get("resultType", "unknown")
                    })
                return places
            else:
                print(f"HERE Discover API error: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"HERE search failed: {e}")
            return []

    @staticmethod
    def get_coordinates(location_name: str, lat: float = None, lon: float = None) -> Optional[tuple]:
        """
        Geocode a location name to (lat, lon) using HERE API.
        """
        results = HereService.search_places(location_name, lat, lon)
        if results:
            return (results[0]['lat'], results[0]['lon'])
        return None

    @staticmethod
    def reverse_geocode(lat: float, lon: float) -> Optional[str]:
        """Reverse geocode (lat, lon) to a name or address using HERE RevGeocode API"""
        api_key = HereService._get_api_key()
        if not api_key:
            return None

        url = "https://revgeocode.search.hereapi.com/v1/revgeocode"
        params = {
            "at": f"{lat},{lon}",
            "apiKey": api_key,
            "limit": 1,
            "lang": "zh-TW"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                if items:
                    item = items[0]
                    # Try to return the name of the place if it is a POI, else fallback to street/label
                    name = item.get("title")
                    if item.get("resultType") == "place" and name:
                        return name
                    
                    # Fallback to address formatting
                    addr = item.get("address", {})
                    street = addr.get("street")
                    houseNumber = addr.get("houseNumber")
                    if street:
                        return f"{street} {houseNumber}" if houseNumber else street
                        
                    return addr.get("label", "")
            else:
                print(f"HERE RevGeocode API error: {response.status_code} - {response.text}")
                
            return None
        except Exception as e:
            print(f"HERE reverse geocode failed: {e}")
            return None

    @staticmethod
    def get_nearby_pois(lat: float, lon: float, radius: int = 300) -> List[dict]:
        """Get nearby POIs using HERE Browse API"""
        api_key = HereService._get_api_key()
        if not api_key:
            return []

        url = "https://browse.search.hereapi.com/v1/browse"
        
        # Categorize what we are looking for as "nearby pois"
        # 100-1000: Restaurant
        # 600-6000: Convenience Store
        # 300-3000: Landmarks
        # 400-4000: Transit
        # https://developer.here.com/documentation/geocoding-search-api/dev_guide/topics-places/places-category-system-full.html
        categories = "100-1000-0000,600-6300-0244,300-3000-0000,400-4000-0000,500-5000-0000,600-6000-0000,700-7000-0000"
        
        params = {
            "at": f"{lat},{lon}",
            "categories": categories,
            "limit": 20,
            "apiKey": api_key,
            "lang": "zh-TW"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                pois = []
                for item in data.get("items", []):
                    # Calculate distance
                    dist = item.get("distance", radius)
                    # HERE Browse API doesn't strictly filter by radius (it orders by distance from 'at')
                    if dist > radius:
                        continue
                        
                    name = item.get("title", "")
                    
                    # Extract general category
                    category = "Unknown"
                    cat_list = item.get("categories", [])
                    if cat_list:
                        category = cat_list[0].get("name", "Unknown")
                        
                    address = item.get("address", {}).get("label", category)
                    if address.startswith(name + ", "):
                        address = address[len(name) + 2:]
                        
                    pois.append({
                        "name": name,
                        "category": category,
                        "address": address,
                        "distance": dist,
                        "lat": item.get("position", {}).get("lat"),
                        "lon": item.get("position", {}).get("lng")
                    })
                
                # Sort by distance
                pois.sort(key=lambda x: x['distance'])
                return pois
            else:
                print(f"HERE Browse API error: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"HERE Browse failed: {e}")
            return []

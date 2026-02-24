
import requests
import json
import sys
import os

# Add server directory to path
sys.path.append(os.path.join(os.getcwd(), 'server'))

from server.app.services.osmnx_service import OSMnxService

def test_search():
    # Helper to print pretty JSON
    def print_places(places):
        for p in places:
            print(f"- {p['name']} ({p.get('address', 'No address')}) [Lat: {p['lat']}, Lon: {p['lon']}]")

    # Taiwan Coordinates (Taipei)
    lat = 25.0330
    lon = 121.5654
    
    # Search for something generic that might exist in both TW and CN
    # "Zhongshan" (San Yat-sen) is very common. 
    # Or "Wanda" (common in China) vs something else.
    # Let's try "Sogo" (Department store) or "Gym"
    query = "全家" # FamilyMart - common in TW, exists in China too?
    # Or "Din Tai Fung"
    
    # Try "Shanghai"
    query = "上海" 

    print(f"Searching for '{query}' near {lat}, {lon} (Taipei)...")
    
    # We can invoke the service directly or via API. Invoking service is faster for debugging.
    # Note: OSMnxService methods are static/class methods mostly? 
    # Check definition.
    
    try:
        service = OSMnxService()
        # Mock headers if needed, logic checks headers for user-agent
        results = service.search_places(query, lat, lon)
        print(f"Found {len(results)} results:")
        print_places(results)
        
        # Check if results are far away (e.g. lat > 30 or lon < 118 for China roughly?)
        # Taiwan is approx Lat 22-25, Lon 120-122.
        
        china_results = [r for r in results if not (21 <= r['lat'] <= 26 and 119 <= r['lon'] <= 123)]
        if china_results:
            print("\n[WARNING] Found results likely outside Taiwan:")
            print_places(china_results)
        else:
            print("\n[OK] All results seem to be within Taiwan range.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_search()

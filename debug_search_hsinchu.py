
import sys
import os
import json

# Add server directory to path
sys.path.append(os.path.join(os.getcwd(), 'server'))

from server.app.services.osmnx_service import OSMnxService

def test_search():
    # Hsinchu Station Coordinates
    lat = 24.8018
    lon = 120.9716
    
    query = "7-11"

    print(f"Searching for '{query}' near {lat}, {lon} (Hsinchu)...")
    
    try:
        service = OSMnxService()
        # Mocking Zoom level 15 (street level)
        results = service.search_places(query, lat, lon, zoom=15.0)
        
        print(f"Found {len(results)} results:")
        
        hsinchu_count = 0
        taipei_count = 0
        
        for p in results:
            print(f"- {p['name']} ({p.get('address', 'No address')}) [Lat: {p['lat']}, Lon: {p['lon']}]")
            
            # Rough check for Hsinchu vs Taipei
            # Hsinchu Lat ~ 24.7 - 24.9
            # Taipei Lat ~ 25.0 - 25.2
            if 24.7 <= p['lat'] <= 24.9:
                hsinchu_count += 1
            elif 25.0 <= p['lat']:
                taipei_count += 1
        
        print(f"\nStats: Hsinchu={hsinchu_count}, Taipei={taipei_count}, Other={len(results)-hsinchu_count-taipei_count}")
        
        if taipei_count > hsinchu_count:
            print("[FAIL] Returned more Taipei results than Hsinchu results!")
        else:
             print("[PASS] Hsinchu results dominate.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_search()

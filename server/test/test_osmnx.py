from app.services.osmnx_service import OSMnxService
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_osmnx():
    print("Testing OSMnx Service...")
    
    # Coordinates for Taipei 101 to Taipei Main Station (Short distance, should use graph)
    lat1, lon1 = 25.033964, 121.564472
    lat2, lon2 = 25.047908, 121.517315
    
    print(f"Calculating route from ({lat1}, {lon1}) to ({lat2}, {lon2})...")
    
    try:
        result = OSMnxService.get_travel_estimate(lat1, lon1, lat2, lon2, "car")
        print("Result:", result)
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_osmnx()

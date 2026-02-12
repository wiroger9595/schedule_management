from app.services.osmnx_service import OSMnxService
import sys

# Coordinates from the failed request
lat1 = 37.32795258
lon1 = -122.01982651
lat2 = 25.0848265
lon2 = 121.5556465
mode = "car"

print(f"Testing long distance estimate...")
print(f"From: {lat1}, {lon1}")
print(f"To: {lat2}, {lon2}")

try:
    res = OSMnxService.get_travel_estimate(lat1, lon1, lat2, lon2, mode)
    if res:
        print("Success!")
        print(res)
    else:
        print("Failed: Result is None")
        sys.exit(1)
except Exception as e:
    print(f"Exception: {e}")
    sys.exit(1)

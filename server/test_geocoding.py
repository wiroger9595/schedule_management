import osmnx as ox
import sys

address = "台北101"
print(f"Geocoding address: {address}")

try:
    # ox.geocode returns (lat, lon)
    location = ox.geocode(address)
    print(f"✓ Success! Coordinates: {location}")
except Exception as e:
    print(f"✗ Error: {e}")

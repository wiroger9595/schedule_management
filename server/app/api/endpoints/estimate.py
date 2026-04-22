from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ...services.here_service import HereService

router = APIRouter()

@router.get("/")
def get_travel_estimate(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    mode: str = "drive"
):
    try:
        from ...services.osmnx_service import OSMnxService
        result = OSMnxService.get_travel_estimate(
            lat1, lon1,
            lat2, lon2,
            mode
        )
        if not result:
            raise HTTPException(status_code=400, detail="Could not calculate route")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all")
def get_all_travel_estimates(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
):
    try:
        from ...services.osmnx_service import OSMnxService
        return OSMnxService.get_travel_estimate_all(
            lat1, lon1,
            lat2, lon2
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reverse")
def reverse_geocode(lat: float, lon: float):
    try:
        address = HereService.reverse_geocode(lat, lon)
        if not address:
            raise HTTPException(status_code=404, detail="Address not found")
        return {"address": address}
    except HTTPException:
        raise 
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/nearby")
def get_nearby_pois(lat: float, lon: float, radius: int = 300):
    """Get nearby places of interest"""
    try:
        pois = HereService.get_nearby_pois(lat, lon, radius)
        return pois
    except Exception as e:
        print(f"Error in nearby endpoint: {e}")
        return []

@router.get("/search")
def search_places(q: str, lat: Optional[float] = None, lon: Optional[float] = None):
    """Search for places by name with coordinate sanity check and Nominatim fallback"""
    try:
        places = HereService.search_places_enhanced(q, lat, lon)
        return places
    except Exception as e:
        print(f"Error in search endpoint: {e}")
        return []

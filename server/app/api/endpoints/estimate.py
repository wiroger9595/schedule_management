from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ...services.osmnx_service import OSMnxService

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
        return OSMnxService.get_travel_estimate_all(
            lat1, lon1,
            lat2, lon2
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

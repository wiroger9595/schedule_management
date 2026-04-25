import requests
import os
from difflib import SequenceMatcher
from typing import List, Optional, Dict

class HereService:
    @staticmethod
    def _get_api_key() -> str:
        key = os.getenv("HERE_API_KEY")
        if not key:
            print("WARNING: HERE_API_KEY environment variable is not set!")
        return key

    @staticmethod
    def search_places(query: str, lat: Optional[float] = None, lon: Optional[float] = None) -> List[dict]:
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
    def _search_here_taiwan_wide(query: str, limit: int = 30) -> List[dict]:
        """
        HERE search without proximity bias — searches all of Taiwan.
        Uses `in=countryCode:TWN` instead of `at` so ranking is by
        name relevance rather than distance from the user.
        """
        api_key = HereService._get_api_key()
        if not api_key:
            return []
        url = "https://discover.search.hereapi.com/v1/discover"
        params = {
            "q": query,
            "apiKey": api_key,
            "limit": limit,
            "lang": "zh-TW",
            # Circle centered on Taiwan (23.9°N, 120.9°E), radius 250km covers entire island
            "in": "circle:23.9,120.9;r=250000",
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"HERE Taiwan-wide search error: {response.status_code}")
                return []
            places = []
            for item in response.json().get("items", []):
                name = item.get("title", "")
                address = item.get("address", {}).get("label", "")
                if address.startswith(name + ", "):
                    address = address[len(name) + 2:]
                places.append({
                    "name": name,
                    "address": address,
                    "lat": item.get("position", {}).get("lat"),
                    "lon": item.get("position", {}).get("lng"),
                    "type": item.get("resultType", "unknown"),
                })
            return places
        except Exception as e:
            print(f"HERE Taiwan-wide search failed: {e}")
            return []

    @staticmethod
    def search_places_enhanced(query: str, lat: Optional[float] = None, lon: Optional[float] = None) -> List[dict]:
        """
        Manual location search for the location picker screen.
        Strategy:
        1. HERE Taiwan-wide (no proximity bias, limit=30) — ranks by name match
        2. HERE proximity-biased as supplement (catches nearby unnamed POIs)
        3. Nominatim fallback if best score still low
        4. Coordinate sanity check on all results
        """
        # Step 1: Taiwan-wide search (no location bias)
        tw_places = HereService._search_here_taiwan_wide(query, limit=30)

        # Step 2: Proximity-biased search to supplement nearby results
        nearby_places = HereService.search_places(query, lat, lon) if lat and lon else []

        # Merge and score
        all_places = tw_places + nearby_places
        scored = []
        for p in all_places:
            score = HereService._name_score(query, p.get("name", ""))
            scored.append({**p, "_score": score})
        scored.sort(key=lambda x: x["_score"], reverse=True)

        # Deduplicate
        deduped = HereService._dedup(scored, threshold_km=0.15)
        best_score = deduped[0]["_score"] if deduped else 0.0

        # Step 3: Nominatim fallback if best score is still weak
        if best_score < 0.65:
            print(f"DEBUG [search]: best_score={best_score:.2f}, trying Nominatim for '{query}'")
            nom = HereService._search_nominatim(query)
            nom_scored = [{**p, "_score": HereService._name_score(query, p.get("name", ""))} for p in nom]
            deduped = HereService._dedup(nom_scored + deduped, threshold_km=0.15)
            deduped.sort(key=lambda x: x["_score"], reverse=True)
            best_score = deduped[0]["_score"] if deduped else 0.0

        # Step 4: Google Places fallback if still weak
        if best_score < 0.65:
            print(f"DEBUG [search]: best_score={best_score:.2f}, trying Google Places for '{query}'")
            goog = HereService._search_google_places(query)
            goog_scored = [{**p, "_score": HereService._name_score(query, p.get("name", ""))} for p in goog]
            deduped = HereService._dedup(goog_scored + deduped, threshold_km=0.15)
            deduped.sort(key=lambda x: x["_score"], reverse=True)

        # Step 5: Coordinate sanity check
        fixed = []
        for p in deduped:
            p_lat = p.get("lat") or 0
            p_lon = p.get("lon") or 0
            addr_str = (p.get("address") or "") + " " + (p.get("name") or "")
            if p_lat and p_lon and not HereService._coords_match_address(addr_str, p_lat, p_lon):
                corrected = HereService._nominatim_geocode_address(addr_str)
                if corrected:
                    print(f"DEBUG [search]: fixed coords for '{p['name']}' ({p_lat:.4f},{p_lon:.4f}) → ({corrected[0]:.4f},{corrected[1]:.4f})")
                    p = {**p, "lat": corrected[0], "lon": corrected[1]}
            # Strip internal scoring fields before returning to frontend
            fixed.append({k: v for k, v in p.items() if not k.startswith("_")})

        return fixed

    @staticmethod
    def _search_google_places(query: str) -> List[dict]:
        """
        Google Places Text Search — best coverage for Taiwan small businesses.
        Only called when HERE + Nominatim both score < 0.65.
        Requires GOOGLE_PLACES_API_KEY env var.
        """
        api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if not api_key:
            print("DEBUG [search]: GOOGLE_PLACES_API_KEY not set, skipping Google Places")
            return []
        try:
            response = requests.post(
                "https://places.googleapis.com/v1/places:searchText",
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": api_key,
                    "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
                },
                json={
                    "textQuery": query,
                    "languageCode": "zh-TW",
                    "regionCode": "TW",
                    "maxResultCount": 10,
                },
                timeout=10,
            )
            if response.status_code != 200:
                print(f"Google Places error: {response.status_code} - {response.text[:200]}")
                return []
            places = []
            for item in response.json().get("places", []):
                name = item.get("displayName", {}).get("text", "")
                address = item.get("formattedAddress", "")
                loc = item.get("location", {})
                places.append({
                    "name": name,
                    "address": address,
                    "lat": loc.get("latitude"),
                    "lon": loc.get("longitude"),
                    "type": "place",
                    "_source": "google",
                })
            print(f"DEBUG [search]: Google Places returned {len(places)} results")
            return places
        except Exception as e:
            print(f"Google Places search failed: {e}")
            return []

    @staticmethod
    def _name_score(query: str, name: str) -> float:
        """Score how well a HERE result name matches the user's query."""
        q = query.lower().strip()
        n = name.lower().strip()
        if not q or not n:
            return 0.0
        # Exact match
        if q == n:
            return 1.0
        # Substring match (user query contained in place name or vice versa)
        if q in n:
            return 0.88
        if n in q:
            return 0.82
        # Token overlap — useful for "星巴克 信義" matching "星巴克(信義店)"
        q_tokens = set(q.split())
        n_tokens = set(n.split())
        if q_tokens & n_tokens:
            overlap = len(q_tokens & n_tokens) / max(len(q_tokens), len(n_tokens))
            return max(overlap, SequenceMatcher(None, q, n).ratio())
        return SequenceMatcher(None, q, n).ratio()

    @staticmethod
    def _search_nominatim(query: str) -> List[dict]:
        """
        Search via Nominatim (OpenStreetMap).
        No API key required. No proximity bias — searches Taiwan-wide by default.
        """
        try:
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": query,
                    "format": "json",
                    "limit": 5,
                    "addressdetails": 1,
                    "accept-language": "zh-TW",
                    "countrycodes": "tw",      # Taiwan only; remove for global
                },
                headers={"User-Agent": "schedule-management-app/1.0"},
                timeout=8,
            )
            if response.status_code != 200:
                print(f"Nominatim error: {response.status_code}")
                return []

            results = []
            for item in response.json():
                addr = item.get("address", {})
                # Build a short readable address from the parts we care about
                parts = [
                    addr.get("road") or addr.get("suburb"),
                    addr.get("city") or addr.get("county"),
                ]
                short_addr = ", ".join(p for p in parts if p) or item.get("display_name", "")

                results.append({
                    "name": item.get("display_name", "").split(",")[0].strip(),
                    "address": short_addr,
                    "lat": float(item["lat"]),
                    "lon": float(item["lon"]),
                    "type": item.get("type", "unknown"),
                    "_source": "nominatim",
                })
            return results
        except Exception as e:
            print(f"Nominatim search failed: {e}")
            return []

    # Taiwan city/county keyword → (lat_min, lat_max, lon_min, lon_max)
    _TW_CITY_BBOX = {
        "基隆": (25.0, 25.5, 121.6, 121.9),
        "台北": (24.9, 25.3, 121.3, 121.7),
        "臺北": (24.9, 25.3, 121.3, 121.7),
        "新北": (24.7, 25.3, 121.2, 122.0),
        "桃園": (24.8, 25.1, 121.0, 121.5),
        "新竹": (24.6, 24.9, 120.8, 121.3),
        "苗栗": (24.2, 24.7, 120.6, 121.0),
        "台中": (23.9, 24.4, 120.4, 121.2),
        "臺中": (23.9, 24.4, 120.4, 121.2),
        "彰化": (23.7, 24.2, 120.3, 120.8),
        "南投": (23.5, 24.2, 120.5, 121.3),
        "雲林": (23.5, 23.9, 120.1, 120.7),
        "嘉義": (23.2, 23.7, 120.2, 120.7),
        "台南": (22.8, 23.5, 120.0, 120.6),
        "臺南": (22.8, 23.5, 120.0, 120.6),
        "高雄": (22.4, 23.2, 120.0, 120.7),
        "屏東": (22.0, 22.8, 120.4, 120.9),
        "宜蘭": (24.5, 24.9, 121.5, 121.9),
        "花蓮": (23.5, 24.5, 121.3, 121.8),
        "台東": (22.4, 23.5, 120.8, 121.4),
        "臺東": (22.4, 23.5, 120.8, 121.4),
    }

    @staticmethod
    def _coords_match_address(address: str, lat: float, lon: float) -> bool:
        """
        Return False if the address mentions a Taiwan city/county whose bounding box
        does NOT contain (lat, lon) — i.e. HERE gave us wrong coordinates.
        Returns True if no city keyword found (can't tell) or coords are in range.
        """
        for keyword, (lat_min, lat_max, lon_min, lon_max) in HereService._TW_CITY_BBOX.items():
            if keyword in address:
                in_bbox = lat_min <= lat <= lat_max and lon_min <= lon <= lon_max
                if not in_bbox:
                    print(f"DEBUG [location]: coord mismatch! address contains '{keyword}' "
                          f"but lat={lat:.4f},lon={lon:.4f} is outside {keyword} bbox")
                    return False
                return True  # First matching keyword decided it
        return True  # No city keyword found, assume OK

    @staticmethod
    def _nominatim_geocode_address(address: str) -> Optional[tuple]:
        """
        Geocode a full address string via Nominatim to get reliable coordinates.
        Used as a fallback when HERE coordinates don't match the address city.
        """
        try:
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 1, "countrycodes": "tw"},
                headers={"User-Agent": "schedule-management-app/1.0"},
                timeout=8,
            )
            if response.status_code == 200:
                results = response.json()
                if results:
                    return float(results[0]["lat"]), float(results[0]["lon"])
        except Exception as e:
            print(f"Nominatim address geocode failed: {e}")
        return None

    @staticmethod
    def _dedup(places: List[dict], threshold_km: float = 0.15) -> List[dict]:
        """Remove near-duplicate results (same place from two sources, within ~150m)."""
        import math
        kept = []
        for p in places:
            lat1, lon1 = p.get("lat") or 0, p.get("lon") or 0
            duplicate = False
            for k in kept:
                lat2, lon2 = k.get("lat") or 0, k.get("lon") or 0
                # Haversine approximation (fast, good enough for dedup)
                dlat = math.radians(lat2 - lat1)
                dlon = math.radians(lon2 - lon1)
                a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
                dist_km = 6371 * 2 * math.asin(math.sqrt(a))
                if dist_km < threshold_km:
                    duplicate = True
                    break
            if not duplicate:
                kept.append(p)
        return kept

    @staticmethod
    def validate_location(query: str, lat: float = None, lon: float = None) -> Dict:
        """
        Agentic location validation tool.
        1. HERE search (proximity-aware, good for nearby businesses)
        2. If HERE confidence < 0.75 → Nominatim fallback (no bias, better for distant landmarks)
        3. Merge, deduplicate, re-score, return best candidates.

        Returns:
            best            – highest-scored place (or None)
            candidates      – top-3 places when multiple are similarly plausible
            confidence      – score of best match (0-1)
            needs_selection – True when the caller should show a choice list
        """
        # ── Step 1: HERE search ──
        here_places = HereService.search_places(query, lat, lon)
        scored = []
        for place in here_places[:8]:
            score = HereService._name_score(query, place.get("name", ""))
            scored.append({**place, "_score": score, "_source": "here"})

        scored.sort(key=lambda x: x["_score"], reverse=True)

        # ── Distance penalty when user GPS is available ────────────────────────
        # Prevents distant exact-name matches (e.g. 新竹市東區) beating nearby
        # colloquial matches (e.g. 台北東區) when the user is clearly in Taipei.
        if lat is not None and lon is not None and scored:
            import math as _math
            for _i, _p in enumerate(scored):
                _plat, _plon = _p.get("lat") or 0, _p.get("lon") or 0
                if _plat and _plon:
                    _dlat = _math.radians(_plat - lat)
                    _dlon = _math.radians(_plon - lon)
                    _a = (_math.sin(_dlat / 2) ** 2 +
                          _math.cos(_math.radians(lat)) * _math.cos(_math.radians(_plat)) *
                          _math.sin(_dlon / 2) ** 2)
                    _dist_km = 6371 * 2 * _math.asin(_math.sqrt(max(0, _a)))
                    _factor = 0.60 if _dist_km > 100 else 0.75 if _dist_km > 50 else 0.88 if _dist_km > 15 else 1.0
                    scored[_i] = {**_p, "_score": round(_p["_score"] * _factor, 3)}
            scored.sort(key=lambda x: x["_score"], reverse=True)

        here_confidence = scored[0]["_score"] if scored else 0.0

        # ── Step 2: Nominatim fallback when HERE confidence is low ──
        if here_confidence < 0.75:
            print(f"DEBUG [location]: HERE confidence={here_confidence:.2f} < 0.75, trying Nominatim...")
            nom_places = HereService._search_nominatim(query)
            for place in nom_places:
                score = HereService._name_score(query, place.get("name", ""))
                scored.append({**place, "_score": score})
            scored.sort(key=lambda x: x["_score"], reverse=True)

        # ── Step 2b: Google Places fallback if still low ──
        best_so_far = scored[0]["_score"] if scored else 0.0
        if best_so_far < 0.65:
            print(f"DEBUG [location]: score={best_so_far:.2f} < 0.65, trying Google Places...")
            goog_places = HereService._search_google_places(query)
            for place in goog_places:
                score = HereService._name_score(query, place.get("name", ""))
                scored.append({**place, "_score": score})
            scored.sort(key=lambda x: x["_score"], reverse=True)

        # ── Step 3: Deduplicate and build candidate list ──
        deduped = HereService._dedup(scored)
        if not deduped:
            return {"best": None, "candidates": [], "confidence": 0.0, "needs_selection": False}

        best = deduped[0]
        confidence = best["_score"]

        # ── Step 4: Coordinate sanity check ──────────────────────────────────
        # HERE sometimes stores wrong coordinates (e.g. 彰化 address but Taipei coords).
        # If address city doesn't match lat/lon, re-geocode via Nominatim.
        best_lat = best.get("lat") or 0
        best_lon = best.get("lon") or 0
        best_address = best.get("address", "") + " " + best.get("name", "")
        if not HereService._coords_match_address(best_address, best_lat, best_lon):
            fixed = HereService._nominatim_geocode_address(best_address)
            if fixed:
                print(f"DEBUG [location]: corrected coords from ({best_lat:.4f},{best_lon:.4f}) to ({fixed[0]:.4f},{fixed[1]:.4f})")
                best = {**best, "lat": fixed[0], "lon": fixed[1], "_coord_fixed": True}
                # Also fix matching candidate in deduped list
                deduped[0] = best

        # Floor: never let the threshold exceed `confidence` itself, so `best` is
        # always included even when confidence < 0.5.
        threshold = max(confidence - 0.15, min(confidence, 0.5))
        candidates = [p for p in deduped if p["_score"] >= threshold][:3]

        needs_selection = confidence < 0.75 or len(candidates) > 1

        print(f"DEBUG [location]: best='{best['name']}' confidence={confidence:.2f} source={best.get('_source','?')} needs_selection={needs_selection}")

        return {
            "best": best,
            "candidates": candidates,
            "confidence": round(confidence, 3),
            "needs_selection": needs_selection,
        }

    @staticmethod
    def get_coordinates(location_name: str, lat: float = None, lon: float = None) -> Optional[tuple]:
        """
        Geocode a location name to (lat, lon).
        Uses validate_location so coord sanity check + all fallbacks are applied.
        """
        result = HereService.validate_location(location_name, lat=lat, lon=lon)
        best = result.get("best")
        if best and best.get("lat") and best.get("lon"):
            return (best["lat"], best["lon"])
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



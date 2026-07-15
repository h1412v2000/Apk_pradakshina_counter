import math
from typing import List, Optional, Tuple
from models.models import Temple

class GeofenceService:
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees) in meters.
        """
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371000 # Radius of earth in meters
        return c * r

    def find_nearest_temple(self, current_lat: float, current_lon: float, temples: List[Temple]) -> Tuple[Optional[Temple], float]:
        if not temples or current_lat is None or current_lon is None:
            return None, float('inf')

        nearest = None
        min_dist = float('inf')

        for temple in temples:
            dist = self.haversine_distance(current_lat, current_lon, temple.lat, temple.lng)
            if dist < min_dist:
                min_dist = dist
                nearest = temple

        return nearest, min_dist

    def sorted_by_distance(self, current_lat: float, current_lon: float,
                            temples: List[Temple]) -> List[Tuple[Temple, float]]:
        """
        Returns every temple paired with its live distance (meters) from the given
        coordinate, nearest first. Returns an empty list if we don't have a real
        location yet (current_lat/lon is None) rather than guessing/using a stale value.
        """
        if current_lat is None or current_lon is None or not temples:
            return []
        scored = [
            (t, self.haversine_distance(current_lat, current_lon, t.lat, t.lng))
            for t in temples
        ]
        scored.sort(key=lambda pair: pair[1])
        return scored

    def is_inside_geofence(self, current_lat: float, current_lon: float, temple: Temple) -> bool:
        """
        Check if current coordinate is within the temple's geofence radius.
        """
        if current_lat is None or current_lon is None:
            return False
        dist = self.haversine_distance(current_lat, current_lon, temple.lat, temple.lng)
        return dist <= temple.geofence_radius_m

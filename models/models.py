from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    id: Optional[int]
    phone_number: str
    name: str
    home_city: str
    created_at: str

@dataclass
class Temple:
    id: Optional[int]
    name: str
    deity: str
    city: str
    state: str
    lat: float
    lng: float
    geofence_radius_m: float
    verified: bool

@dataclass
class Visit:
    id: Optional[int]
    user_id: int
    temple_id: int
    start_time: str
    end_time: Optional[str]
    source: str  # 'auto' or 'manual'

@dataclass
class PradakshinaSession:
    id: Optional[int]
    visit_id: int
    count: int
    confidence_score: float  # 0.0 to 1.0

@dataclass
class JapaSession:
    id: Optional[int]
    user_id: int
    temple_id: Optional[int]
    mantra_name: str
    count: int
    duration_sec: int
    start_time: str

@dataclass
class Sankalpa:
    id: Optional[int]
    user_id: int
    description: str
    target_count: int
    target_type: str  # 'pradakshina' or 'japa'
    deadline_date: str
    current_progress: int
    status: str  # 'active', 'completed', 'failed'

@dataclass
class Streak:
    id: Optional[int]
    user_id: int
    streak_type: str  # 'daily'
    current_count: int
    longest_count: int
    last_active_date: str

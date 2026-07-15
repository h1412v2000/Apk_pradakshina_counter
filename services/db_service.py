import os
import sqlite3
import json
from typing import List, Optional
from models.models import User, Temple, Visit, PradakshinaSession, JapaSession, Sankalpa, Streak

DB_PATH = "pradakshina.db"

class DatabaseService:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    home_city TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Temples table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS temples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    deity TEXT NOT NULL,
                    city TEXT NOT NULL,
                    state TEXT NOT NULL,
                    lat REAL NOT NULL,
                    lng REAL NOT NULL,
                    geofence_radius_m REAL NOT NULL,
                    verified INTEGER NOT NULL CHECK (verified IN (0, 1))
                )
            """)

            # Visits table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    temple_id INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    source TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (temple_id) REFERENCES temples(id)
                )
            """)

            # Pradakshina Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pradakshina_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    visit_id INTEGER NOT NULL,
                    count INTEGER NOT NULL,
                    confidence_score REAL NOT NULL,
                    target_count INTEGER DEFAULT 0,
                    target_reached INTEGER DEFAULT 0,
                    FOREIGN KEY (visit_id) REFERENCES visits(id)
                )
            """)
            
            # Migration
            try:
                cursor.execute("ALTER TABLE pradakshina_sessions ADD COLUMN target_count INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE pradakshina_sessions ADD COLUMN target_reached INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass

            # Japa Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS japa_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    temple_id INTEGER,
                    mantra_name TEXT NOT NULL,
                    count INTEGER NOT NULL,
                    duration_sec INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (temple_id) REFERENCES temples(id)
                )
            """)

            # Sankalpas table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sankalpas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    target_count INTEGER NOT NULL,
                    target_type TEXT NOT NULL,
                    deadline_date TEXT NOT NULL,
                    current_progress INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # Streaks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS streaks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    streak_type TEXT NOT NULL,
                    current_count INTEGER NOT NULL,
                    longest_count INTEGER NOT NULL,
                    last_active_date TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            conn.commit()

        # Seed temples if table is empty
        self._seed_temples()
        self._ensure_default_user()

    def _seed_temples(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM temples")
            if cursor.fetchone()[0] == 0:
                seed_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "temples_seed.json")
                if os.path.exists(seed_path):
                    with open(seed_path, "r", encoding="utf-8") as f:
                        temples = json.load(f)
                        for t in temples:
                            cursor.execute("""
                                INSERT INTO temples (name, deity, city, state, lat, lng, geofence_radius_m, verified)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (t['name'], t['deity'], t['city'], t['state'], t['lat'], t['lng'], t['geofence_radius_m'], 1 if t['verified'] else 0))
                    conn.commit()

    def _ensure_default_user(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO users (phone_number, name, home_city, created_at)
                    VALUES ('+919999999999', 'Devotee', 'Chennai', datetime('now'))
                """)
                # Insert a default streak
                cursor.execute("""
                    INSERT INTO streaks (user_id, streak_type, current_count, longest_count, last_active_date)
                    VALUES (1, 'daily', 0, 0, date('now', '-1 day'))
                """)
                conn.commit()

    # User CRUD
    def get_user(self, user_id: int = 1) -> Optional[User]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if row:
                return User(id=row['id'], phone_number=row['phone_number'], name=row['name'], home_city=row['home_city'], created_at=row['created_at'])
        return None

    # Temples CRUD
    def get_all_temples(self) -> List[Temple]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM temples").fetchall()
            return [Temple(id=r['id'], name=r['name'], deity=r['deity'], city=r['city'], state=r['state'],
                           lat=r['lat'], lng=r['lng'], geofence_radius_m=r['geofence_radius_m'], verified=bool(r['verified'])) for r in rows]

    # Visits & Pradakshinas
    def start_visit(self, user_id: int, temple_id: int, source: str = 'auto') -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO visits (user_id, temple_id, start_time, source)
                VALUES (?, ?, datetime('now'), ?)
            """, (user_id, temple_id, source))
            conn.commit()
            return cursor.lastrowid

    def end_visit(self, visit_id: int):
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE visits SET end_time = datetime('now') WHERE id = ?
            """, (visit_id,))
            conn.commit()

    def get_recent_visits(self, user_id: int = 1, limit: int = 10):
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT v.id, v.start_time, v.end_time, v.source, t.name as temple_name, t.deity
                FROM visits v
                JOIN temples t ON v.temple_id = t.id
                WHERE v.user_id = ?
                ORDER BY v.start_time DESC
                LIMIT ?
            """, (user_id, limit)).fetchall()
            return [dict(r) for r in rows]

    def add_pradakshina_session(self, visit_id: int, count: int, confidence_score: float = 1.0, target_count: int = 0, target_reached: int = 0):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pradakshina_sessions (visit_id, count, confidence_score, target_count, target_reached)
                VALUES (?, ?, ?, ?, ?)
            """, (visit_id, count, confidence_score, target_count, target_reached))
            
            # Update streaks & active sankalpas
            cursor.execute("SELECT user_id FROM visits WHERE id = ?", (visit_id,))
            user_row = cursor.fetchone()
            if user_row:
                user_id = user_row[0]
                self._update_streak(user_id, count)
                self._update_sankalpa_progress(user_id, 'pradakshina', count)
            conn.commit()

    def _update_streak(self, user_id: int, count: int):
        if count <= 0:
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM streaks WHERE user_id = ? AND streak_type = 'daily'", (user_id,))
            row = cursor.fetchone()
            if row:
                current = row['current_count']
                longest = row['longest_count']
                last_active = row['last_active_date']
                
                # Check date difference
                # Using SQLite date function to check if the last active date was today or yesterday
                cursor.execute("SELECT date('now'), date('now', '-1 day')")
                today, yesterday = cursor.fetchone()
                
                if last_active == today:
                    # Already updated today
                    pass
                elif last_active == yesterday:
                    current += 1
                    if current > longest:
                        longest = current
                    cursor.execute("""
                        UPDATE streaks SET current_count = ?, longest_count = ?, last_active_date = date('now')
                        WHERE id = ?
                    """, (current, longest, row['id']))
                else:
                    # Streak broken or first time
                    current = 1
                    if current > longest:
                        longest = current
                    cursor.execute("""
                        UPDATE streaks SET current_count = ?, longest_count = ?, last_active_date = date('now')
                        WHERE id = ?
                    """, (current, longest, row['id']))
            conn.commit()

    def _update_sankalpa_progress(self, user_id: int, type_: str, amount: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sankalpas
                SET current_progress = current_progress + ?
                WHERE user_id = ? AND target_type = ? AND status = 'active'
            """, (amount, user_id, type_))
            
            # Auto-complete finished sankalpas
            cursor.execute("""
                UPDATE sankalpas
                SET status = 'completed'
                WHERE user_id = ? AND target_type = ? AND current_progress >= target_count AND status = 'active'
            """, (user_id, type_))
            conn.commit()

    # Japa CRUD
    def add_japa_session(self, user_id: int, temple_id: Optional[int], mantra: str, count: int, duration: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO japa_sessions (user_id, temple_id, mantra_name, count, duration_sec, start_time)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (user_id, temple_id, mantra, count, duration))
            self._update_streak(user_id, 1) # active for today
            self._update_sankalpa_progress(user_id, 'japa', count)
            conn.commit()

    # Sankalpa CRUD
    def create_sankalpa(self, user_id: int, description: str, target: int, type_: str, deadline: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sankalpas (user_id, description, target_count, target_type, deadline_date, current_progress, status)
                VALUES (?, ?, ?, ?, ?, 0, 'active')
            """, (user_id, description, target, type_, deadline))
            conn.commit()
            return cursor.lastrowid

    def get_active_sankalpas(self, user_id: int = 1) -> List[Sankalpa]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM sankalpas WHERE user_id = ? ORDER BY deadline_date ASC", (user_id,)).fetchall()
            return [Sankalpa(id=r['id'], user_id=r['user_id'], description=r['description'], target_count=r['target_count'],
                             target_type=r['target_type'], deadline_date=r['deadline_date'], current_progress=r['current_progress'], status=r['status']) for r in rows]

    # Streaks CRUD
    def get_streak(self, user_id: int = 1) -> Optional[Streak]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM streaks WHERE user_id = ? AND streak_type = 'daily'", (user_id,)).fetchone()
            if row:
                return Streak(id=row['id'], user_id=row['user_id'], streak_type=row['streak_type'],
                              current_count=row['current_count'], longest_count=row['longest_count'], last_active_date=row['last_active_date'])
        return None

    # Stats Aggregation
    def get_lifetime_stats(self, user_id: int = 1):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(ps.count) FROM pradakshina_sessions ps
                JOIN visits v ON ps.visit_id = v.id
                WHERE v.user_id = ?
            """, (user_id,))
            total_pradakshinas = cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT SUM(js.count) FROM japa_sessions js
                WHERE js.user_id = ?
            """, (user_id,))
            total_japa = cursor.fetchone()[0] or 0

            # Temple wise breakdown
            cursor.execute("""
                SELECT t.name, SUM(ps.count) as total
                FROM pradakshina_sessions ps
                JOIN visits v ON ps.visit_id = v.id
                JOIN temples t ON v.temple_id = t.id
                WHERE v.user_id = ?
                GROUP BY t.id
                ORDER BY total DESC
            """, (user_id,))
            temple_breakdown = [dict(r) for r in cursor.fetchall()]

            return {
                "total_pradakshinas": total_pradakshinas,
                "total_japa": total_japa,
                "temple_breakdown": temple_breakdown
            }

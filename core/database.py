import sqlite3
import os
import random
from datetime import datetime

DB_PATH = "data/fairway_iq.db"


def get_db_connection():
    """
    Returns a thread-safe connection configured with WAL mode and high busy-timeout
    to handle multi-user reads/writes without database locks.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20.0, check_same_thread=False)
    
    # ⚡ Performance & Concurrency Tuning
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    
    conn.row_factory = sqlite3.Row  
    return conn


def init_db():
    """Initializes the relational database schema if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Society Configuration Settings Table (Multi-tenant switchboard)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS society_settings (
        society_id TEXT PRIMARY KEY,
        society_name TEXT NOT NULL,
        tournament_format TEXT DEFAULT 'Match Play - Net',
        points_win INTEGER DEFAULT 3,
        points_draw INTEGER DEFAULT 1,
        points_loss INTEGER DEFAULT 0,
        player_directory_mode TEXT DEFAULT 'Seasonal'
    );
    """)
    
    # 2. Transient Seasonal Roster Table (Fluid seasonal registration)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS seasonal_roster (
        player_id TEXT PRIMARY KEY,
        society_id TEXT,
        season_id TEXT NOT NULL,
        player_name TEXT NOT NULL,
        handicap REAL NOT NULL,
        checked_in INTEGER DEFAULT 0,
        FOREIGN KEY (society_id) REFERENCES society_settings(society_id) ON DELETE CASCADE
    );
    """)

    # 3. Rounds Table (To group head-to-head match-ups by match-day)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rounds (
        round_id INTEGER PRIMARY KEY AUTOINCREMENT,
        season_id TEXT NOT NULL,
        round_number INTEGER NOT NULL,
        play_date TEXT NOT NULL
    );
    """)

    # 4. Matches Table (The heart of the head-to-head Match Play engine)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        match_id INTEGER PRIMARY KEY AUTOINCREMENT,
        round_id INTEGER NOT NULL,
        player_1_id TEXT NOT NULL,
        player_2_id TEXT NOT NULL,
        player_1_net_score INTEGER,  
        player_2_net_score INTEGER,  
        p1_points INTEGER DEFAULT 0,
        p2_points INTEGER DEFAULT 0,
        match_status TEXT DEFAULT 'Scheduled',
        FOREIGN KEY (round_id) REFERENCES rounds(round_id) ON DELETE CASCADE,
        FOREIGN KEY (player_1_id) REFERENCES seasonal_roster(player_id),
        FOREIGN KEY (player_2_id) REFERENCES seasonal_roster(player_id)
    );
    """)

    # 5. Golf Courses Table (Stores club profiles)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS golf_courses (
        course_id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_name TEXT NOT NULL,
        location TEXT DEFAULT "Kenya"
    );
    """)

    # 6. Course Holes Table (Stores Par and Stroke Index mapping per tee set)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS course_holes (
        hole_id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        tee_color TEXT NOT NULL,
        hole_number INTEGER NOT NULL,
        par INTEGER NOT NULL,
        stroke_index INTEGER NOT NULL,
        FOREIGN KEY (course_id) REFERENCES golf_courses(course_id) ON DELETE CASCADE,
        UNIQUE(course_id, tee_color, hole_number)
    );
    """)
    
    # 7. Relational Scorecards Table (For historical round summaries)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scorecards (
        card_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id TEXT,
        gross_score INTEGER NOT NULL,
        net_score REAL NOT NULL,
        format_played TEXT NOT NULL,
        marker_name TEXT NOT NULL,
        play_date TEXT NOT NULL,
        FOREIGN KEY (player_id) REFERENCES seasonal_roster(player_id)
    );
    """)
    
    # 8. 📱 Live Offline PWA Sync Table (Receives background sync batches from PWA clients)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS live_scorecards (
        player_id TEXT NOT NULL,
        hole_number INTEGER NOT NULL,
        score INTEGER NOT NULL,
        putts INTEGER DEFAULT 0,
        fairway_hit INTEGER DEFAULT 0,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (player_id, hole_number)
    );
    """)
    
    # Seed default Kachumbari League configurations if the table is blank
    cursor.execute("SELECT COUNT(*) FROM society_settings;")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO society_settings (society_id, society_name, points_win, points_draw, points_loss)
        VALUES ('Kachumbari', 'Kachumbari Golf League', 3, 1, 0);
        """)

    # Seed default Limuru Country Club and white tee details dynamically if blank
    cursor.execute("SELECT COUNT(*) FROM golf_courses;")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO golf_courses (course_name, location) VALUES ('Limuru Country Club', 'Kiambu');")
        limuru_id = cursor.lastrowid
        
        limuru_white_tees = [
            (1, 4, 3), (2, 4, 15), (3, 3, 11), (4, 5, 1), (5, 4, 9), (6, 4, 5), (7, 3, 13), (8, 4, 7), (9, 5, 17),
            (10, 4, 4), (11, 4, 14), (12, 3, 12), (13, 5, 2), (14, 4, 10), (15, 4, 8), (16, 3, 16), (17, 4, 6), (18, 5, 18)
        ]
        
        for hole_num, par, si in limuru_white_tees:
            cursor.execute("""
                INSERT OR IGNORE INTO course_holes (course_id, tee_color, hole_number, par, stroke_index)
                VALUES (?, 'White', ?, ?, ?)
            """, (limuru_id, hole_num, par, si))
            
        print("Limuru Country Club white tee specs successfully seeded!")
        
    conn.commit()
    conn.close()
    print("Database initialized successfully with Match Play, Roster, Course, and PWA Live Sync schemas!")


# =====================================================================
# PWA OFFLINE SYNC HANDLER (LAST-WRITE-WINS CONFLICT RESOLUTION)
# =====================================================================

def sync_pwa_scorecard_payload(player_id: str, scores_dict: dict) -> dict:
    """
    Ingests batch scorecards sent from the PWA LocalStorage sync bridge.
    Enforces a Last-Write-Wins rule using ISO timestamps.
    
    Expected scores_dict payload format:
    {
       "1": {"score": 4, "ts": "2026-08-06T10:15:00.000Z"},
       "2": {"score": 5, "ts": "2026-08-06T10:30:00.000Z"}
    }
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    synced_count = 0

    try:
        for hole_str, payload in scores_dict.items():
            hole_num = int(hole_str)
            score_val = payload.get("score")
            client_ts = payload.get("ts", datetime.utcnow().isoformat())
            
            # Fetch existing timestamp from SQLite
            cursor.execute(
                "SELECT updated_at FROM live_scorecards WHERE player_id = ? AND hole_number = ?",
                (player_id, hole_num)
            )
            existing = cursor.fetchone()

            # UPSERT only if record doesn't exist OR client timestamp is newer
            if existing is None or client_ts > existing["updated_at"]:
                cursor.execute("""
                    INSERT INTO live_scorecards (player_id, hole_number, score, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(player_id, hole_number) DO UPDATE SET
                        score = excluded.score,
                        updated_at = excluded.updated_at
                """, (player_id, hole_num, score_val, client_ts))
                synced_count += 1

        conn.commit()
        return {"status": "success", "synced_holes": synced_count}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


# =====================================================================
# DYNAMIC COURSE QUERIES
# =====================================================================

def get_course_pars_and_si(course_name, tee_color="White"):
    """
    Queries database for a given course & tee set. 
    Returns a dict formatted as: {hole_number: (par, stroke_index)}
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.hole_number, h.par, h.stroke_index 
        FROM course_holes h
        JOIN golf_courses c ON h.course_id = c.course_id
        WHERE c.course_name = ? AND h.tee_color = ?
        ORDER BY h.hole_number ASC
    """, (course_name, tee_color))
    rows = cursor.fetchall()
    conn.close()
    return {row['hole_number']: (row['par'], row['stroke_index']) for row in rows}


# =====================================================================
# MATCH PLAY CALCULATIONS & DATA WRITING
# =====================================================================

def record_match_score(match_id, p1_net, p2_net):
    """
    Updates the match with net scores and automatically calculates
    the points based on the active society rules in the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT points_win, points_draw, points_loss 
        FROM society_settings 
        LIMIT 1
    """)
    settings = cursor.fetchone()
    
    win_pts = settings['points_win'] if settings else 3
    draw_pts = settings['points_draw'] if settings else 1
    loss_pts = settings['points_loss'] if settings else 0

    if p1_net < p2_net:     
        p1_points, p2_points = win_pts, loss_pts
    elif p2_net < p1_net:   
        p1_points, p2_points = loss_pts, win_pts
    else:                   
        p1_points, p2_points = draw_pts, draw_pts
        
    cursor.execute("""
        UPDATE matches 
        SET player_1_net_score = ?, 
            player_2_net_score = ?, 
            p1_points = ?, 
            p2_points = ?, 
            match_status = 'Completed'
        WHERE match_id = ?
    """, (p1_net, p2_net, p1_points, p2_points, match_id))
    
    conn.commit()
    conn.close()
    return "Scores and league points recorded successfully!"


def generate_round_pairings(round_id, society_id, season_id):
    """
    Shuffles all checked-in players from the seasonal roster for a specific 
    society and season, then pairs them up head-to-head.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT player_id, player_name FROM seasonal_roster 
        WHERE society_id = ? AND season_id = ? AND checked_in = 1
    """, (society_id, season_id))
    
    players = cursor.fetchall()
    
    if len(players) < 2:
        conn.close()
        return "Error: You need at least 2 checked-in players to generate pairings!"
        
    player_list = [(row['player_id'], row['player_name']) for row in players]
    random.shuffle(player_list)
    
    cursor.execute("DELETE FROM matches WHERE round_id = ?", (round_id,))
    
    pairings_created = 0
    for i in range(0, len(player_list) - 1, 2):
        p1 = player_list[i]
        p2 = player_list[i+1]
        
        cursor.execute("""
            INSERT INTO matches (round_id, player_1_id, player_2_id)
            VALUES (?, ?, ?)
        """, (round_id, p1[0], p2[0]))
        pairings_created += 1
        
    conn.commit()
    conn.close()
    return f"Successfully generated {pairings_created} head-to-head matches!"


if __name__ == "__main__":
    init_db()
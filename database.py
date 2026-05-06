import sqlite3
from datetime import datetime, timedelta
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'pronosticos.db')

def init_db():
    """Inicializa la base de datos"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pronosticos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT UNIQUE,
            home_team TEXT,
            away_team TEXT,
            sport TEXT,
            sport_name TEXT,
            date TEXT,
            time TEXT,
            commence_time TEXT,
            home_odds REAL,
            away_odds REAL,
            draw_odds REAL,
            prediction TEXT,
            prediction_team TEXT,
            confidence REAL,
            is_clear_favorite INTEGER,
            is_very_safe INTEGER,
            is_risky INTEGER,
            status TEXT DEFAULT 'pending',
            result TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

def save_pronostico(match):
    """Guarda un pronóstico en la base de datos"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT OR REPLACE INTO pronosticos
            (match_id, home_team, away_team, sport, sport_name, date, time, commence_time,
             home_odds, away_odds, draw_odds, prediction, prediction_team, confidence,
             is_clear_favorite, is_very_safe, is_risky, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            match.get('id'),
            match.get('home_team'),
            match.get('away_team'),
            match.get('sport'),
            match.get('sport_name'),
            match.get('date'),
            match.get('time'),
            match.get('datetime').isoformat() if match.get('datetime') else None,
            match.get('home_odds'),
            match.get('away_odds'),
            match.get('draw_odds'),
            match.get('prediction'),
            match.get('prediction_team'),
            match.get('confidence'),
            1 if match.get('is_clear_favorite') else 0,
            1 if match.get('is_very_safe') else 0,
            1 if match.get('is_risky') else 0,
            'pending'
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()

def get_pronosticos(limit=50, status=None):
    """Obtiene pronósticos de la base de datos"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = 'SELECT * FROM pronosticos'
    params = []

    if status:
        query += ' WHERE status = ?'
        params.append(status)

    query += ' ORDER BY created_at DESC LIMIT ?'
    params.append(limit)

    cursor.execute(query, params)
    results = cursor.fetchall()

    pronosticos = []
    for row in results:
        pronostico = dict(row)
        pronostico['is_clear_favorite'] = bool(pronostico['is_clear_favorite'])
        pronostico['is_very_safe'] = bool(pronostico['is_very_safe'])
        pronostico['is_risky'] = bool(pronostico['is_risky'])
        pronosticos.append(pronostico)

    conn.close()
    return pronosticos

def get_stats():
    """Obtiene estadísticas de pronósticos"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM pronosticos')
    total = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM pronosticos WHERE status = "won"')
    won = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM pronosticos WHERE status = "lost"')
    lost = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM pronosticos WHERE status = "pending"')
    pending = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM pronosticos WHERE is_clear_favorite = 1')
    favorites = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM pronosticos WHERE is_very_safe = 1')
    very_safe = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM pronosticos WHERE is_risky = 1')
    risky = cursor.fetchone()[0]

    win_rate = 0
    if total > 0 and (won + lost) > 0:
        win_rate = round((won / (won + lost)) * 100, 1)

    conn.close()

    return {
        'total': total,
        'won': won,
        'lost': lost,
        'pending': pending,
        'favorites': favorites,
        'very_safe': very_safe,
        'risky': risky,
        'win_rate': win_rate
    }

def update_pronostico_status(match_id, status, result=None):
    """Actualiza el estado de un pronóstico"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE pronosticos
        SET status = ?, result = ?
        WHERE match_id = ?
    ''', (status, result, match_id))

    conn.commit()
    conn.close()

def get_recent_pronosticos(days=7):
    """Obtiene pronósticos de los últimos X días"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    date_limit = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    cursor.execute('''
        SELECT * FROM pronosticos
        WHERE created_at >= ?
        ORDER BY created_at DESC
    ''', (date_limit,))

    results = cursor.fetchall()

    pronosticos = []
    for row in results:
        pronostico = dict(row)
        pronostico['is_clear_favorite'] = bool(pronostico['is_clear_favorite'])
        pronostico['is_very_safe'] = bool(pronostico['is_very_safe'])
        pronostico['is_risky'] = bool(pronostico['is_risky'])
        pronosticos.append(pronostico)

    conn.close()
    return pronosticos

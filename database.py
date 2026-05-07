import os
from datetime import datetime, timedelta
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
import sqlite3

# Configuración de base de datos
DATABASE_URL = os.getenv('DATABASE_URL')
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    # PostgreSQL
    @contextmanager
    def get_db_connection():
        """Context manager para conexiones a PostgreSQL"""
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        try:
            yield conn
        finally:
            conn.close()

    def init_db():
        """Inicializa la base de datos con índices"""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pronosticos (
                    id SERIAL PRIMARY KEY,
                    match_id TEXT UNIQUE,
                    home_team TEXT,
                    away_team TEXT,
                    sport TEXT,
                    sport_name TEXT,
                    league TEXT,
                    date TEXT,
                    time TEXT,
                    commence_time TEXT,
                    home_odds REAL,
                    away_odds REAL,
                    draw_odds REAL,
                    prediction TEXT,
                    prediction_team TEXT,
                    confidence REAL,
                    is_clear_favorite BOOLEAN,
                    is_very_safe BOOLEAN,
                    is_risky BOOLEAN,
                    status TEXT DEFAULT 'active',
                    result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Crear índices para mejor rendimiento
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_match_id ON pronosticos(match_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON pronosticos(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON pronosticos(created_at DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sport ON pronosticos(sport)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_commence_time ON pronosticos(commence_time)')

    def save_pronostico(match):
        """Guarda un pronóstico en la base de datos"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO pronosticos
                    (match_id, home_team, away_team, sport, sport_name, league, date, time, commence_time,
                     home_odds, away_odds, draw_odds, prediction, prediction_team, confidence,
                     is_clear_favorite, is_very_safe, is_risky, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (match_id) DO UPDATE SET
                        home_team = EXCLUDED.home_team,
                        away_team = EXCLUDED.away_team,
                        home_odds = EXCLUDED.home_odds,
                        away_odds = EXCLUDED.away_odds,
                        draw_odds = EXCLUDED.draw_odds,
                        confidence = EXCLUDED.confidence
                ''', (
                    match.get('id'),
                    match.get('home_team'),
                    match.get('away_team'),
                    match.get('sport'),
                    match.get('sport_name'),
                    match.get('league'),
                    match.get('date'),
                    match.get('time'),
                    match.get('datetime').isoformat() if match.get('datetime') else None,
                    match.get('home_odds'),
                    match.get('away_odds'),
                    match.get('draw_odds'),
                    match.get('prediction'),
                    match.get('prediction_team'),
                    match.get('confidence'),
                    match.get('is_clear_favorite', False),
                    match.get('is_very_safe', False),
                    match.get('is_risky', False),
                    'active'
                ))
            except Exception as e:
                print(f"Error guardando pronóstico: {e}")

    def get_pronosticos(limit=50, status=None):
        """Obtiene pronósticos de la base de datos"""
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            query = 'SELECT * FROM pronosticos'
            params = []

            if status:
                query += ' WHERE status = %s'
                params.append(status)
            elif status is None:
                # No filtrar por estado, devolver todos
                pass
            else:
                query += ' WHERE status != %s'
                params.append('active')

            query += ' ORDER BY created_at DESC LIMIT %s'
            params.append(limit)

            cursor.execute(query, params)
            results = cursor.fetchall()

            return [dict(row) for row in results]

    def get_stats():
        """Obtiene estadísticas de pronósticos"""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM pronosticos')
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM pronosticos WHERE status = 'won'")
            won = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM pronosticos WHERE status = 'lost'")
            lost = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM pronosticos WHERE status = 'pending'")
            pending = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM pronosticos WHERE is_clear_favorite = TRUE')
            favorites = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM pronosticos WHERE is_very_safe = TRUE')
            very_safe = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM pronosticos WHERE is_risky = TRUE')
            risky = cursor.fetchone()[0]

            win_rate = 0
            if total > 0 and (won + lost) > 0:
                win_rate = round((won / (won + lost)) * 100, 1)

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
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE pronosticos
                SET status = %s, result = %s
                WHERE match_id = %s
            ''', (status, result, match_id))

    def get_finished_matches():
        """Obtiene partidos que ya terminaron (basado en la fecha)"""
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Usar una conversión más robusta del timestamp
            cursor.execute('''
                SELECT * FROM pronosticos
                WHERE (commence_time::timestamp with time zone) < NOW() - INTERVAL '4 hours'
                AND status = 'active'
            ''')
            results = cursor.fetchall()

            return [dict(row) for row in results]

    def mark_as_finished(match_id):
        """Marca un partido como terminado (cambia de active a pending para historial)"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE pronosticos
                SET status = 'pending'
                WHERE match_id = %s AND status = 'active'
            ''', (match_id,))

    def get_active_matches():
        """Obtiene solo partidos activos (no terminados)"""
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute('''
                SELECT * FROM pronosticos
                WHERE status = 'active'
                ORDER BY created_at DESC
            ''')
            results = cursor.fetchall()

            return [dict(row) for row in results]

else:
    # SQLite (para desarrollo local)
    DB_PATH = os.path.join(os.path.dirname(__file__), 'pronosticos.db')

    @contextmanager
    def get_db_connection():
        """Context manager para conexiones a la base de datos"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db():
        """Inicializa la base de datos con índices"""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pronosticos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id TEXT UNIQUE,
                    home_team TEXT,
                    away_team TEXT,
                    sport TEXT,
                    sport_name TEXT,
                    league TEXT,
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
                    status TEXT DEFAULT 'active',
                    result TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Crear índices para mejor rendimiento
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_match_id ON pronosticos(match_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON pronosticos(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON pronosticos(created_at DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sport ON pronosticos(sport)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_commence_time ON pronosticos(commence_time)')

            conn.commit()

    def save_pronostico(match):
        """Guarda un pronóstico en la base de datos"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO pronosticos
                    (match_id, home_team, away_team, sport, sport_name, league, date, time, commence_time,
                     home_odds, away_odds, draw_odds, prediction, prediction_team, confidence,
                     is_clear_favorite, is_very_safe, is_risky, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    match.get('id'),
                    match.get('home_team'),
                    match.get('away_team'),
                    match.get('sport'),
                    match.get('sport_name'),
                    match.get('league'),
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
                    'active'
                ))
                conn.commit()
            except sqlite3.IntegrityError:
                pass

    def get_pronosticos(limit=50, status=None):
        """Obtiene pronósticos de la base de datos"""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            query = 'SELECT * FROM pronosticos'
            params = []

            if status:
                query += ' WHERE status = ?'
                params.append(status)
            elif status is None:
                # No filtrar por estado, devolver todos
                pass
            else:
                query += ' WHERE status != ?'
                params.append('active')

            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            results = cursor.fetchall()

            return [_row_to_dict(row) for row in results]

    def get_stats():
        """Obtiene estadísticas de pronósticos"""
        with get_db_connection() as conn:
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
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE pronosticos
                SET status = ?, result = ?
                WHERE match_id = ?
            ''', (status, result, match_id))
            conn.commit()

    def get_finished_matches():
        """Obtiene partidos que ya terminaron (basado en la fecha)"""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM pronosticos
                WHERE datetime(commence_time) < datetime('now', '-4 hours')
                AND status = 'active'
            ''')
            results = cursor.fetchall()

            return [_row_to_dict(row) for row in results]

    def mark_as_finished(match_id):
        """Marca un partido como terminado (cambia de active a pending para historial)"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE pronosticos
                SET status = 'pending'
                WHERE match_id = ? AND status = 'active'
            ''', (match_id,))
            conn.commit()

    def get_active_matches():
        """Obtiene solo partidos activos (no terminados)"""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM pronosticos
                WHERE status = 'active'
                ORDER BY created_at DESC
            ''')
            results = cursor.fetchall()

            return [_row_to_dict(row) for row in results]

    def _row_to_dict(row):
        """Convierte una fila de la base de datos a diccionario"""
        pronostico = dict(row)
        pronostico['is_clear_favorite'] = bool(pronostico['is_clear_favorite'])
        pronostico['is_very_safe'] = bool(pronostico['is_very_safe'])
        pronostico['is_risky'] = bool(pronostico['is_risky'])
        return pronostico

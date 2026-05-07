from flask import Flask, render_template, jsonify, request
import requests
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import time
from database import init_db, save_pronostico, get_pronosticos, get_stats as get_db_stats, update_pronostico_status, get_finished_matches, mark_as_finished, get_active_matches

load_dotenv()

app = Flask(__name__)

# Configuración
ODDS_API_KEY = os.getenv('ODDS_API_KEY')
BASE_URL = 'https://api.the-odds-api.com/v4'
CACHE_DURATION = 43200  # 12 horas
CONFIDENCE_THRESHOLD_FAVORITE = 60
CONFIDENCE_THRESHOLD_VERY_SAFE = 75
CONFIDENCE_THRESHOLD_RISKY = 50

# Inicializar base de datos
init_db()

# Cache en memoria
cache = {'data': None, 'timestamp': 0, 'last_update': None}

# Ligas de fútbol
FOOTBALL_LEAGUES = [
    ('soccer_epl', 'Premier League'),
    ('soccer_spain_la_liga', 'La Liga'),
    ('soccer_italy_serie_a', 'Serie A'),
    ('soccer_germany_bundesliga', 'Bundesliga'),
    ('soccer_france_ligue_one', 'Ligue 1'),
    ('soccer_uefa_champs_league', 'Champions League'),
    ('soccer_argentina_primera_division', 'Liga Argentina')
]

SPORT_NAMES = {
    'football': 'Fútbol',
    'basketball': 'NBA'
}


def get_odds(sport_key, regions='us', markets='h2h'):
    """Obtiene las cuotas de la API"""
    url = f'{BASE_URL}/sports/{sport_key}/odds'
    params = {
        'api_key': ODDS_API_KEY,
        'regions': regions,
        'markets': markets,
        'oddsFormat': 'decimal'
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return []


def calculate_confidence(home_odds, draw_odds, away_odds):
    """Calcula el nivel de confianza basado en las cuotas"""
    home_prob = 1 / home_odds if home_odds else 0
    draw_prob = 1 / draw_odds if draw_odds else 0
    away_prob = 1 / away_odds if away_odds else 0

    max_prob = max(home_prob, draw_prob, away_prob)
    confidence = max_prob * 100

    if max_prob == home_prob:
        prediction = 'Local'
        prediction_team = 'home'
    elif max_prob == away_prob:
        prediction = 'Visitante'
        prediction_team = 'away'
    else:
        prediction = 'Empate'
        prediction_team = 'draw'

    return {
        'confidence': round(confidence, 1),
        'prediction': prediction,
        'prediction_team': prediction_team,
        'is_clear_favorite': confidence >= CONFIDENCE_THRESHOLD_FAVORITE,
        'is_very_safe': confidence >= CONFIDENCE_THRESHOLD_VERY_SAFE,
        'is_risky': confidence < CONFIDENCE_THRESHOLD_RISKY
    }


def parse_datetime(commence_time):
    """Parsea y formatea la fecha del partido"""
    try:
        dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
        now_utc = datetime.now(timezone.utc)
        return {
            'time': dt.strftime('%H:%M'),
            'date': dt.strftime('%d/%m'),
            'datetime': dt,
            'is_today': dt.date() == now_utc.date(),
            'is_tomorrow': dt.date() == (now_utc + timedelta(days=1)).date(),
            'days_until': (dt.date() - now_utc.date()).days
        }
    except:
        return {
            'time': '--:--',
            'date': '--/--',
            'datetime': None,
            'is_today': False,
            'is_tomorrow': False,
            'days_until': 999
        }


def analyze_match(match, sport_type, league_name=None):
    """Analiza un partido y extrae la información relevante"""
    bookmakers = match.get('bookmakers', [])
    if not bookmakers:
        return None

    first_bookmaker = bookmakers[0]
    markets = first_bookmaker.get('markets', [])
    if not markets:
        return None

    h2h_market = markets[0]
    outcomes = h2h_market.get('outcomes', [])

    home_team = match.get('home_team', '').lower()
    away_team = match.get('away_team', '').lower()

    home_odds = None
    draw_odds = None
    away_odds = None

    for outcome in outcomes:
        name = outcome.get('name', '').lower()
        price = outcome.get('price')

        if sport_type == 'basketball':
            if name == home_team or 'home' in name:
                home_odds = price
            elif name == away_team or 'away' in name:
                away_odds = price
        else:
            if name == home_team:
                home_odds = price
            elif name == away_team:
                away_odds = price
            elif 'draw' in name or 'empate' in name:
                draw_odds = price

    if not home_odds or not away_odds:
        return None

    confidence_data = calculate_confidence(home_odds, draw_odds, away_odds)
    date_info = parse_datetime(match.get('commence_time', ''))

    return {
        'id': match.get('id'),
        'home_team': match.get('home_team'),
        'away_team': match.get('away_team'),
        'sport': sport_type,
        'sport_name': SPORT_NAMES.get(sport_type, sport_type),
        'league': league_name,
        **date_info,
        'home_odds': round(home_odds, 2),
        'draw_odds': round(draw_odds, 2) if draw_odds else None,
        'away_odds': round(away_odds, 2),
        **confidence_data
    }


def get_all_matches():
    """Obtiene todos los partidos con cache"""
    current_time = time.time()

    if cache['data'] and (current_time - cache['timestamp']) < CACHE_DURATION:
        return cache['data']

    matches = []

    # Obtener partidos de fútbol
    for league_key, league_name in FOOTBALL_LEAGUES:
        try:
            league_matches = get_odds(league_key, regions='eu', markets='h2h')
            for match in league_matches:
                analyzed = analyze_match(match, 'football', league_name)
                if analyzed:
                    matches.append(analyzed)
                    save_pronostico(analyzed)
        except Exception as e:
            print(f"Error obteniendo {league_name}: {e}")

    # Obtener partidos de NBA
    try:
        nba_matches = get_odds('basketball_nba', regions='us', markets='h2h')
        for match in nba_matches:
            analyzed = analyze_match(match, 'basketball', 'NBA')
            if analyzed:
                matches.append(analyzed)
                save_pronostico(analyzed)
    except Exception as e:
        print(f"Error obteniendo NBA: {e}")

    # Ordenar por fecha
    matches.sort(key=lambda x: x['datetime'] if x['datetime'] else datetime.max)

    cache['data'] = matches
    cache['timestamp'] = current_time
    cache['last_update'] = datetime.now(timezone.utc)  # Guardar fecha de actualización

    return matches


def get_todays_matches():
    """Obtiene partidos de las últimas 24 horas desde la última actualización, excluyendo terminados"""
    all_matches = get_all_matches()
    now_utc = datetime.now(timezone.utc)

    if cache['last_update']:
        # Filtrar partidos de las últimas 24 horas desde la última actualización
        cutoff_time = cache['last_update'] - timedelta(hours=24)
        # Excluir partidos que ya terminaron (más de 3 horas después del inicio)
        return [
            m for m in all_matches
            if m['datetime'] and m['datetime'] >= cutoff_time and (m['datetime'] + timedelta(hours=3)) >= now_utc
        ]
    else:
        # Si no hay actualización registrada, mostrar todos los partidos no terminados
        return [m for m in all_matches if m['datetime'] and (m['datetime'] + timedelta(hours=3)) >= now_utc]


def check_finished_matches():
    """Verifica y marca partidos terminados"""
    finished = get_finished_matches()
    for match in finished:
        mark_as_finished(match['match_id'])
    return len(finished)


def get_combinada(matches):
    """Genera la combinada del día con los 3 pronósticos más seguros"""
    cutoff_time = cache['last_update'] - timedelta(hours=24) if cache['last_update'] else None

    today_favorites = [
        m for m in matches
        if m['is_clear_favorite'] and (not cutoff_time or m['datetime'] >= cutoff_time)
    ]

    today_favorites.sort(key=lambda x: x['confidence'], reverse=True)
    return today_favorites[:3]


def get_stats(matches):
    """Calcula estadísticas generales"""
    if not matches:
        return {
            'total': 0,
            'favorites': 0,
            'very_safe': 0,
            'risky': 0,
            'avg_confidence': 0,
            'today_count': 0,
            'tomorrow_count': 0
        }

    cutoff_time = cache['last_update'] - timedelta(hours=24) if cache['last_update'] else None

    total = len(matches)
    matches_in_window = [m for m in matches if not cutoff_time or m['datetime'] >= cutoff_time]

    return {
        'total': total,
        'favorites': sum(1 for m in matches_in_window if m['is_clear_favorite']),
        'very_safe': sum(1 for m in matches_in_window if m['is_very_safe']),
        'risky': sum(1 for m in matches_in_window if m['is_risky']),
        'avg_confidence': round(sum(m['confidence'] for m in matches_in_window) / len(matches_in_window), 1) if matches_in_window else 0,
        'today_count': sum(1 for m in matches_in_window if m['is_today']),
        'tomorrow_count': sum(1 for m in matches_in_window if m['is_tomorrow'])
    }


# Rutas
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/matches')
def api_matches():
    # Verificar partidos terminados antes de devolver los matches
    check_finished_matches()
    matches = get_todays_matches()
    stats = get_stats(matches)
    return jsonify({
        'matches': matches,
        'stats': stats,
        'total': len(matches)
    })


@app.route('/api/all-matches')
def api_all_matches():
    matches = get_all_matches()
    stats = get_stats(matches)
    return jsonify({
        'matches': matches,
        'stats': stats,
        'total': len(matches)
    })


@app.route('/api/combinada')
def api_combinada():
    matches = get_todays_matches()
    combinada = get_combinada(matches)
    return jsonify({
        'combinada': combinada,
        'total': len(combinada)
    })


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'API funcionando correctamente'})


@app.route('/historial')
def historial():
    return render_template('historial.html')


@app.route('/api/historial')
def api_historial():
    limit = int(request.args.get('limit', 50))
    status = request.args.get('status')
    pronosticos = get_pronosticos(limit=limit, status=status)
    stats = get_db_stats()
    return jsonify({
        'pronosticos': pronosticos,
        'stats': stats,
        'total': len(pronosticos)
    })


@app.route('/api/historial/stats')
def api_historial_stats():
    return jsonify(get_db_stats())


@app.route('/api/historial/<match_id>/update', methods=['POST'])
def update_pronostico(match_id):
    data = request.json
    update_pronostico_status(
        match_id,
        data.get('status'),
        data.get('result')
    )
    return jsonify({'status': 'ok'})


@app.route('/api/check-finished', methods=['POST'])
def check_finished():
    """Verifica y marca partidos terminados"""
    count = check_finished_matches()
    return jsonify({
        'status': 'ok',
        'finished_count': count
    })


if __name__ == '__main__':
    print("Iniciando servidor de pronosticos deportivos...")
    print("Abre http://localhost:5000 en tu navegador")
    app.run(debug=True, host='0.0.0.0', port=5000)

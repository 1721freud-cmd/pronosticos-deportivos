from flask import Flask, render_template, jsonify
import requests
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from functools import lru_cache
import time

load_dotenv()

app = Flask(__name__)

# Configuración de la API
ODDS_API_KEY = os.getenv('ODDS_API_KEY')
BASE_URL = 'https://api.the-odds-api.com/v4'

# Cache para evitar llamadas repetidas a la API
CACHE_DURATION = 7200  # 2 horas (7200 segundos) - para no exceder el límite de 500 requests/mes
cache = {'data': None, 'timestamp': 0}

def get_odds(sport_key, regions='us', markets='h2h'):
    """Obtiene las cuotas de una API para un deporte específico"""
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
    except requests.exceptions.RequestException as e:
        print(f"Error obteniendo cuotas: {e}")
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
        'is_clear_favorite': confidence >= 60,
        'is_very_safe': confidence >= 75,
        'is_risky': confidence < 50
    }

def analyze_match(match, sport_type):
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

    commence_time = match.get('commence_time', '')
    try:
        dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
        formatted_time = dt.strftime('%H:%M')
        formatted_date = dt.strftime('%d/%m')
        formatted_datetime = dt
        is_today = dt.date() == datetime.now(timezone.utc).date()
        is_tomorrow = dt.date() == (datetime.now(timezone.utc) + timedelta(days=1)).date()
        days_until = (dt.date() - datetime.now(timezone.utc).date()).days
    except:
        formatted_time = '--:--'
        formatted_date = '--/--'
        formatted_datetime = None
        is_today = False
        is_tomorrow = False
        days_until = 999

    return {
        'id': match.get('id'),
        'home_team': match.get('home_team'),
        'away_team': match.get('away_team'),
        'sport': sport_type,
        'sport_name': 'Fútbol' if sport_type == 'football' else 'NBA',
        'time': formatted_time,
        'date': formatted_date,
        'datetime': formatted_datetime,
        'is_today': is_today,
        'is_tomorrow': is_tomorrow,
        'days_until': days_until,
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

    # Fútbol - Premier League
    football_matches = get_odds('soccer_epl', regions='eu', markets='h2h')
    for match in football_matches:
        analyzed = analyze_match(match, 'football')
        if analyzed:
            matches.append(analyzed)

    # NBA
    nba_matches = get_odds('basketball_nba', regions='us', markets='h2h')
    for match in nba_matches:
        analyzed = analyze_match(match, 'basketball')
        if analyzed:
            matches.append(analyzed)

    # Ordenar por fecha
    matches.sort(key=lambda x: x['datetime'] if x['datetime'] else datetime.max)

    cache['data'] = matches
    cache['timestamp'] = current_time

    return matches

def get_todays_matches():
    """Obtiene solo partidos de hoy y mañana"""
    all_matches = get_all_matches()
    return [m for m in all_matches if m['days_until'] <= 1]

def get_combinada(matches):
    """Genera la combinada del día con los 3 pronósticos más seguros de hoy"""
    # Filtrar solo partidos de hoy y favoritos claros
    today_favorites = [m for m in matches if m['is_clear_favorite'] and m['days_until'] <= 1]

    # Ordenar por confianza descendente
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

    total = len(matches)
    favorites = len([m for m in matches if m['is_clear_favorite']])
    very_safe = len([m for m in matches if m['is_very_safe']])
    risky = len([m for m in matches if m['is_risky']])
    avg_confidence = round(sum(m['confidence'] for m in matches) / total, 1) if total > 0 else 0
    today_count = len([m for m in matches if m['is_today']])
    tomorrow_count = len([m for m in matches if m['is_tomorrow']])

    return {
        'total': total,
        'favorites': favorites,
        'very_safe': very_safe,
        'risky': risky,
        'avg_confidence': avg_confidence,
        'today_count': today_count,
        'tomorrow_count': tomorrow_count
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/matches')
def api_matches():
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

if __name__ == '__main__':
    print("Iniciando servidor de pronosticos deportivos...")
    print("Abre http://localhost:5000 en tu navegador")
    app.run(debug=True, host='0.0.0.0', port=5000)

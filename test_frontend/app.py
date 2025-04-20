from flask import Flask, render_template, jsonify, request
import requests

app = Flask(__name__)

# Configuration
BASE_API_URL = "http://localhost:8080"
CACHE_TIMEOUT = 300  # 5 minutes cache for hero data

hero_cache = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/player/<int:account_id>/stats')
def get_player_stats(account_id):
    try:
        match_count = request.args.get('count', default=50, type=int)
        
        matches_url = f"{BASE_API_URL}/players/{account_id}/matches?start=0&end={match_count}"
        matches_response = requests.get(matches_url)
        matches_response.raise_for_status()
        matches = matches_response.json()
        
        if not matches:
            return jsonify({"error": "No matches found"}), 404
        else:
            print(f"Matches found: {len(matches)}")
        
        hero_stats = {}

        for match in matches:
            hero_id = match['hero_id']
            
            if hero_id not in hero_stats:
                hero_stats[hero_id] = {
                    'matches': 0,
                    'wins': 0,
                    'kills': 0,
                    'deaths': 0,
                    'assists': 0,
                    'durations': 0
                }
            
            hero_stats[hero_id]['matches'] += 1
            hero_stats[hero_id]['wins'] += 1 if match['win'] else 0
            hero_stats[hero_id]['kills'] += match['kills']
            hero_stats[hero_id]['deaths'] += match['deaths']
            hero_stats[hero_id]['assists'] += match['assists']
            hero_stats[hero_id]['durations'] += match['duration']
        
        hero_data = []
        for hero_id, stats in hero_stats.items():
            hero_name = get_hero_name(hero_id)
            
            hero_data.append({
                'hero_id': hero_id,
                'name': hero_name,
                'matches': stats['matches'],
                'win_rate': (stats['wins'] / stats['matches']) * 100,
                'avg_kills': stats['kills'] / stats['matches'],
                'avg_deaths': stats['deaths'] / stats['matches'],
                'avg_assists': stats['assists'] / stats['matches'],
                'avg_duration': stats['durations'] / stats['matches']
            })
        
        hero_data.sort(key=lambda x: x['matches'], reverse=True)
        
        return jsonify({
            'account_id': account_id,
            'match_count': match_count,
            'heroes': hero_data
        })
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

def process_hero_name(hero_name):
    name = " ".join(list(map(lambda x: x.capitalize(), hero_name.split("_")[3:])))
    if name == "Vengefulspirit":
        return "Vengeful Spirit"
    return name

def get_hero_name(hero_id):
    """Get hero name from cache or API"""
    if hero_id in hero_cache:
        return hero_cache[hero_id]
    
    try:
        hero_url = f"{BASE_API_URL}/heroes/{hero_id}"
        hero_response = requests.get(hero_url)
        hero_response.raise_for_status()
        hero_data = hero_response.json()
        hero_name = process_hero_name(hero_data.get('name', f"Hero {hero_id}"))
        
        hero_cache[hero_id] = hero_name
        return hero_name
        
    except requests.exceptions.RequestException:
        return f"Hero {hero_id}"
    
@app.route('/api/hero/<int:hero_id>/winrate-by-level')
def get_hero_winrate_by_level(hero_id):
    try:
        winrate_url = f"{BASE_API_URL}/stats/{hero_id}/?rating_id=43&types=xp"
        winrate_response = requests.get(winrate_url)
        winrate_response.raise_for_status()
        winrate_data = winrate_response.json()
        
        processed_data = {
            "hero_id": hero_id,
            "hero_name": get_hero_name(hero_id),
            "levels": [],
            "winrates": []
        }
        
        for level in sorted(map(int, winrate_data.keys())):
            processed_data["levels"].append(level)
            processed_data["winrates"].append(winrate_data[str(level)] * 100)
        
        return jsonify(processed_data)
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/hero-stats')
def hero_stats():
    return render_template('hero_stats.html')

@app.route('/api/heroes')
def get_all_heroes():
    try:
        heroes_url = f"{BASE_API_URL}/heroes"
        heroes_response = requests.get(heroes_url)
        heroes_response.raise_for_status()
        heroes_data = heroes_response.json()
        
        processed_heroes = []
        for hero_data in heroes_data.get("heroes"):
            processed_heroes.append({
                "id": int(hero_data.get("id")),
                "name": process_hero_name(hero_data.get("name"))
            })
        
        return jsonify(processed_heroes)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/hero/<int:hero_id>/stats/<int:rating_id>/<string:stat_type>')
def get_hero_stats(hero_id, rating_id, stat_type):
    if stat_type not in ['xp', 'with', 'item']:
        return jsonify({"error": "Invalid stat type"}), 400
    
    try:
        stats_url = f"{BASE_API_URL}/stats/{hero_id}/?rating_id={rating_id}&types={stat_type}"
        stats_response = requests.get(stats_url)
        stats_response.raise_for_status()
        return jsonify(stats_response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
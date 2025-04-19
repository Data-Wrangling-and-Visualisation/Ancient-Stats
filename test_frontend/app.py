from flask import Flask, render_template, jsonify, request
import requests

app = Flask(__name__)

# Configuration
BASE_API_URL = "http://localhost:8080"  # Your Dota 2 API base URL
CACHE_TIMEOUT = 300  # 5 minutes cache for hero data

# In-memory cache for hero data (simple implementation)
hero_cache = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/player/<int:account_id>/stats')
def get_player_stats(account_id):
    try:
        match_count = request.args.get('count', default=50, type=int)
        
        # Fetch matches data from the Dota 2 API
        matches_url = f"{BASE_API_URL}/players/{account_id}/matches?start=0&end={match_count}"
        matches_response = requests.get(matches_url)
        matches_response.raise_for_status()
        matches = matches_response.json()
        
        if not matches:
            return jsonify({"error": "No matches found"}), 404
        else:
            print(f"Matches found: {len(matches)}")
        
        # Process matches data
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
        
        # Get hero names
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
        
        # Sort by most played heroes
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
        
        # Cache the hero name
        hero_cache[hero_id] = hero_name
        return hero_name
        
    except requests.exceptions.RequestException:
        return f"Hero {hero_id}"

if __name__ == '__main__':
    app.run(debug=True, port=5000)
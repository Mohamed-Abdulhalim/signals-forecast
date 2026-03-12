from flask import Flask, render_template, jsonify
import json
import os
from datetime import datetime
import glob

app = Flask(__name__)

def load_latest_signals():
    signal_files = glob.glob('data/signals/signals_*.json')
    if not signal_files:
        return {'signals': []}
    latest_file = max(signal_files)
    with open(latest_file, 'r') as f:
        return json.load(f)

def load_latest_forecasts():
    forecast_files = glob.glob('data/forecasts/forecasts_*.json')
    if not forecast_files:
        return {'forecasts': []}
    latest_file = max(forecast_files)
    with open(latest_file, 'r') as f:
        return json.load(f)

def load_latest_prices():
    categories = ['energy', 'safe_haven', 'food']
    all_prices = []
    for category in categories:
        files = glob.glob(f'data/prices/{category}_*.json')
        if files:
            latest_file = max(files)
            with open(latest_file, 'r') as f:
                data = json.load(f)
                all_prices.extend(data.get('assets', []))
    return all_prices

def load_price_history(asset_name, days=90):
    """Load historical prices for a specific asset across all files"""
    categories = ['energy', 'safe_haven', 'food']
    history = {}  # date -> price

    for category in categories:
        files = sorted(glob.glob(f'data/prices/{category}_*.json'))
        for filepath in files:
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                for asset in data.get('assets', []):
                    if asset.get('asset') == asset_name and asset.get('price'):
                        date = asset.get('date') or filepath.split('_')[-1].replace('.json','')
                        # Format date as YYYY-MM-DD
                        if len(date) == 8:
                            date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
                        history[date] = asset['price']
            except:
                continue

    # Sort by date and return last N days
    sorted_history = sorted(history.items())
    if days:
        sorted_history = sorted_history[-days:]
    return sorted_history

def load_track_record():
    try:
        with open('data/track_record.json', 'r') as f:
            return json.load(f)
    except:
        return {"predictions": [], "summary": {"total": 0, "open": 0, "hits": 0, "misses": 0, "average_accuracy": None}}

@app.route('/')
def home():
    signals = load_latest_signals()
    forecasts = load_latest_forecasts()
    return render_template('index.html',
                         signals=signals.get('signals', []),
                         forecasts=forecasts.get('forecasts', []))

@app.route('/signals')
def signals_page():
    signals = load_latest_signals()
    prices = load_latest_prices()
    return render_template('signals.html',
                         signals=signals.get('signals', []),
                         prices=prices)

@app.route('/forecasts')
def forecasts_page():
    forecasts = load_latest_forecasts()
    return render_template('forecasts.html',
                         forecasts=forecasts.get('forecasts', []))

@app.route('/methodology')
def methodology():
    return render_template('methodology.html')

@app.route('/track-record')
def track_record():
    record = load_track_record()
    return render_template('track_record.html',
                           predictions=record.get('predictions', []),
                           summary=record.get('summary', {}))

@app.route('/work-with-me')
def work_with_me():
    return render_template('work_with_me.html')

# ── API endpoints ──────────────────────────────────────────────

@app.route('/api/signals')
def api_signals():
    return jsonify(load_latest_signals())

@app.route('/api/forecasts')
def api_forecasts():
    return jsonify(load_latest_forecasts())

@app.route('/api/prices')
def api_prices():
    return jsonify({'prices': load_latest_prices()})

@app.route('/api/history/<asset_name>')
def api_history(asset_name):
    """Return price history for charting"""
    days = 90
    history = load_price_history(asset_name, days)
    return jsonify({
        'asset': asset_name,
        'history': [{'date': d, 'price': p} for d, p in history]
    })

@app.route('/api/chart-data')
def api_chart_data():
    """Return history + forecast for all assets in one call"""
    forecasts = load_latest_forecasts()
    assets = ['Brent Oil', 'Natural Gas', 'Gold', 'USD Index', 'Rice', 'Wheat', 'Corn']
    result = {}

    for asset in assets:
        history = load_price_history(asset, 90)
        if not history:
            continue

        # Find forecast for this asset
        forecast = next((f for f in forecasts.get('forecasts', []) if f['asset'] == asset), None)

        result[asset] = {
            'history': [{'date': d, 'price': p} for d, p in history],
            'forecast': {
                'target': forecast['forecast_30_days']['prediction'] if forecast else None,
                'lower': forecast['forecast_30_days']['lower_bound'] if forecast else None,
                'upper': forecast['forecast_30_days']['upper_bound'] if forecast else None,
                'date': forecast['forecast_date'] if forecast else None,
                'confidence': forecast['forecast_30_days']['confidence'] if forecast else None,
            } if forecast else None
        }

    return jsonify(result)

@app.route('/robots.txt')
def robots():
    with open('robots.txt', 'r') as f:
        content = f.read()
    return content, 200, {'Content-Type': 'text/plain'}

@app.route('/sitemap.xml')
def sitemap():
    with open('sitemap.xml', 'r') as f:
        content = f.read()
    return content, 200, {'Content-Type': 'application/xml'}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

from flask import Flask, render_template, jsonify
import json
import os
from datetime import datetime
import glob

app = Flask(__name__)

def load_latest_signals():
    """Load the most recent signals data"""
    signal_files = glob.glob('data/signals/signals_*.json')
    
    if not signal_files:
        return {'signals': []}
    
    latest_file = max(signal_files)
    
    with open(latest_file, 'r') as f:
        return json.load(f)

def load_latest_forecasts():
    """Load the most recent forecasts"""
    forecast_files = glob.glob('data/forecasts/forecasts_*.json')
    
    if not forecast_files:
        return {'forecasts': []}
    
    latest_file = max(forecast_files)
    
    with open(latest_file, 'r') as f:
        return json.load(f)

def load_latest_prices():
    """Load latest prices across all categories"""
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

@app.route('/')
def home():
    """Homepage with current signals"""
    signals = load_latest_signals()
    forecasts = load_latest_forecasts()
    
    return render_template('index.html', 
                         signals=signals.get('signals', []),
                         forecasts=forecasts.get('forecasts', []))

@app.route('/signals')
def signals_page():
    """Signals page with detailed indicators"""
    signals = load_latest_signals()
    prices = load_latest_prices()
    
    return render_template('signals.html',
                         signals=signals.get('signals', []),
                         prices=prices)

@app.route('/forecasts')
def forecasts_page():
    """Forecast page with predictions"""
    forecasts = load_latest_forecasts()
    
    return render_template('forecasts.html',
                         forecasts=forecasts.get('forecasts', []))

@app.route('/methodology')
def methodology():
    """Methodology explanation page"""
    return render_template('methodology.html')

@app.route('/track-record')
def track_record():
    """Track record page"""
    return render_template('track_record.html')

@app.route('/work-with-me')
def work_with_me():
    """Contact/services page"""
    return render_template('work_with_me.html')

# API endpoints
@app.route('/api/signals')
def api_signals():
    """API endpoint for signals data"""
    return jsonify(load_latest_signals())

@app.route('/api/forecasts')
def api_forecasts():
    """API endpoint for forecasts data"""
    return jsonify(load_latest_forecasts())

@app.route('/api/prices')
def api_prices():
    """API endpoint for current prices"""
    return jsonify({'prices': load_latest_prices()})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

import json
import os
from datetime import datetime, timedelta
import numpy as np
from scipy import stats

class ForecastEngine:
    def __init__(self):
        self.data_dir     = 'data/prices'
        self.forecast_dir = 'data/forecasts'
        os.makedirs(self.forecast_dir, exist_ok=True)

    def load_price_history(self, category, asset_name, days=60):
        prices, dates = [], []
        for i in range(days):
            date     = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
            filename = f"{self.data_dir}/{category}_{date}.json"
            if os.path.exists(filename):
                with open(filename) as f:
                    data = json.load(f)
                for asset in data.get('assets', []):
                    if asset['asset'] == asset_name:
                        prices.append(asset['price'])
                        dates.append(date)
                        break
        return list(reversed(prices)), list(reversed(dates))

    def price_floor(self, asset_name):
        floors = {
            'Natural Gas': 1.0,
            'Brent Oil':   20.0,
            'Gold':        800.0,
            'USD Index':   85.0,
            'Wheat':       200.0,
            'Corn':        200.0,
            'Rice':        5.0,
        }
        return floors.get(asset_name, 0.01)

    def max_change_pct(self, days_ahead):
        """
        Cap how far a forecast can move from current price.
        30 days  → max ±35%
        90 days  → max ±60%
        Prevents runaway linear extrapolation.
        """
        return 0.35 + (days_ahead - 30) / 90 * 0.25

    def linear_forecast(self, prices, days_ahead, asset_name=''):
        if len(prices) < 10:
            return None

        recent = prices[-30:]
        x      = np.arange(len(recent))

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, recent)

        future_x   = len(recent) + days_ahead
        prediction = intercept + slope * future_x

        residuals    = np.array(recent) - (intercept + slope * x)
        std_residual = np.std(residuals)
        horizon_factor = np.sqrt(days_ahead / 30)
        margin = 1.96 * std_residual * horizon_factor

        current_price = prices[-1]
        floor         = self.price_floor(asset_name)
        max_chg       = self.max_change_pct(days_ahead)

        # Cap prediction within ±max_change of current price
        max_price = current_price * (1 + max_chg)
        min_price = max(current_price * (1 - max_chg), floor)
        prediction = max(min(prediction, max_price), min_price)

        lower_bound = max(prediction - margin, floor)
        upper_bound = min(prediction + margin, max_price * 1.1)

        return {
            'prediction':  round(prediction,  2),
            'lower_bound': round(lower_bound, 2),
            'upper_bound': round(upper_bound, 2),
            'confidence':  'high' if r_value**2 > 0.7 else 'medium' if r_value**2 > 0.4 else 'low'
        }

    def generate_forecast(self, asset_name, category, prices):
        if len(prices) < 14:
            return {'asset': asset_name, 'error': 'Insufficient historical data'}

        current_price = prices[-1]
        forecast_30   = self.linear_forecast(prices, 30, asset_name)
        forecast_90   = self.linear_forecast(prices, 90, asset_name)

        recent_avg = np.mean(prices[-7:])
        older_avg  = np.mean(prices[-14:-7])
        momentum   = (recent_avg - older_avg) / older_avg if older_avg != 0 else 0

        return {
            'asset':            asset_name,
            'category':         category,
            'current_price':    current_price,
            'forecast_30_days': forecast_30,
            'forecast_90_days': forecast_90,
            'momentum':         round(momentum, 4),
            'trend':            'up' if momentum > 0.02 else 'down' if momentum < -0.02 else 'neutral',
            'methodology':      'Linear regression with volatility bands',
            'timestamp':        datetime.now().isoformat(),
            'forecast_date':    (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        }

    def generate_all_forecasts(self):
        assets = [
            ('energy',     'Brent Oil'),
            ('energy',     'Natural Gas'),
            ('safe_haven', 'Gold'),
            ('safe_haven', 'USD Index'),
            ('food',       'Wheat'),
            ('food',       'Corn'),
            ('food',       'Rice'),
        ]
        forecasts = {'timestamp': datetime.now().isoformat(), 'forecasts': []}

        for category, asset_name in assets:
            prices, dates = self.load_price_history(category, asset_name, days=60)
            if prices:
                forecast = self.generate_forecast(asset_name, category, prices)
                forecasts['forecasts'].append(forecast)

        filename = f"{self.forecast_dir}/forecasts_{datetime.now().strftime('%Y%m%d')}.json"
        with open(filename, 'w') as f:
            json.dump(forecasts, f, indent=2)

        return forecasts

if __name__ == '__main__':
    engine    = ForecastEngine()
    forecasts = engine.generate_all_forecasts()
    print(json.dumps(forecasts, indent=2))

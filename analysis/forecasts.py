import json
import os
from datetime import datetime, timedelta
import numpy as np
from scipy import stats

class ForecastEngine:
    def __init__(self):
        self.data_dir = 'data/prices'
        self.forecast_dir = 'data/forecasts'
        os.makedirs(self.forecast_dir, exist_ok=True)
    
    def load_price_history(self, category, asset_name, days=60):
        """Load historical prices for an asset"""
        prices = []
        dates = []
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
            filename = f"{self.data_dir}/{category}_{date}.json"
            
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    data = json.load(f)
                    
                    for asset in data.get('assets', []):
                        if asset['asset'] == asset_name:
                            prices.append(asset['price'])
                            dates.append(date)
                            break
        
        # Reverse to chronological order
        prices = list(reversed(prices))
        dates = list(reversed(dates))
        
        return prices, dates
    
    def linear_forecast(self, prices, days_ahead):
        """Simple linear regression forecast"""
        if len(prices) < 10:
            return None
        
        # Use last 30 days for trend
        recent_prices = prices[-30:]
        x = np.arange(len(recent_prices))
        
        # Linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, recent_prices)
        
        # Predict future
        future_x = len(recent_prices) + days_ahead
        prediction = intercept + slope * future_x
        
        # Calculate confidence interval
        residuals = recent_prices - (intercept + slope * x)
        std_residual = np.std(residuals)
        
        # 95% confidence interval
        margin = 1.96 * std_residual
        
        return {
            'prediction': round(prediction, 2),
            'lower_bound': round(prediction - margin, 2),
            'upper_bound': round(prediction + margin, 2),
            'confidence': 'high' if r_value**2 > 0.7 else 'medium' if r_value**2 > 0.4 else 'low'
        }
    
    def volatility_adjusted_forecast(self, prices, days_ahead):
        """Forecast considering volatility bands"""
        if len(prices) < 20:
            return None
        
        recent = prices[-20:]
        mean_price = np.mean(recent)
        std_dev = np.std(recent)
        
        # Simple drift estimate
        drift = (recent[-1] - recent[0]) / len(recent)
        
        # Project forward
        prediction = recent[-1] + (drift * days_ahead)
        
        # Volatility expands with time
        volatility_factor = np.sqrt(days_ahead / 30)
        margin = std_dev * volatility_factor * 1.5
        
        return {
            'prediction': round(prediction, 2),
            'lower_bound': round(prediction - margin, 2),
            'upper_bound': round(prediction + margin, 2),
            'volatility': round(std_dev, 2)
        }
    
    def generate_forecast(self, asset_name, category, prices):
        """Generate comprehensive forecast"""
        if len(prices) < 14:
            return {
                'asset': asset_name,
                'error': 'Insufficient historical data'
            }
        
        current_price = prices[-1]
        
        # 30-day forecast
        forecast_30 = self.linear_forecast(prices, 30)
        vol_30 = self.volatility_adjusted_forecast(prices, 30)
        
        # 90-day forecast
        forecast_90 = self.linear_forecast(prices, 90)
        vol_90 = self.volatility_adjusted_forecast(prices, 90)
        
        # Calculate momentum
        recent_avg = np.mean(prices[-7:])
        older_avg = np.mean(prices[-14:-7])
        momentum = (recent_avg - older_avg) / older_avg if older_avg != 0 else 0
        
        return {
            'asset': asset_name,
            'category': category,
            'current_price': current_price,
            'forecast_30_days': forecast_30,
            'forecast_90_days': forecast_90,
            'momentum': round(momentum, 4),
            'trend': 'up' if momentum > 0.02 else 'down' if momentum < -0.02 else 'neutral',
            'methodology': 'Linear regression with volatility bands',
            'timestamp': datetime.now().isoformat(),
            'forecast_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        }
    
    def generate_all_forecasts(self):
        """Generate forecasts for all assets"""
        assets = [
            ('energy', 'Brent Oil'),
            ('energy', 'Natural Gas'),
            ('safe_haven', 'Gold'),
            ('safe_haven', 'USD Index'),
            ('food', 'Wheat'),
            ('food', 'Corn'),
            ('food', 'Rice')
        ]
        
        forecasts = {
            'timestamp': datetime.now().isoformat(),
            'forecasts': []
        }
        
        for category, asset_name in assets:
            prices, dates = self.load_price_history(category, asset_name, days=60)
            
            if prices:
                forecast = self.generate_forecast(asset_name, category, prices)
                forecasts['forecasts'].append(forecast)
        
        # Save forecasts
        filename = f"{self.forecast_dir}/forecasts_{datetime.now().strftime('%Y%m%d')}.json"
        with open(filename, 'w') as f:
            json.dump(forecasts, f, indent=2)
        
        return forecasts

if __name__ == '__main__':
    engine = ForecastEngine()
    forecasts = engine.generate_all_forecasts()
    print(json.dumps(forecasts, indent=2))

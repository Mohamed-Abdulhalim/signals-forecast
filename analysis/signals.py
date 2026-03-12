import json
import os
from datetime import datetime, timedelta
import numpy as np

class SignalGenerator:
    def __init__(self):
        self.data_dir = 'data/prices'
        self.signal_dir = 'data/signals'
        os.makedirs(self.signal_dir, exist_ok=True)
    
    def load_historical_data(self, category, days=30):
        """Load past price data for analysis"""
        prices = []
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
            filename = f"{self.data_dir}/{category}_{date}.json"
            
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    prices.append(json.load(f))
        
        return prices
    
    def calculate_momentum(self, prices):
        """Calculate price momentum score"""
        if len(prices) < 2:
            return 0.5
        
        recent = prices[-7:]  # Last 7 days
        older = prices[-14:-7]  # Previous 7 days
        
        if not recent or not older:
            return 0.5
        
        recent_avg = np.mean(recent)
        older_avg = np.mean(older)
        
        if older_avg == 0:
            return 0.5
        
        change = (recent_avg - older_avg) / older_avg
        
        # Normalize to 0-1 scale
        momentum = 0.5 + (change * 5)  # 10% change = 0.5 momentum shift
        return max(0, min(1, momentum))
    
    def calculate_volatility(self, prices):
        """Calculate price volatility level"""
        if len(prices) < 7:
            return 'Unknown'
        
        std_dev = np.std(prices[-14:])
        mean = np.mean(prices[-14:])
        
        if mean == 0:
            return 'Unknown'
        
        cv = std_dev / mean  # Coefficient of variation
        
        if cv < 0.02:
            return 'Low'
        elif cv < 0.05:
            return 'Moderate'
        else:
            return 'High'
    
    def generate_signal(self, asset_name, prices):
        """Generate bullish/neutral/bearish signal"""
        if len(prices) < 7:
            return {
                'asset': asset_name,
                'signal': 'neutral',
                'confidence': 'low',
                'reason': 'Insufficient data'
            }
        
        # Calculate momentum
        momentum = self.calculate_momentum(prices)
        
        # Calculate trend (simple moving average)
        sma_short = np.mean(prices[-7:])
        sma_long = np.mean(prices[-14:])
        
        # Determine signal
        if momentum > 0.6 and sma_short > sma_long:
            signal = 'bullish'
            confidence = 'high' if momentum > 0.7 else 'medium'
        elif momentum < 0.4 and sma_short < sma_long:
            signal = 'bearish'
            confidence = 'high' if momentum < 0.3 else 'medium'
        else:
            signal = 'neutral'
            confidence = 'medium'
        
        volatility = self.calculate_volatility(prices)
        
        return {
            'asset': asset_name,
            'signal': signal,
            'confidence': confidence,
            'momentum': round(momentum, 2),
            'volatility': volatility,
            'current_price': prices[-1] if prices else None,
            'timestamp': datetime.now().isoformat()
        }
    
    def process_category_data(self, historical_data):
        """Process historical data to extract price arrays per asset"""
        asset_prices = {}
        
        for day_data in historical_data:
            for asset in day_data.get('assets', []):
                asset_name = asset['asset']
                price = asset['price']
                
                if asset_name not in asset_prices:
                    asset_prices[asset_name] = []
                
                asset_prices[asset_name].append(price)
        
        # Reverse to get chronological order
        for asset in asset_prices:
            asset_prices[asset] = list(reversed(asset_prices[asset]))
        
        return asset_prices
    
    def generate_all_signals(self):
        """Generate signals for all assets"""
        categories = ['energy', 'safe_haven', 'food']
        all_signals = {
            'timestamp': datetime.now().isoformat(),
            'signals': []
        }
        
        for category in categories:
            historical = self.load_historical_data(category, days=30)
            
            if not historical:
                continue
            
            asset_prices = self.process_category_data(historical)
            
            for asset_name, prices in asset_prices.items():
                signal = self.generate_signal(asset_name, prices)
                signal['category'] = category
                all_signals['signals'].append(signal)
        
        # Save signals
        filename = f"{self.signal_dir}/signals_{datetime.now().strftime('%Y%m%d')}.json"
        with open(filename, 'w') as f:
            json.dump(all_signals, f, indent=2)
        
        return all_signals

if __name__ == '__main__':
    generator = SignalGenerator()
    signals = generator.generate_all_signals()
    print(json.dumps(signals, indent=2))

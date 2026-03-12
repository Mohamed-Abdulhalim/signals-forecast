import requests
import json
from datetime import datetime
import os

class FoodCollector:
    def __init__(self):
        self.data_dir = 'data/prices'
        os.makedirs(self.data_dir, exist_ok=True)
    
    def get_commodity_price(self, symbol, name):
        """Generic commodity price fetcher using Yahoo Finance"""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1d')
            
            if not hist.empty:
                return {
                    'asset': name,
                    'symbol': symbol,
                    'price': round(hist['Close'].iloc[-1], 2),
                    'currency': 'USD',
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            print(f"Error fetching {name}: {e}")
            return None
    
    def get_wheat(self):
        """Get wheat futures price"""
        # ZW=F is Chicago wheat futures
        return self.get_commodity_price('ZW=F', 'Wheat')
    
    def get_corn(self):
        """Get corn futures price"""
        # ZC=F is Chicago corn futures
        return self.get_commodity_price('ZC=F', 'Corn')
    
    def get_rice(self):
        """Get rough rice futures price"""
        # ZR=F is rough rice futures
        return self.get_commodity_price('ZR=F', 'Rice')
    
    def collect_all(self):
        """Collect all food commodity data"""
        results = {
            'category': 'food',
            'timestamp': datetime.now().isoformat(),
            'assets': []
        }
        
        wheat = self.get_wheat()
        if wheat:
            results['assets'].append(wheat)
        
        corn = self.get_corn()
        if corn:
            results['assets'].append(corn)
        
        rice = self.get_rice()
        if rice:
            results['assets'].append(rice)
        
        # Save to file
        filename = f"{self.data_dir}/food_{datetime.now().strftime('%Y%m%d')}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        return results

if __name__ == '__main__':
    collector = FoodCollector()
    data = collector.collect_all()
    print(json.dumps(data, indent=2))

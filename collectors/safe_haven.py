import requests
import json
from datetime import datetime
import os

class SafeHavenCollector:
    def __init__(self):
        self.data_dir = 'data/prices'
        os.makedirs(self.data_dir, exist_ok=True)
    
    def get_gold_price(self):
        """Get gold price from public API"""
        try:
            # Using metals-api.com free tier or similar
            # Alternative: scrape from reliable sources
            url = 'https://api.metals.live/v1/spot/gold'
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'asset': 'Gold',
                    'symbol': 'XAU',
                    'price': float(data[0]['price']),
                    'currency': 'USD',
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            print(f"Error fetching gold: {e}")
            
            # Fallback: use Yahoo Finance
            try:
                import yfinance as yf
                gold = yf.Ticker('GC=F')
                hist = gold.history(period='1d')
                
                if not hist.empty:
                    return {
                        'asset': 'Gold',
                        'symbol': 'XAU',
                        'price': round(hist['Close'].iloc[-1], 2),
                        'currency': 'USD',
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'timestamp': datetime.now().isoformat()
                    }
            except:
                pass
            
            return None
    
    def get_usd_index(self):
        """Get US Dollar Index (DXY)"""
        try:
            import yfinance as yf
            dxy = yf.Ticker('DX-Y.NYB')
            hist = dxy.history(period='1d')
            
            if not hist.empty:
                return {
                    'asset': 'USD Index',
                    'symbol': 'DXY',
                    'price': round(hist['Close'].iloc[-1], 2),
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            print(f"Error fetching DXY: {e}")
            return None
    
    def collect_all(self):
        """Collect all safe haven data"""
        results = {
            'category': 'safe_haven',
            'timestamp': datetime.now().isoformat(),
            'assets': []
        }
        
        gold = self.get_gold_price()
        if gold:
            results['assets'].append(gold)
        
        usd = self.get_usd_index()
        if usd:
            results['assets'].append(usd)
        
        # Save to file
        filename = f"{self.data_dir}/safe_haven_{datetime.now().strftime('%Y%m%d')}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        return results

if __name__ == '__main__':
    collector = SafeHavenCollector()
    data = collector.collect_all()
    print(json.dumps(data, indent=2))

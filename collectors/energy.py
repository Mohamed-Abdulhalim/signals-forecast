import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class EnergyCollector:
    def __init__(self):
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_KEY')
        self.data_dir = 'data/prices'
        os.makedirs(self.data_dir, exist_ok=True)
    
    def get_brent_oil(self):
        """Get Brent Crude Oil prices"""
        url = f'https://www.alphavantage.co/query'
        params = {
            'function': 'BRENT',
            'interval': 'daily',
            'apikey': self.alpha_vantage_key
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'data' in data:
                latest = data['data'][0]
                return {
                    'asset': 'Brent Oil',
                    'symbol': 'BRENT',
                    'price': float(latest['value']),
                    'date': latest['date'],
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            print(f"Error fetching Brent oil: {e}")
            return None
    
    def get_natural_gas(self):
        """Get Natural Gas prices"""
        url = f'https://www.alphavantage.co/query'
        params = {
            'function': 'NATURAL_GAS',
            'interval': 'daily',
            'apikey': self.alpha_vantage_key
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'data' in data:
                latest = data['data'][0]
                return {
                    'asset': 'Natural Gas',
                    'symbol': 'NATGAS',
                    'price': float(latest['value']),
                    'date': latest['date'],
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            print(f"Error fetching natural gas: {e}")
            return None
    
    def collect_all(self):
        """Collect all energy data"""
        results = {
            'category': 'energy',
            'timestamp': datetime.now().isoformat(),
            'assets': []
        }
        
        oil = self.get_brent_oil()
        if oil:
            results['assets'].append(oil)
        
        gas = self.get_natural_gas()
        if gas:
            results['assets'].append(gas)
        
        # Save to file
        filename = f"{self.data_dir}/energy_{datetime.now().strftime('%Y%m%d')}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        return results

if __name__ == '__main__':
    collector = EnergyCollector()
    data = collector.collect_all()
    print(json.dumps(data, indent=2))

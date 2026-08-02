import requests
import json
from datetime import datetime
import os


class EnergyCollector:
    def __init__(self):
        self.alpha_vantage_key = os.environ.get('ALPHA_VANTAGE_KEY', '')
        self.data_dir = 'data/prices'
        os.makedirs(self.data_dir, exist_ok=True)

    # ── BRENT OIL ───────────────────────────────────────────────

    def _brent_from_yfinance(self):
        try:
            import yfinance as yf
            hist = yf.Ticker('BZ=F').history(period='2d')
            if not hist.empty:
                price = round(float(hist['Close'].iloc[-1]), 2)
                if 20 < price < 200:
                    print(f"    [OK] Brent Oil via yfinance BZ=F: ${price}")
                    return price
                print(f"    [WARN] yfinance BZ=F price {price} outside sane range")
        except Exception as e:
            print(f"    [WARN] yfinance BZ=F failed: {e}")
        return None

    def _brent_from_alpha_vantage(self):
        if not self.alpha_vantage_key:
            print("    [WARN] No ALPHA_VANTAGE_KEY set, skipping AV Brent")
            return None
        try:
            url = 'https://www.alphavantage.co/query'
            params = {
                'function': 'BRENT',
                'interval': 'daily',
                'apikey': self.alpha_vantage_key
            }
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            if 'data' in data and data['data']:
                latest = data['data'][0]
                price = round(float(latest['value']), 2)
                if 20 < price < 200:
                    print(f"    [OK] Brent Oil via Alpha Vantage: ${price}")
                    return price
                print(f"    [WARN] AV Brent price {price} outside sane range")
        except Exception as e:
            print(f"    [WARN] Alpha Vantage Brent failed: {e}")
        return None

    def get_brent_oil(self):
        """Try yfinance first (no quota cost), fall back to Alpha Vantage."""
        print("  [BRENT] Trying 2 sources...")
        price = self._brent_from_yfinance() or self._brent_from_alpha_vantage()
        if price is None:
            print("  [FAIL] All Brent Oil sources failed — skipping today")
            return None
        return {
            'asset': 'Brent Oil',
            'symbol': 'BRENT',
            'price': price,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat()
        }

    # ── NATURAL GAS ─────────────────────────────────────────────

    def _natgas_from_yfinance(self):
        try:
            import yfinance as yf
            hist = yf.Ticker('NG=F').history(period='2d')
            if not hist.empty:
                price = round(float(hist['Close'].iloc[-1]), 2)
                if 0.5 < price < 20:
                    print(f"    [OK] Natural Gas via yfinance NG=F: ${price}")
                    return price
                print(f"    [WARN] yfinance NG=F price {price} outside sane range")
        except Exception as e:
            print(f"    [WARN] yfinance NG=F failed: {e}")
        return None

    def _natgas_from_alpha_vantage(self):
        if not self.alpha_vantage_key:
            print("    [WARN] No ALPHA_VANTAGE_KEY set, skipping AV Natural Gas")
            return None
        try:
            url = 'https://www.alphavantage.co/query'
            params = {
                'function': 'NATURAL_GAS',
                'interval': 'daily',
                'apikey': self.alpha_vantage_key
            }
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            if 'data' in data and data['data']:
                latest = data['data'][0]
                price = round(float(latest['value']), 2)
                if 0.5 < price < 20:
                    print(f"    [OK] Natural Gas via Alpha Vantage: ${price}")
                    return price
                print(f"    [WARN] AV Natural Gas price {price} outside sane range")
        except Exception as e:
            print(f"    [WARN] Alpha Vantage Natural Gas failed: {e}")
        return None

    def get_natural_gas(self):
        """Try yfinance first (no quota cost), fall back to Alpha Vantage."""
        print("  [NATGAS] Trying 2 sources...")
        price = self._natgas_from_yfinance() or self._natgas_from_alpha_vantage()
        if price is None:
            print("  [FAIL] All Natural Gas sources failed — skipping today")
            return None
        return {
            'asset': 'Natural Gas',
            'symbol': 'NATGAS',
            'price': price,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat()
        }

    # ── COLLECT ALL ─────────────────────────────────────────────

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

        if not results['assets']:
            print("  [WARN] No energy data collected today")
            return results

        filename = f"{self.data_dir}/energy_{datetime.now().strftime('%Y%m%d')}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"  [SAVED] {filename}")
        return results


if __name__ == '__main__':
    collector = EnergyCollector()
    data = collector.collect_all()
    print(json.dumps(data, indent=2))

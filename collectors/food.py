import requests
import json
from datetime import datetime
import os
import time


class FoodCollector:
    def __init__(self):
        self.data_dir = 'data/prices'
        os.makedirs(self.data_dir, exist_ok=True)
        self.alpha_vantage_key = os.environ.get('ALPHA_VANTAGE_KEY', '')

    # ── WHEAT ───────────────────────────────────────────────────

    def _wheat_from_yfinance(self):
        try:
            import yfinance as yf
            hist = yf.Ticker('ZW=F').history(period='2d')
            if not hist.empty:
                price = round(float(hist['Close'].iloc[-1]), 2)
                if 100 < price < 2000:
                    print(f"    [OK] Wheat via yfinance ZW=F: ${price}")
                    return price
                print(f"    [WARN] yfinance ZW=F price {price} outside sane range")
        except Exception as e:
            print(f"    [WARN] yfinance ZW=F failed: {e}")
        return None

    def _wheat_from_alpha_vantage(self):
        if not self.alpha_vantage_key:
            print("    [WARN] No ALPHA_VANTAGE_KEY set, skipping AV wheat")
            return None
        try:
            url = (
                'https://www.alphavantage.co/query'
                '?function=WHEAT&interval=daily'
                f'&apikey={self.alpha_vantage_key}'
            )
            r = requests.get(url, timeout=15)
            data = r.json()
            if 'data' in data and data['data']:
                latest = data['data'][0]
                price = round(float(latest['value']), 2)
                if 100 < price < 2000:
                    print(f"    [OK] Wheat via Alpha Vantage: ${price}")
                    return price
                print(f"    [WARN] AV wheat price {price} outside sane range")
            else:
                print(f"    [WARN] AV wheat unexpected response: {data}")
        except Exception as e:
            print(f"    [WARN] Alpha Vantage wheat failed: {e}")
        return None

    def get_wheat(self):
        print("  [WHEAT] Trying 2 sources...")
        price = self._wheat_from_alpha_vantage() or self._wheat_from_yfinance()
        if price is None:
            print("  [FAIL] All wheat sources failed — skipping Wheat today")
            return None
        return {
            'asset': 'Wheat',
            'symbol': 'ZW=F',
            'price': price,
            'currency': 'USD',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat()
        }

    # ── CORN ────────────────────────────────────────────────────

    def _corn_from_yfinance(self):
        try:
            import yfinance as yf
            hist = yf.Ticker('ZC=F').history(period='2d')
            if not hist.empty:
                price = round(float(hist['Close'].iloc[-1]), 2)
                if 100 < price < 2000:
                    print(f"    [OK] Corn via yfinance ZC=F: ${price}")
                    return price
                print(f"    [WARN] yfinance ZC=F price {price} outside sane range")
        except Exception as e:
            print(f"    [WARN] yfinance ZC=F failed: {e}")
        return None

    def _corn_from_alpha_vantage(self):
        if not self.alpha_vantage_key:
            print("    [WARN] No ALPHA_VANTAGE_KEY set, skipping AV corn")
            return None
        try:
            url = (
                'https://www.alphavantage.co/query'
                '?function=CORN&interval=daily'
                f'&apikey={self.alpha_vantage_key}'
            )
            r = requests.get(url, timeout=15)
            data = r.json()
            if 'data' in data and data['data']:
                latest = data['data'][0]
                price = round(float(latest['value']), 2)
                if 100 < price < 2000:
                    print(f"    [OK] Corn via Alpha Vantage: ${price}")
                    return price
                print(f"    [WARN] AV corn price {price} outside sane range")
            else:
                print(f"    [WARN] AV corn unexpected response: {data}")
        except Exception as e:
            print(f"    [WARN] Alpha Vantage corn failed: {e}")
        return None

    def get_corn(self):
        print("  [CORN] Trying 2 sources...")
        price = self._corn_from_alpha_vantage() or self._corn_from_yfinance()
        if price is None:
            print("  [FAIL] All corn sources failed — skipping Corn today")
            return None
        return {
            'asset': 'Corn',
            'symbol': 'ZC=F',
            'price': price,
            'currency': 'USD',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat()
        }

    # ── RICE ────────────────────────────────────────────────────

    def _rice_from_yfinance(self):
        try:
            import yfinance as yf
            hist = yf.Ticker('ZR=F').history(period='2d')
            if not hist.empty:
                price = round(float(hist['Close'].iloc[-1]), 2)
                if 5 < price < 200:
                    print(f"    [OK] Rice via yfinance ZR=F: ${price}")
                    return price
                print(f"    [WARN] yfinance ZR=F price {price} outside sane range")
        except Exception as e:
            print(f"    [WARN] yfinance ZR=F failed: {e}")
        return None

    def _rice_from_pdba(self):
        try:
            import yfinance as yf
            hist = yf.Ticker('PDBA').history(period='2d')
            if not hist.empty:
                price = round(float(hist['Close'].iloc[-1]), 2)
                if 5 < price < 200:
                    print(f"    [OK] Rice via yfinance PDBA: ${price}")
                    return price
                print(f"    [WARN] yfinance PDBA price {price} outside sane range")
        except Exception as e:
            print(f"    [WARN] yfinance PDBA failed: {e}")
        return None

    def _rice_from_alpha_vantage(self):
        if not self.alpha_vantage_key:
            print("    [WARN] No ALPHA_VANTAGE_KEY set, skipping AV rice")
            return None
        try:
            url = (
                'https://www.alphavantage.co/query'
                '?function=TIME_SERIES_DAILY&symbol=PDBA'
                f'&apikey={self.alpha_vantage_key}'
            )
            r = requests.get(url, timeout=15)
            series = r.json().get('Time Series (Daily)', {})
            if series:
                latest_date = sorted(series.keys())[-1]
                price = round(float(series[latest_date]['4. close']), 2)
                if 5 < price < 200:
                    print(f"    [OK] Rice via Alpha Vantage PDBA: ${price}")
                    return price
                print(f"    [WARN] AV rice price {price} outside sane range")
            else:
                print(f"    [WARN] AV rice unexpected response: {r.json()}")
        except Exception as e:
            print(f"    [WARN] Alpha Vantage rice failed: {e}")
        return None

    def get_rice(self):
        print("  [RICE] Trying 3 sources...")
        price = (
            self._rice_from_yfinance() or
            self._rice_from_alpha_vantage() or
            self._rice_from_pdba()
        )
        if price is None:
            print("  [FAIL] All rice sources failed — skipping Rice today")
            return None
        return {
            'asset': 'Rice',
            'symbol': 'PDBA',
            'price': price,
            'currency': 'USD',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat()
        }

    # ── COLLECT ALL ─────────────────────────────────────────────

    def collect_all(self):
        results = {
            'category': 'food',
            'timestamp': datetime.now().isoformat(),
            'assets': []
        }

        time.sleep(10)  # let any AV rate-limit window from the prior step clear

        wheat = self.get_wheat()
        if wheat:
            results['assets'].append(wheat)

        time.sleep(15)  # respect Alpha Vantage's 1 request/second limit

        corn = self.get_corn()
        if corn:
            results['assets'].append(corn)

        time.sleep(15)  # respect Alpha Vantage's 1 request/second limit

        rice = self.get_rice()
        if rice:
            results['assets'].append(rice)

        if not results['assets']:
            print("  [WARN] No food data collected today")
            return results

        filename = f"{self.data_dir}/food_{datetime.now().strftime('%Y%m%d')}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"  [SAVED] {filename}")
        return results


if __name__ == '__main__':
    collector = FoodCollector()
    data = collector.collect_all()
    print(json.dumps(data, indent=2))

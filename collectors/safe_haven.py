import requests
import json
from datetime import datetime
import os

class SafeHavenCollector:
    def __init__(self):
        self.data_dir = 'data/prices'
        os.makedirs(self.data_dir, exist_ok=True)
        self.alpha_vantage_key = os.environ.get('ALPHA_VANTAGE_KEY', '')

    # ── GOLD ────────────────────────────────────────────────────

    def _gold_from_metals_live(self):
        """Source 1: metals.live — direct spot price, no key needed"""
        try:
            r = requests.get('https://api.metals.live/v1/spot/gold', timeout=10)
            if r.status_code == 200:
                price = float(r.json()[0]['price'])
                if 1500 < price < 5000:   # sanity check — real gold range
                    print(f"    [OK] Gold via metals.live: ${price}")
                    return price
        except Exception as e:
            print(f"    [WARN] metals.live failed: {e}")
        return None

    def _gold_from_yfinance(self):
        """Source 2: yfinance GC=F — gold futures, essentially spot"""
        try:
            import yfinance as yf
            hist = yf.Ticker('GC=F').history(period='2d')
            if not hist.empty:
                price = round(float(hist['Close'].iloc[-1]), 2)
                if 1500 < price < 5000:
                    print(f"    [OK] Gold via yfinance GC=F: ${price}")
                    return price
        except Exception as e:
            print(f"    [WARN] yfinance GC=F failed: {e}")
        return None

    def _gold_from_alpha_vantage(self):
        """Source 3: Alpha Vantage CURRENCY_EXCHANGE_RATE XAU/USD
           Works on free tier — returns spot FX rate for gold."""
        if not self.alpha_vantage_key:
            print("    [WARN] No ALPHA_VANTAGE_KEY set, skipping AV gold")
            return None
        try:
            url = (
                'https://www.alphavantage.co/query'
                '?function=CURRENCY_EXCHANGE_RATE'
                '&from_currency=XAU'
                '&to_currency=USD'
                f'&apikey={self.alpha_vantage_key}'
            )
            r = requests.get(url, timeout=15)
            data = r.json()
            rate_data = data.get('Realtime Currency Exchange Rate', {})
            rate = rate_data.get('5. Exchange Rate', '')
            if rate:
                price = round(float(rate), 2)
                if 1500 < price < 5000:
                    print(f"    [OK] Gold via Alpha Vantage XAU/USD: ${price}")
                    return price
                else:
                    print(f"    [WARN] AV returned suspicious gold price: ${price}")
        except Exception as e:
            print(f"    [WARN] Alpha Vantage XAU/USD failed: {e}")
        return None

    def get_gold_price(self):
        """Try three independent sources in order. First success wins."""
        print("  [GOLD] Trying 3 sources...")

        price = (
            self._gold_from_metals_live() or
            self._gold_from_yfinance()    or
            self._gold_from_alpha_vantage()
        )

        if price is None:
            print("  [FAIL] All gold sources failed — skipping Gold today")
            return None

        return {
            'asset':     'Gold',
            'symbol':    'XAU',
            'price':     price,
            'currency':  'USD',
            'date':      datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat()
        }

    # ── USD INDEX ────────────────────────────────────────────────

    def _usd_from_yfinance(self):
        """Source 1: yfinance DX-Y.NYB — actual DXY index"""
        try:
            import yfinance as yf
            hist = yf.Ticker('DX-Y.NYB').history(period='2d')
            if not hist.empty:
                price = round(float(hist['Close'].iloc[-1]), 2)
                if 80 < price < 130:   # sanity check — DXY realistic range
                    print(f"    [OK] USD Index via yfinance: {price}")
                    return price
        except Exception as e:
            print(f"    [WARN] yfinance DXY failed: {e}")
        return None

    def _usd_from_alpha_vantage(self):
        """Source 2: Alpha Vantage EUR/USD inverted × 112
           EUR/USD ~1.08 → DXY approximation ~103.7"""
        if not self.alpha_vantage_key:
            return None
        try:
            url = (
                'https://www.alphavantage.co/query'
                '?function=FX_DAILY'
                '&from_symbol=EUR'
                '&to_symbol=USD'
                f'&apikey={self.alpha_vantage_key}'
            )
            r = requests.get(url, timeout=15)
            data = r.json()
            series = data.get('Time Series FX (Daily)', {})
            if series:
                latest_date = sorted(series.keys())[-1]
                eurusd = float(series[latest_date]['4. close'])
                # Invert EUR/USD and scale to DXY range
                # DXY ≈ 1/EURUSD * 112 (approximate, EUR is 57.6% of DXY)
                price = round((1 / eurusd) * 112, 2)
                if 80 < price < 130:
                    print(f"    [OK] USD Index via AV EUR/USD inversion: {price}")
                    return price
        except Exception as e:
            print(f"    [WARN] Alpha Vantage EUR/USD failed: {e}")
        return None

    def get_usd_index(self):
        """Try two sources. First success wins."""
        print("  [USD] Trying 2 sources...")

        price = (
            self._usd_from_yfinance()        or
            self._usd_from_alpha_vantage()
        )

        if price is None:
            print("  [FAIL] All USD Index sources failed — skipping today")
            return None

        return {
            'asset':     'USD Index',
            'symbol':    'DXY',
            'price':     price,
            'date':      datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat()
        }

    # ── COLLECT ALL ──────────────────────────────────────────────

    def collect_all(self):
        results = {
            'category':  'safe_haven',
            'timestamp': datetime.now().isoformat(),
            'assets':    []
        }

        gold = self.get_gold_price()
        if gold:
            results['assets'].append(gold)

        usd = self.get_usd_index()
        if usd:
            results['assets'].append(usd)

        if not results['assets']:
            print("  [WARN] No safe haven data collected today")
            return results

        filename = f"{self.data_dir}/safe_haven_{datetime.now().strftime('%Y%m%d')}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"  [SAVED] {filename}")
        return results


if __name__ == '__main__':
    collector = SafeHavenCollector()
    data = collector.collect_all()
    print(json.dumps(data, indent=2))

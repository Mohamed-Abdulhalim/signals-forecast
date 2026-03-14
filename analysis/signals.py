import json
import os
from datetime import datetime, timedelta
import numpy as np

class SignalGenerator:
    def __init__(self):
        self.data_dir = 'data/prices'
        self.signal_dir = 'data/signals'
        os.makedirs(self.signal_dir, exist_ok=True)

        # Mean-reversion thresholds per asset class.
        # If price is more than X% above/below its 90-day average,
        # the mean-reversion check overrides or dampens the momentum signal.
        self.reversion_thresholds = {
            'energy':     0.12,   # 12% — energy is more volatile
            'safe_haven': 0.08,   # 8%  — gold/USD revert more reliably
            'food':       0.10,   # 10% — food commodities
        }

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

    def load_long_history(self, category, days=90):
        """Load a longer lookback for mean-reversion baseline"""
        return self.load_historical_data(category, days=days)

    def calculate_momentum(self, prices):
        """Calculate price momentum score"""
        if len(prices) < 2:
            return 0.5

        recent = prices[-7:]   # Last 7 days
        older  = prices[-14:-7]  # Previous 7 days

        if not recent or not older:
            return 0.5

        recent_avg = np.mean(recent)
        older_avg  = np.mean(older)

        if older_avg == 0:
            return 0.5

        change = (recent_avg - older_avg) / older_avg

        # Normalize to 0-1 scale: 10% change = 0.5 momentum shift
        momentum = 0.5 + (change * 5)
        return max(0, min(1, momentum))

    def calculate_volatility(self, prices):
        """Calculate price volatility level"""
        if len(prices) < 7:
            return 'Unknown'

        std_dev = np.std(prices[-14:])
        mean    = np.mean(prices[-14:])

        if mean == 0:
            return 'Unknown'

        cv = std_dev / mean  # Coefficient of variation

        if cv < 0.02:
            return 'Low'
        elif cv < 0.05:
            return 'Moderate'
        else:
            return 'High'

    def calculate_mean_reversion(self, prices_90d, threshold):
        """
        Check if current price is stretched relative to its 90-day mean.

        Returns:
          'stretched_high'  — price is significantly above long-run average (bearish bias)
          'stretched_low'   — price is significantly below long-run average (bullish bias)
          'normal'          — price is within normal range
          None              — insufficient data
        """
        if len(prices_90d) < 30:
            return None  # Need enough data for a meaningful baseline

        mean_90d    = np.mean(prices_90d)
        current     = prices_90d[-1]

        if mean_90d == 0:
            return None

        deviation = (current - mean_90d) / mean_90d

        if deviation > threshold:
            return 'stretched_high'
        elif deviation < -threshold:
            return 'stretched_low'
        else:
            return 'normal'

    def generate_signal(self, asset_name, prices, prices_90d=None, category='energy'):
        """Generate bullish/neutral/bearish signal with mean-reversion check"""
        if len(prices) < 7:
            return {
                'asset':      asset_name,
                'signal':     'neutral',
                'confidence': 'low',
                'reason':     'Insufficient data'
            }

        # ── Step 1: Momentum-based signal (existing logic) ──────────────────
        momentum  = self.calculate_momentum(prices)
        sma_short = np.mean(prices[-7:])
        sma_long  = np.mean(prices[-14:])

        if momentum > 0.6 and sma_short > sma_long:
            signal     = 'bullish'
            confidence = 'high' if momentum > 0.7 else 'medium'
        elif momentum < 0.4 and sma_short < sma_long:
            signal     = 'bearish'
            confidence = 'high' if momentum < 0.3 else 'medium'
        else:
            signal     = 'neutral'
            confidence = 'medium'

        # ── Step 2: Mean-reversion override ─────────────────────────────────
        reversion_applied = False
        threshold = self.reversion_thresholds.get(category, 0.10)

        if prices_90d and len(prices_90d) >= 30:
            stretch = self.calculate_mean_reversion(prices_90d, threshold)

            if stretch == 'stretched_high':
                # Price is far above its long-run average
                if signal == 'bullish':
                    # Momentum says up, but price is already stretched — downgrade
                    signal     = 'neutral'
                    confidence = 'medium'
                    reversion_applied = True
                elif signal == 'neutral':
                    # Neutral + stretched → lean bearish
                    signal     = 'bearish'
                    confidence = 'medium'
                    reversion_applied = True
                # If already bearish, reversion confirms — upgrade confidence
                elif signal == 'bearish' and confidence == 'medium':
                    confidence = 'high'
                    reversion_applied = True

            elif stretch == 'stretched_low':
                # Price is far below its long-run average
                if signal == 'bearish':
                    # Momentum says down, but price is deeply stretched — downgrade
                    signal     = 'neutral'
                    confidence = 'medium'
                    reversion_applied = True
                elif signal == 'neutral':
                    # Neutral + stretched low → lean bullish
                    signal     = 'bullish'
                    confidence = 'medium'
                    reversion_applied = True
                # If already bullish, reversion confirms — upgrade confidence
                elif signal == 'bullish' and confidence == 'medium':
                    confidence = 'high'
                    reversion_applied = True

        volatility = self.calculate_volatility(prices)

        result = {
            'asset':             asset_name,
            'signal':            signal,
            'confidence':        confidence,
            'momentum':          round(momentum, 2),
            'volatility':        volatility,
            'current_price':     prices[-1] if prices else None,
            'timestamp':         datetime.now().isoformat(),
            'reversion_applied': reversion_applied,
        }

        return result

    def process_category_data(self, historical_data):
        """Process historical data to extract price arrays per asset"""
        asset_prices = {}

        for day_data in historical_data:
            for asset in day_data.get('assets', []):
                asset_name = asset['asset']
                price      = asset['price']

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
            'signals':   []
        }

        for category in categories:
            # Load 30-day window for momentum
            historical_30  = self.load_historical_data(category, days=30)
            # Load 90-day window for mean-reversion baseline
            historical_90  = self.load_historical_data(category, days=90)

            if not historical_30:
                continue

            asset_prices_30 = self.process_category_data(historical_30)
            asset_prices_90 = self.process_category_data(historical_90)

            for asset_name, prices in asset_prices_30.items():
                prices_90d = asset_prices_90.get(asset_name, [])
                signal = self.generate_signal(
                    asset_name,
                    prices,
                    prices_90d=prices_90d,
                    category=category
                )
                signal['category'] = category
                all_signals['signals'].append(signal)

        # Save signals
        filename = f"{self.signal_dir}/signals_{datetime.now().strftime('%Y%m%d')}.json"
        with open(filename, 'w') as f:
            json.dump(all_signals, f, indent=2)

        return all_signals


if __name__ == '__main__':
    generator = SignalGenerator()
    signals   = generator.generate_all_signals()
    print(json.dumps(signals, indent=2))

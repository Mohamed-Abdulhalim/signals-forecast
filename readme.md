# EdgePulse

**Commodity intelligence for operators who can't afford surprises.**

Live at → [signals-forecast.vercel.app](https://signals-forecast.vercel.app)

---

EdgePulse tracks 7 instability-sensitive assets across energy, safe haven, and food supply categories — generating daily signals, 30-day forecasts, and confidence-rated outlooks from public market data.

Built for import/export operators, supply chain managers, and commodity-exposed businesses who need directional intelligence without a Bloomberg terminal.

---

## What It Tracks

| Category | Assets |
|----------|--------|
| **Energy** | Brent Oil, Natural Gas |
| **Safe Haven** | Gold, USD Index |
| **Food & Supply** | Wheat, Corn, Rice |

---

## How It Works

```
Public APIs → Daily Collection → Signal Engine → Forecast Model → Live Dashboard
```

**Data pipeline runs automatically via GitHub Actions:**
- Every 4 hours — price refresh
- Daily 8AM UTC — full data collection
- Monday 9AM UTC — signal + forecast generation

No manual intervention. No server to maintain.

---

## Signal Logic

Signals are derived from three converging indicators:

- **Momentum score** — normalized rate of change over recent periods
- **Trend direction** — short vs. long-period moving average crossover
- **Volatility regime** — standard deviation classification (low / moderate / high)

When all three align → High Confidence. Mixed signals → Medium. Insufficient data → Low.

Output: `Bullish` · `Neutral` · `Bearish` with confidence rating and momentum score.

---

## Forecast Model

Linear regression over asset-specific lookback windows:

| Asset | Regression Window | Notes |
|-------|------------------|-------|
| Brent Oil | 30 days | Standard |
| Gold | 30 days | Standard |
| USD Index | 30 days | Standard |
| Natural Gas | 21 days | High seasonality |
| Wheat | 21 days | High seasonality |
| Corn | 21 days | High seasonality |
| Rice | 30 days | ETF proxy (PDBA) |

Output: 30-day price target with upper/lower confidence bounds.

---

## Data Sources

| Asset | Primary | Fallback |
|-------|---------|----------|
| Brent Oil | Alpha Vantage | — |
| Natural Gas | Alpha Vantage | — |
| Gold | metals.live | yfinance GC=F → Alpha Vantage |
| USD Index | yfinance DX-Y.NYB | Alpha Vantage EUR/USD inverted |
| Wheat | Alpha Vantage | — |
| Corn | Alpha Vantage | — |
| Rice | yfinance PDBA | Alpha Vantage |

All sources are public and free. One API key required (Alpha Vantage — free tier sufficient).

---

## Project Structure

```
signals-forecast/
├── .github/workflows/       # Automation (collect, analyze, refresh)
├── collectors/
│   ├── energy.py            # Brent Oil, Natural Gas
│   ├── safe_haven.py        # Gold (3-source fallback), USD Index
│   ├── food.py              # Wheat, Corn, Rice
│   └── refresh_prices.py    # 4-hour lightweight price refresh
├── analysis/
│   ├── signals.py           # Momentum + trend signal engine
│   └── forecasts.py         # Asset-specific regression forecasts
├── data/
│   ├── prices/              # Daily JSON price files
│   ├── signals/             # Weekly signal outputs
│   └── forecasts/           # Weekly forecast outputs
├── web/
│   ├── app.py               # Flask routes
│   ├── static/
│   │   ├── style.css        # Design system
│   │   └── tooltips.js      # Tooltip engine
│   └── templates/           # 6 pages
├── sitemap.xml
├── robots.txt
├── requirements.txt
└── vercel.json
```

---

## Deployment

This project is deployed on Vercel with GitHub Actions handling all data operations.

**Environment variable required:**
```
ALPHA_VANTAGE_KEY=your_key_here
```

Get a free key at [alphavantage.co](https://www.alphavantage.co/support/#api-key) — 25 requests/day is enough.

**To fork and deploy your own instance:**

1. Fork the repo
2. Add `ALPHA_VANTAGE_KEY` to GitHub Secrets
3. Connect repo to Vercel
4. GitHub Actions handles everything else

No scheduler to run. No server to provision. Fully automated from day one.

---

## Stack

`Python` `Flask` `NumPy` `SciPy` `yfinance` `Vercel` `GitHub Actions`

---

## Built By

[Mohamed Abdulhalim](https://github.com/Mohamed-Abdulhalim) — data systems & commodity intelligence.

For custom forecasting pipelines, market data infrastructure, or intelligence dashboards:
**mohamed.data.solutions@gmail.com**

---

*EdgePulse is an independent intelligence tool. Not financial advice.*

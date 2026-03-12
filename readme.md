# Signals & Forecasts

A focused intelligence dashboard for instability-sensitive assets.

## Overview

This system tracks 7 key assets across 3 categories:

**Energy:** Brent Oil, Natural Gas  
**Safe Haven:** Gold, USD Index  
**Food & Supply:** Wheat, Rice, Corn

## Features

- **Daily price collection** from reliable public APIs
- **Signal generation** (bullish/neutral/bearish) based on momentum and trend analysis
- **30-day and 90-day forecasts** with confidence ranges
- **Track record** to document prediction accuracy
- **Clean web interface** for public viewing

## Quick Start

### 1. Environment Setup

```bash
# Clone or download this project
cd signals-forecast

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Get API Keys

**Alpha Vantage** (required for energy data):
- Sign up: https://www.alphavantage.co/support/#api-key
- Free tier: 25 requests/day

Create `.env` file:
```bash
cp .env.example .env
# Edit .env and add your Alpha Vantage key
```

### 3. Run Initial Data Collection

```bash
# Collect first data set
python collectors/energy.py
python collectors/safe_haven.py
python collectors/food.py
```

This creates `data/prices/` with today's data.

### 4. Generate Signals & Forecasts

After 7-14 days of data collection:

```bash
# Generate signals
python analysis/signals.py

# Generate forecasts
python analysis/forecasts.py
```

### 5. Launch Website

```bash
cd web
python app.py
```

Visit: http://localhost:5000

## Project Structure

```
signals-forecast/
├── collectors/          # Data collection scripts
│   ├── energy.py
│   ├── safe_haven.py
│   └── food.py
├── analysis/           # Signal and forecast generation
│   ├── signals.py
│   └── forecasts.py
├── data/              # Stored data (git-ignored)
│   ├── prices/
│   ├── signals/
│   └── forecasts/
├── web/               # Flask web application
│   ├── app.py
│   ├── static/
│   │   └── style.css
│   └── templates/
│       ├── index.html
│       ├── signals.html
│       ├── forecasts.html
│       ├── methodology.html
│       ├── track_record.html
│       └── work_with_me.html
├── scheduler.py       # Automation script
├── requirements.txt
└── .env              # Your API keys (not committed)
```

## Automation

Run the scheduler to automate data collection:

```bash
python scheduler.py
```

Schedule:
- **Daily 8:00 AM** - Collect price data
- **Weekly Monday 9:00 AM** - Generate signals & forecasts

Alternatively, use cron (Linux/Mac) or Task Scheduler (Windows).

## Data Sources

- **Energy:** Alpha Vantage API
- **Safe Haven:** Yahoo Finance (via yfinance)
- **Food Commodities:** Yahoo Finance futures data

All sources are public and free.

## Deployment

### Option 1: Simple VPS (DigitalOcean, Linode, AWS EC2)

```bash
# Install dependencies
pip install -r requirements.txt

# Set up systemd service (Linux)
sudo nano /etc/systemd/system/signals-forecast.service

# Run web app
gunicorn --bind 0.0.0.0:5000 web.app:app

# Run scheduler in background
nohup python scheduler.py &
```

### Option 2: Vercel (frontend only)

- Deploy static HTML/CSS
- Use serverless functions for API endpoints
- Schedule data collection via GitHub Actions

### Option 3: Heroku

```bash
# Create Procfile
web: gunicorn web.app:app
worker: python scheduler.py

# Deploy
heroku create your-app-name
git push heroku main
```

## Customization

### Add More Assets

Edit `analysis/forecasts.py` and `analysis/signals.py`:

```python
assets = [
    ('category', 'Asset Name'),
    # Add your new asset
]
```

Create corresponding collector in `collectors/`.

### Change Forecast Horizon

In `analysis/forecasts.py`, modify:

```python
forecast_30 = self.linear_forecast(prices, 30)  # Change 30 to desired days
```

### Modify Signal Logic

In `analysis/signals.py`, adjust thresholds:

```python
if momentum > 0.6 and sma_short > sma_long:  # Tweak 0.6 threshold
    signal = 'bullish'
```

## Maintenance

### Weekly Tasks
- Review signal accuracy
- Check data collection logs
- Update methodology based on performance

### Monthly Tasks
- Evaluate forecast accuracy
- Update track record page
- Refine models if needed

## Troubleshooting

**No data appearing:**
- Check `.env` file has correct API key
- Verify internet connection
- Check `data/prices/` directory exists

**Forecasts showing "insufficient data":**
- Need at least 14 days of price history
- Run collectors daily for 2 weeks first

**Website not loading:**
- Check Flask is running: `python web/app.py`
- Verify port 5000 isn't blocked
- Check console for error messages

## License

MIT - Build whatever you want with this.

## Contact

For custom forecasting systems: [your.email@example.com]

---

Built with Flask, NumPy, and persistence.

import schedule
import time
import sys
import os
from datetime import datetime

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from collectors.energy import EnergyCollector
from collectors.safe_haven import SafeHavenCollector
from collectors.food import FoodCollector
from analysis.signals import SignalGenerator
from analysis.forecasts import ForecastEngine

def collect_daily_data():
    """Run daily data collection"""
    print(f"\n{'='*50}")
    print(f"Daily Data Collection - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")
    
    try:
        # Collect energy data
        print("\n[1/3] Collecting energy prices...")
        energy = EnergyCollector()
        energy_data = energy.collect_all()
        print(f"✓ Energy data collected: {len(energy_data.get('assets', []))} assets")
        
        # Collect safe haven data
        print("\n[2/3] Collecting safe haven assets...")
        safe_haven = SafeHavenCollector()
        safe_haven_data = safe_haven.collect_all()
        print(f"✓ Safe haven data collected: {len(safe_haven_data.get('assets', []))} assets")
        
        # Collect food commodity data
        print("\n[3/3] Collecting food commodities...")
        food = FoodCollector()
        food_data = food.collect_all()
        print(f"✓ Food data collected: {len(food_data.get('assets', []))} assets")
        
        print("\n✓ Daily data collection complete!")
        
    except Exception as e:
        print(f"\n✗ Error during data collection: {e}")

def generate_weekly_signals():
    """Run weekly signal generation"""
    print(f"\n{'='*50}")
    print(f"Weekly Signal Generation - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")
    
    try:
        # Generate signals
        print("\n[1/2] Generating market signals...")
        generator = SignalGenerator()
        signals = generator.generate_all_signals()
        print(f"✓ Signals generated for {len(signals.get('signals', []))} assets")
        
        # Generate forecasts
        print("\n[2/2] Generating price forecasts...")
        engine = ForecastEngine()
        forecasts = engine.generate_all_forecasts()
        print(f"✓ Forecasts generated for {len(forecasts.get('forecasts', []))} assets")
        
        print("\n✓ Weekly analysis complete!")
        
    except Exception as e:
        print(f"\n✗ Error during weekly analysis: {e}")

def run_scheduler():
    """Set up and run the scheduler"""
    print("Signal & Forecast Scheduler Started")
    print("=" * 50)
    print("\nSchedule:")
    print("- Daily: 8:00 AM - Data collection")
    print("- Weekly: Monday 9:00 AM - Signal generation & forecasts")
    print("\nPress Ctrl+C to stop\n")
    
    # Schedule daily data collection
    schedule.every().day.at("08:00").do(collect_daily_data)
    
    # Schedule weekly signal generation (Monday 9 AM)
    schedule.every().monday.at("09:00").do(generate_weekly_signals)
    
    # For testing: run immediately on startup
    # Uncomment these lines during development:
    # collect_daily_data()
    # generate_weekly_signals()
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == '__main__':
    try:
        run_scheduler()
    except KeyboardInterrupt:
        print("\n\nScheduler stopped by user")

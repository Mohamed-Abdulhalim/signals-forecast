import time

from edgepulse.model import clean_series


def fetch_history(tickers, period="10y", attempts=3):
    import yfinance as yf

    last_error = None
    for attempt in range(attempts):
        try:
            frame = yf.download(
                tickers=list(tickers),
                period=period,
                interval="1d",
                auto_adjust=False,
                progress=False,
                group_by="ticker",
                threads=False,
            )
            if frame is not None and not frame.empty:
                return frame
        except Exception as e:
            last_error = e
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"Yahoo download failed: {last_error}")


def series_for(frame, asset):
    ticker = asset["ticker"]
    try:
        closes = frame[ticker]["Close"]
    except KeyError:
        return []
    points = [(idx.date(), float(v) / asset["divisor"]) for idx, v in closes.dropna().items()]
    return clean_series(points, asset["spike"])

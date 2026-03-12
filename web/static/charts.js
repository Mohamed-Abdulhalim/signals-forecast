/**
 * charts.js — EdgePulse chart system
 * Sparklines on signals page, forecast charts on forecasts page
 * Uses Chart.js loaded from CDN
 */

const EP = {
  gold:    '#C9A84C',
  goldDim: '#8B6914',
  green:   '#4a9a6a',
  grey:    '#555550',
  red:     '#9a4a4a',
  bg:      '#141413',
  border:  '#222220',
  text:    '#9a9690',
};

// ── Sparklines (signals page) ────────────────────────────────
async function initSparklines() {
  const wraps = document.querySelectorAll('[data-sparkline]');
  if (!wraps.length) return;

  let chartData;
  try {
    const res = await fetch('/api/chart-data');
    chartData = await res.json();
  } catch (e) {
    console.warn('Could not load chart data:', e);
    return;
  }

  wraps.forEach(wrap => {
    const asset = wrap.dataset.sparkline;
    const signal = wrap.dataset.signal || 'neutral';
    const data = chartData[asset];
    if (!data || !data.history.length) return;

    const canvas = document.createElement('canvas');
    canvas.style.width  = '100%';
    canvas.style.height = '60px';
    wrap.appendChild(canvas);

    const prices = data.history.map(d => d.price);
    const labels = data.history.map(d => d.date);

    // Color by signal
    const color = signal === 'bullish' ? EP.green
                : signal === 'bearish' ? EP.red
                : EP.grey;

    new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          data: prices,
          borderColor: color,
          borderWidth: 1.5,
          pointRadius: 0,
          fill: true,
          backgroundColor: (ctx) => {
            const gradient = ctx.chart.ctx.createLinearGradient(0, 0, 0, 60);
            gradient.addColorStop(0, color + '33');
            gradient.addColorStop(1, color + '00');
            return gradient;
          },
          tension: 0.3,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        scales: {
          x: { display: false },
          y: { display: false }
        },
        elements: { line: { borderCapStyle: 'round' } }
      }
    });
  });
}

// ── Forecast charts (forecasts page) ────────────────────────
async function initForecastCharts() {
  const wraps = document.querySelectorAll('[data-forecast-chart]');
  if (!wraps.length) return;

  let chartData;
  try {
    const res = await fetch('/api/chart-data');
    chartData = await res.json();
  } catch (e) {
    console.warn('Could not load chart data:', e);
    return;
  }

  wraps.forEach(wrap => {
    const asset = wrap.dataset.forecastChart;
    const data = chartData[asset];
    if (!data || !data.history.length || !data.forecast) return;

    const canvas = document.createElement('canvas');
    canvas.style.width  = '100%';
    canvas.style.height = '180px';
    wrap.appendChild(canvas);

    const history  = data.history;
    const forecast = data.forecast;

    // Last historical point + forecast point
    const lastDate  = history[history.length - 1].date;
    const lastPrice = history[history.length - 1].price;

    const histLabels = history.map(d => d.date);
    const histPrices = history.map(d => d.price);

    // Forecast line: from last point to forecast date
    const projLabels = [lastDate, forecast.date];
    const projPrices = [lastPrice, forecast.target];

    // Direction color
    const goingUp = forecast.target > lastPrice;
    const lineColor = goingUp ? EP.green : EP.red;

    new Chart(canvas, {
      type: 'line',
      data: {
        labels: [...histLabels, forecast.date],
        datasets: [
          // Historical line
          {
            label: 'Historical',
            data: [...histPrices, null],
            borderColor: EP.gold,
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false,
            tension: 0.2,
            segment: {},
          },
          // Forecast projection
          {
            label: 'Forecast',
            data: [...Array(histPrices.length - 1).fill(null), lastPrice, forecast.target],
            borderColor: lineColor,
            borderWidth: 1.5,
            borderDash: [5, 4],
            pointRadius: [0, 0, 4],
            pointBackgroundColor: lineColor,
            fill: false,
            tension: 0.1,
          },
          // Upper bound
          {
            label: 'Upper',
            data: [...Array(histPrices.length - 1).fill(null), lastPrice, forecast.upper],
            borderColor: 'transparent',
            pointRadius: 0,
            fill: '+1',
            backgroundColor: lineColor + '18',
            tension: 0.1,
          },
          // Lower bound
          {
            label: 'Lower',
            data: [...Array(histPrices.length - 1).fill(null), lastPrice, forecast.lower],
            borderColor: 'transparent',
            pointRadius: 0,
            fill: false,
            tension: 0.1,
          },
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 600, easing: 'easeInOutQuart' },
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1c1c1c',
            borderColor: EP.border,
            borderWidth: 1,
            titleColor: EP.text,
            bodyColor: EP.gold,
            titleFont: { family: 'DM Mono', size: 10 },
            bodyFont:  { family: 'DM Mono', size: 11 },
            callbacks: {
              title: (items) => items[0].label,
              label: (item) => {
                if (item.datasetIndex === 0 && item.raw !== null)
                  return ` $${Number(item.raw).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                if (item.datasetIndex === 1 && item.raw !== null)
                  return ` Forecast $${Number(item.raw).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                return null;
              },
              filter: (item) => item.raw !== null && item.datasetIndex <= 1,
            }
          }
        },
        scales: {
          x: {
            ticks: {
              color: EP.text,
              font: { family: 'DM Mono', size: 9 },
              maxTicksLimit: 6,
              maxRotation: 0,
            },
            grid: { color: EP.border + '80', drawBorder: false },
          },
          y: {
            ticks: {
              color: EP.text,
              font: { family: 'DM Mono', size: 9 },
              maxTicksLimit: 5,
              callback: (v) => '$' + Number(v).toLocaleString('en-US', {maximumFractionDigits: 2}),
            },
            grid: { color: EP.border + '80', drawBorder: false },
          }
        }
      }
    });
  });
}

// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  if (document.querySelector('[data-sparkline]'))       initSparklines();
  if (document.querySelector('[data-forecast-chart]'))  initForecastCharts();
});

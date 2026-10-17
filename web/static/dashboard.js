(function () {
  if (typeof Chart === 'undefined') return;
  const css = getComputedStyle(document.documentElement);
  const color = (name, fallback) => (css.getPropertyValue(name) || fallback).trim();
  const gold = color('--gold', '#C9A84C');
  const up = color('--bullish-text', '#6ab88a');
  const down = color('--bearish-text', '#c07070');
  const muted = color('--text-muted', '#5a5855');

  document.querySelectorAll('canvas[data-chart]').forEach(canvas => {
    let d;
    try { d = JSON.parse(canvas.dataset.chart); } catch (e) { return; }
    if (!d.history || d.history.length < 2) return;

    const labels = d.history.map(p => p[0]);
    const prices = d.history.map(p => p[1]);
    const n = prices.length;
    const line = d.trend === 'down' ? down : up;
    const datasets = [{
      data: prices,
      borderColor: line,
      borderWidth: 1.4,
      pointRadius: 0,
      tension: 0.15,
    }];

    if (d.lo && d.hi && d.target) {
      labels.push(d.target);
      prices.push(null);
      const endDot = Array(n + 1).fill(0).map((_, i) => (i === n ? 2 : 0));
      const cone = v => Array(n - 1).fill(null).concat([prices[n - 1], v]);
      datasets.push({ data: cone(d.hi), borderColor: gold, borderWidth: 1, borderDash: [4, 3], pointRadius: endDot, fill: false });
      datasets.push({ data: cone(d.lo), borderColor: gold, borderWidth: 1, borderDash: [4, 3], pointRadius: endDot, fill: '-1', backgroundColor: 'rgba(201,168,76,0.10)' });
    }

    const fmt = v => v == null ? '' : Number(v).toLocaleString('en-US', { minimumFractionDigits: d.decimals, maximumFractionDigits: d.decimals });

    new Chart(canvas, {
      type: 'line',
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        spanGaps: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            filter: item => item.raw != null,
            callbacks: {
              label: item => item.datasetIndex === 0 ? fmt(item.raw) : (item.datasetIndex === 1 ? 'high ' : 'low ') + fmt(item.raw),
            },
          },
        },
        scales: {
          x: { display: false },
          y: { position: 'right', ticks: { color: muted, font: { size: 10 }, maxTicksLimit: 4, callback: v => fmt(v) }, grid: { color: 'rgba(255,255,255,0.03)' } },
        },
      },
    });
  });
})();

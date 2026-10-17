(function () {
  if (typeof Chart === 'undefined') return;
  const css = getComputedStyle(document.documentElement);
  const color = (name, fallback) => (css.getPropertyValue(name) || fallback).trim();
  const gold = color('--gold', '#C9A84C');
  const line = color('--text-secondary', '#9a9690');
  const muted = color('--text-muted', '#5a5855');
  const HISTORY_POINTS = 130;

  function businessDays(fromIso, toIso) {
    const out = [];
    const d = new Date(fromIso + 'T00:00:00Z');
    const end = new Date(toIso + 'T00:00:00Z');
    d.setUTCDate(d.getUTCDate() + 1);
    while (d <= end) {
      const wd = d.getUTCDay();
      if (wd !== 0 && wd !== 6) out.push(d.toISOString().slice(0, 10));
      d.setUTCDate(d.getUTCDate() + 1);
    }
    return out;
  }

  document.querySelectorAll('canvas[data-chart]').forEach(canvas => {
    let d;
    try { d = JSON.parse(canvas.dataset.chart); } catch (e) { return; }
    if (!d.history || d.history.length < 2) return;

    const hist = d.history.slice(-HISTORY_POINTS);
    const labels = hist.map(p => p[0]);
    const prices = hist.map(p => p[1]);
    const n = prices.length;
    const last = prices[n - 1];
    const datasets = [{
      data: prices.slice(),
      borderColor: line,
      borderWidth: 1.4,
      pointRadius: 0,
      tension: 0.15,
      order: 1,
    }];

    if (d.lo && d.hi && d.target) {
      const future = businessDays(labels[n - 1], d.target);
      const m = future.length;
      if (m > 0) {
        labels.push(...future);
        datasets[0].data.push(...Array(m).fill(null));
        const fan = edge => Array(n - 1).fill(null).concat(
          [last],
          future.map((_, k) => last * Math.pow(edge / last, Math.sqrt((k + 1) / m)))
        );
        const style = { borderColor: gold, borderWidth: 1, borderDash: [4, 3], pointRadius: 0, tension: 0, order: 2 };
        datasets.push(Object.assign({ data: fan(d.hi), fill: false }, style));
        datasets.push(Object.assign({ data: fan(d.lo), fill: '-1', backgroundColor: 'rgba(201,168,76,0.14)' }, style));
      }
    }

    const fmt = v => v == null ? '' : Number(v).toLocaleString('en-US', { minimumFractionDigits: d.decimals, maximumFractionDigits: d.decimals });

    new Chart(canvas, {
      type: 'line',
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            filter: item => item.raw != null && !(item.datasetIndex > 0 && item.dataIndex === n - 1),
            callbacks: {
              label: item => item.datasetIndex === 0 ? fmt(item.raw) : (item.datasetIndex === 1 ? 'range high ' : 'range low ') + fmt(item.raw),
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

/**
 * tooltips.js
 * Portal-based tooltip system.
 * Renders tooltip into a fixed div on <body> so it is never
 * clipped by overflow:hidden parents (signal grid, metric grid, etc.)
 *
 * Usage in HTML:
 *   <span class="tooltip-wrap">
 *     Label text
 *     <span class="tooltip-icon">?</span>
 *     <span class="tooltip-box">Explanation text here.</span>
 *   </span>
 */

(function () {
  // Create the portal element once
  const portal = document.createElement('div');
  portal.id = 'tooltip-portal';
  portal.innerHTML = '<div class="tooltip-inner"></div>';
  document.body.appendChild(portal);

  const inner = portal.querySelector('.tooltip-inner');
  let hideTimer = null;

  function showTooltip(icon) {
    const box = icon.closest('.tooltip-wrap')?.querySelector('.tooltip-box');
    if (!box) return;

    clearTimeout(hideTimer);

    inner.textContent = box.textContent.trim();

    // Position: above the icon, centred
    const rect = icon.getBoundingClientRect();
    const tipW = 220;
    const tipH = 80; // approximate, will adjust after render

    let left = rect.left + rect.width / 2 - tipW / 2;
    let top  = rect.top - tipH - 10 + window.scrollY;

    // Keep within viewport horizontally
    left = Math.max(8, Math.min(left, window.innerWidth - tipW - 8));

    portal.style.left   = left + 'px';
    portal.style.top    = (rect.top + window.scrollY - 10) + 'px'; // initial, adjusted below
    portal.style.width  = tipW + 'px';
    portal.classList.add('visible');

    // After render, adjust vertical position properly
    requestAnimationFrame(() => {
      const h = portal.offsetHeight;
      portal.style.top = (rect.top + window.scrollY - h - 8) + 'px';
    });
  }

  function hideTooltip() {
    hideTimer = setTimeout(() => {
      portal.classList.remove('visible');
    }, 80);
  }

  // Attach events to all tooltip icons
  function init() {
    document.querySelectorAll('.tooltip-icon').forEach(icon => {
      icon.addEventListener('mouseenter', () => showTooltip(icon));
      icon.addEventListener('mouseleave', hideTooltip);
      icon.addEventListener('focus',      () => showTooltip(icon));
      icon.addEventListener('blur',       hideTooltip);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

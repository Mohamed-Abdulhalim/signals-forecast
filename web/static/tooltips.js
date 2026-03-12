/**
 * tooltips.js — position: fixed tooltip positioner
 * The .tooltip-box is already position:fixed in CSS.
 * This script just sets the correct top/left on mouseenter
 * so it appears above the hovered icon, viewport-relative.
 */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.tooltip-wrap').forEach(function (wrap) {
    var box = wrap.querySelector('.tooltip-box');
    if (!box) return;

    wrap.addEventListener('mouseenter', function () {
      var icon = wrap.querySelector('.tooltip-icon') || wrap;
      var r = icon.getBoundingClientRect();

      // Position above the icon, centred horizontally
      var tipW = 220;
      var left = r.left + r.width / 2 - tipW / 2;

      // Clamp to viewport
      left = Math.max(8, Math.min(left, window.innerWidth - tipW - 8));

      box.style.left = left + 'px';
      box.style.width = tipW + 'px';

      // Temporarily show off-screen to measure height
      box.style.visibility = 'hidden';
      box.style.opacity = '0';
      box.style.top = '0px';

      // Use rAF so browser has painted and we can measure
      requestAnimationFrame(function () {
        var h = box.offsetHeight;
        var top = r.top - h - 8;

        // If it would go above viewport, show below instead
        if (top < 8) top = r.bottom + 8;

        box.style.top = top + 'px';
        box.style.visibility = 'visible';
        box.style.opacity = '1';
      });
    });
  });
});

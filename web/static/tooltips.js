/**
 * tooltips.js — clean JS-only tooltip system
 * One shared box appended to body. No CSS hover. No overflow clipping.
 */
(function () {
  // Create one shared tooltip box on body
  var box = document.createElement('div');
  box.style.cssText = [
    'position:fixed',
    'z-index:99999',
    'background:#1c1c1c',
    'border:1px solid #2a2a2a',
    'border-radius:6px',
    'padding:10px 14px',
    'width:220px',
    'font-family:Outfit,sans-serif',
    'font-size:13px',
    'font-weight:300',
    'color:#9a9690',
    'line-height:1.5',
    'box-shadow:0 8px 32px rgba(0,0,0,0.8)',
    'pointer-events:none',
    'opacity:0',
    'transition:opacity 0.15s ease',
    'white-space:normal',
    'display:block'
  ].join(';');
  document.body.appendChild(box);

  var current = null;

  function show(icon, text) {
    box.textContent = text;
    box.style.opacity = '0';
    box.style.top = '-999px';
    box.style.left = '-999px';

    // Need to paint first to measure height
    requestAnimationFrame(function () {
      var r   = icon.getBoundingClientRect();
      var w   = 220;
      var h   = box.offsetHeight;
      var left = r.left + r.width / 2 - w / 2;
      var top  = r.top - h - 10;

      // Clamp horizontally
      left = Math.max(8, Math.min(left, window.innerWidth - w - 8));
      // Flip below if not enough space above
      if (top < 8) top = r.bottom + 10;

      box.style.left    = left + 'px';
      box.style.top     = top  + 'px';
      box.style.width   = w    + 'px';
      box.style.opacity = '1';
    });
  }

  function hide() {
    box.style.opacity = '0';
    current = null;
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.tooltip-wrap').forEach(function (wrap) {
      var textEl = wrap.querySelector('.tooltip-box');
      if (!textEl) return;
      var text = textEl.textContent.trim();

      var icon = wrap.querySelector('.tooltip-icon');
      if (!icon) return;

      icon.addEventListener('mouseenter', function () {
        current = icon;
        show(icon, text);
      });

      icon.addEventListener('mouseleave', function () {
        hide();
      });
    });
  });
})();

/* ============================================================
   static/js/hero-3d.js  —  v2
   ------------------------------------------------------------
   A quiet gradient field for the homepage hero.

   Design reference: Linear / Vercel homepage backgrounds — a
   near-still surface with one soft light that drifts slowly.
   Low contrast, muted, never asking to be looked at.

   Technique (kept deliberately simple, per Three.js's own
   gradient examples): one fullscreen plane, one fragment
   shader, a single smooth light blob moving on a slow path
   plus faint film grain so the gradient never visibly bands.
   No geometry, no lights, no models — 60fps on a laptop GPU.

   Loaded only on pages that contain .hero-section, only after
   the page is idle, never on mobile, never under reduced motion.
   ============================================================ */

(function () {
  'use strict';

  if (typeof THREE === 'undefined') return;

  const host = document.querySelector('.hero-section');
  if (!host) return;

  /* ── Canvas behind hero content ─────────────────────────── */
  const canvas = document.createElement('canvas');
  canvas.setAttribute('aria-hidden', 'true');
  Object.assign(canvas.style, {
    position: 'absolute',
    inset: '0',
    width: '100%',
    height: '100%',
    borderRadius: 'inherit',
    zIndex: '0',
    pointerEvents: 'none',
    opacity: '0',
    transition: 'opacity 800ms cubic-bezier(0.2, 0, 0, 1)'
  });

  if (getComputedStyle(host).position === 'static') host.style.position = 'relative';
  host.style.overflow = 'hidden';
  host.insertBefore(canvas, host.firstChild);

  Array.prototype.forEach.call(host.children, function (child) {
    if (child === canvas) return;
    if (getComputedStyle(child).position === 'static') child.style.position = 'relative';
    child.style.zIndex = '1';
  });

  /* ── Palette from design tokens ─────────────────────────── */
  const css  = getComputedStyle(document.documentElement);
  const dark = document.documentElement.getAttribute('data-theme') === 'dark';

  function hexToVec(hex, fallback) {
    const h = (hex || '').trim().replace('#', '') || fallback;
    return [
      parseInt(h.substring(0, 2), 16) / 255,
      parseInt(h.substring(2, 4), 16) / 255,
      parseInt(h.substring(4, 6), 16) / 255
    ];
  }

  /* Two closely-related tones. Low contrast is the whole point. */
  const cField = hexToVec(css.getPropertyValue('--surface'),    dark ? '151A21' : 'FFFFFF');
  const cGlow  = hexToVec(css.getPropertyValue('--brand-tint'), dark ? '1E2A3D' : 'E8EDF5');

  /* ── Renderer ───────────────────────────────────────────── */
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({
      canvas: canvas,
      antialias: false,
      alpha: true,
      powerPreference: 'low-power'
    });
  } catch (e) {
    canvas.remove();
    return;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));

  const scene  = new THREE.Scene();
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

  const uniforms = {
    uTime:  { value: 0 },
    uRes:   { value: new THREE.Vector2(1, 1) },
    uField: { value: new THREE.Vector3().fromArray(cField) },
    uGlow:  { value: new THREE.Vector3().fromArray(cGlow) },
    uDark:  { value: dark ? 1.0 : 0.0 }
  };

  const vertexShader = [
    'varying vec2 vUv;',
    'void main() {',
    '  vUv = uv;',
    '  gl_Position = vec4(position, 1.0);',
    '}'
  ].join('\n');

  /* One soft radial light on a slow Lissajous path, a faint
     second light for asymmetry, and dither to kill banding.  */
  const fragmentShader = [
    'precision mediump float;',
    'varying vec2 vUv;',
    'uniform float uTime;',
    'uniform vec2  uRes;',
    'uniform vec3  uField;',
    'uniform vec3  uGlow;',
    'uniform float uDark;',

    'float dither(vec2 p) {',
    '  return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453) - 0.5;',
    '}',

    'void main() {',
    '  vec2 uv = vUv;',
    '  float agu = uRes.x / uRes.y;',
    '  vec2 p = vec2((uv.x - 0.5) * agu, uv.y - 0.5);',

    '  float t = uTime * 0.06;',                 /* very slow */

    /* primary light — wide, soft, drifting */
    '  vec2 c1 = vec2(sin(t) * 0.28 * agu, cos(t * 0.8) * 0.18);',
    '  float d1 = length(p - c1);',
    '  float g1 = smoothstep(0.9, 0.0, d1);',

    /* secondary light — smaller, opposite drift, faint */
    '  vec2 c2 = vec2(sin(t * 0.7 + 2.0) * 0.34 * agu, cos(t + 1.0) * 0.22);',
    '  float d2 = length(p - c2);',
    '  float g2 = smoothstep(0.7, 0.0, d2) * 0.5;',

    '  float glow = clamp(g1 + g2, 0.0, 1.0);',

    /* mix tones — gentle in light mode, a touch stronger in dark */
    '  float strength = mix(0.6, 0.85, uDark);',
    '  vec3 col = mix(uField, uGlow, glow * strength);',

    /* vertical settle so the top is calmer than the middle */
    '  col = mix(col, uField, smoothstep(0.5, 1.0, uv.y) * 0.25);',

    /* dither ±1/255 to prevent visible gradient banding */
    '  col += dither(gl_FragCoord.xy) * (1.0 / 255.0);',

    /* fade at edges so it never fights the panel border */
    '  float edge = smoothstep(0.0, 0.12, uv.x) * smoothstep(1.0, 0.88, uv.x)',
    '             * smoothstep(0.0, 0.10, uv.y) * smoothstep(1.0, 0.90, uv.y);',

    '  gl_FragColor = vec4(col, edge);',
    '}'
  ].join('\n');

  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(2, 2),
    new THREE.ShaderMaterial({
      uniforms: uniforms,
      vertexShader: vertexShader,
      fragmentShader: fragmentShader,
      transparent: true
    })
  );
  scene.add(mesh);

  /* ── Size ───────────────────────────────────────────────── */
  function resize() {
    const w = host.clientWidth;
    const h = host.clientHeight;
    renderer.setSize(w, h, false);
    uniforms.uRes.value.set(w, h);
  }
  resize();

  let resizeTimer = null;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(resize, 150);
  });

  /* ── Loop — paused off-screen and when tab hidden ───────── */
  let running = true;
  let frame   = null;
  const clock = new THREE.Clock();

  function render() {
    if (!running) { frame = null; return; }
    uniforms.uTime.value = clock.getElapsedTime();
    renderer.render(scene, camera);
    frame = requestAnimationFrame(render);
  }
  function start() { if (!frame) { running = true; render(); } }
  function stop()  { running = false; }

  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) {
      entries[0].isIntersecting ? start() : stop();
    }, { threshold: 0 }).observe(host);
  } else {
    start();
  }

  document.addEventListener('visibilitychange', function () {
    document.hidden ? stop() : start();
  });

  /* Fade in after the first painted frame */
  requestAnimationFrame(function () {
    requestAnimationFrame(function () { canvas.style.opacity = dark ? '1' : '0.85'; });
  });
})();

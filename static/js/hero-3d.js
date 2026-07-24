/* ============================================================
   static/js/hero-3d.js
   ------------------------------------------------------------
   Gradient-mesh background for the homepage hero.

   Loaded ONLY on pages that contain .hero-section, and only
   after the page is interactive — so the other 15 pages never
   download Three.js.

   A shader-driven soft colour field, drifting very slowly.
   No geometry, no lights, no models: one fullscreen plane and
   a fragment shader, which is why it holds 60fps on a laptop
   GPU and costs almost nothing per frame.
   ============================================================ */

(function () {
  'use strict';

  if (typeof THREE === 'undefined') return;

  const host = document.querySelector('.hero-section');
  if (!host) return;

  /* ── Canvas, positioned behind hero content ─────────────── */
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
    transition: 'opacity 600ms cubic-bezier(0.2, 0, 0, 1)'
  });

  if (getComputedStyle(host).position === 'static') host.style.position = 'relative';
  host.insertBefore(canvas, host.firstChild);

  /* Lift hero content above the canvas */
  Array.prototype.forEach.call(host.children, function (child) {
    if (child === canvas) return;
    if (getComputedStyle(child).position === 'static') child.style.position = 'relative';
    child.style.zIndex = '1';
  });

  /* ── Palette pulled from the design tokens ──────────────── */
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

  const cBase = hexToVec(css.getPropertyValue('--surface'),     dark ? '151A21' : 'FFFFFF');
  const cWarm = hexToVec(css.getPropertyValue('--brand-tint'),  dark ? '1A2433' : 'E8EDF5');
  const cCool = hexToVec(css.getPropertyValue('--signal-high-tint'), dark ? '12271F' : 'E4F2EC');

  /* ── Scene ──────────────────────────────────────────────── */
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
    uBase:  { value: new THREE.Vector3().fromArray(cBase) },
    uWarm:  { value: new THREE.Vector3().fromArray(cWarm) },
    uCool:  { value: new THREE.Vector3().fromArray(cCool) }
  };

  const vertexShader = [
    'varying vec2 vUv;',
    'void main() {',
    '  vUv = uv;',
    '  gl_Position = vec4(position, 1.0);',
    '}'
  ].join('\n');

  const fragmentShader = [
    'precision mediump float;',
    'varying vec2 vUv;',
    'uniform float uTime;',
    'uniform vec2  uRes;',
    'uniform vec3  uBase;',
    'uniform vec3  uWarm;',
    'uniform vec3  uCool;',

    /* value noise + 3 octaves of fbm — enough for soft blobs */
    'float hash(vec2 p) {',
    '  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);',
    '}',
    'float noise(vec2 p) {',
    '  vec2 i = floor(p), f = fract(p);',
    '  vec2 u = f * f * (3.0 - 2.0 * f);',
    '  return mix(mix(hash(i + vec2(0.0,0.0)), hash(i + vec2(1.0,0.0)), u.x),',
    '             mix(hash(i + vec2(0.0,1.0)), hash(i + vec2(1.0,1.0)), u.x), u.y);',
    '}',
    'float fbm(vec2 p) {',
    '  float v = 0.0, a = 0.5;',
    '  for (int i = 0; i < 3; i++) { v += a * noise(p); p *= 2.0; a *= 0.5; }',
    '  return v;',
    '}',

    'void main() {',
    '  vec2 uv = vUv;',
    '  uv.x *= uRes.x / uRes.y;',
    '  float t = uTime * 0.035;',            /* very slow drift */
    '  float n1 = fbm(uv * 1.6 + vec2(t, t * 0.6));',
    '  float n2 = fbm(uv * 2.1 - vec2(t * 0.8, t * 0.4) + 4.0);',
    '  vec3 col = uBase;',
    '  col = mix(col, uWarm, smoothstep(0.35, 0.85, n1));',
    '  col = mix(col, uCool, smoothstep(0.45, 0.95, n2) * 0.7);',
    /* fade toward the edges so it never fights the card border */
    '  float edge = smoothstep(0.0, 0.35, vUv.y) * smoothstep(1.0, 0.65, vUv.y);',
    '  gl_FragColor = vec4(col, edge * 0.9);',
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

  /* ── Loop — paused when off-screen or tab is hidden ─────── */
  let running = true;
  let frame   = null;
  const clock = new THREE.Clock();

  function render() {
    if (!running) { frame = null; return; }
    uniforms.uTime.value = clock.getElapsedTime();
    renderer.render(scene, camera);
    frame = requestAnimationFrame(render);
  }

  function start() { if (!frame) { running = true; clock.start(); render(); } }
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

  /* Fade in once the first frame is on screen */
  requestAnimationFrame(function () {
    requestAnimationFrame(function () { canvas.style.opacity = '1'; });
  });
})();

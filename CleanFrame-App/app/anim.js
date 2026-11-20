/* CleanFrame animated backgrounds. ES5, TV-safe. Each effect draws a full
   opaque frame into ctx at size W x H for time t (seconds). State persists
   in module scope, seeded lazily on first draw so a still frame (t fixed)
   and the live loop share one look. */
(function () {
  'use strict';
  function rand(a, b) { return a + Math.random() * (b - a); }
  function hx(a) { a = Math.round(a * 255); return (a < 16 ? '0' : '') + a.toString(16); }

  /* shared starfield (seeded once) */
  var stars = null;
  function seedStars(n) {
    if (stars) return; stars = [];
    for (var i = 0; i < n; i++) stars.push({ x: Math.random(), y: Math.random(), r: rand(0.3, 1.5), p: rand(0, 6.28), s: rand(0.4, 1) });
  }

  function base(ctx, W, H, c1, c2) {
    var g = ctx.createLinearGradient(0, 0, W, H);
    g.addColorStop(0, c1); g.addColorStop(1, c2);
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  }
  function blob(ctx, W, H, x, y, r, col, a) {
    var g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, col + hx(a)); g.addColorStop(1, col + '00');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  }
  function vignette(ctx, W, H, a) {
    var g = ctx.createRadialGradient(W / 2, H * 0.44, H * 0.3, W / 2, H * 0.5, H * 1.1);
    g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,' + a + ')');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  }
  function dockShade(ctx, W, H) {
    var g = ctx.createLinearGradient(0, H * 0.58, 0, H);
    g.addColorStop(0, 'rgba(2,4,6,0)'); g.addColorStop(1, 'rgba(2,4,6,0.5)');
    ctx.fillStyle = g; ctx.fillRect(0, H * 0.58, W, H * 0.42);
  }
  function drawStars(ctx, W, H, t, tint) {
    seedStars(260);
    for (var i = 0; i < stars.length; i++) {
      var s = stars[i], tw = 0.5 + 0.5 * Math.sin(t * s.s + s.p);
      ctx.fillStyle = tint + hx(0.12 + 0.5 * tw * s.s);
      ctx.beginPath(); ctx.arc(s.x * W, s.y * H, s.r * (H / 1080), 0, 6.283); ctx.fill();
    }
  }

  /* 1) Aurora: drifting green/teal/violet curtains */
  function aurora(ctx, W, H, t) {
    base(ctx, W, H, '#05121a', '#02060a');
    drawStars(ctx, W, H, t, '#dff6ff');
    ctx.globalCompositeOperation = 'screen';
    var cols = ['#2effa6', '#19d0e6', '#7a5cff', '#2effa6'];
    for (var b = 0; b < 4; b++) {
      var baseY = H * (0.3 + 0.12 * b), amp = H * (0.07 + 0.02 * b), col = cols[b];
      ctx.beginPath(); ctx.moveTo(0, H);
      for (var x = 0; x <= W; x += W / 40) {
        var y = baseY + Math.sin(x / W * 6.283 * 1.5 + t * (0.3 + 0.08 * b) + b) * amp
              + Math.sin(x / W * 6.283 * 3.0 - t * 0.2) * amp * 0.4;
        ctx.lineTo(x, y);
      }
      ctx.lineTo(W, H); ctx.closePath();
      var g = ctx.createLinearGradient(0, baseY - amp, 0, baseY + amp * 3);
      g.addColorStop(0, col + '00'); g.addColorStop(0.35, col + '3a'); g.addColorStop(1, col + '00');
      ctx.fillStyle = g; ctx.fill();
    }
    ctx.globalCompositeOperation = 'source-over';
    vignette(ctx, W, H, 0.5); dockShade(ctx, W, H);
  }

  /* 2) Warp: gentle starfield drifting toward the viewer */
  var warpStars = null;
  function warp(ctx, W, H, t) {
    base(ctx, W, H, '#070512', '#01010a');
    if (!warpStars) { warpStars = []; for (var i = 0; i < 300; i++) warpStars.push({ a: rand(0, 6.283), r: rand(0.02, 1), z: rand(0.1, 1), c: rand(0, 1) }); }
    var cx = W / 2, cy = H * 0.46, maxR = Math.sqrt(W * W + H * H) / 2;
    ctx.globalCompositeOperation = 'screen';
    for (var j = 0; j < warpStars.length; j++) {
      var s = warpStars[j];
      s.z -= 0.0016; if (s.z <= 0.02) { s.z = 1; s.a = rand(0, 6.283); s.r = rand(0.02, 1); }
      var rad = s.r * maxR / s.z, x = cx + Math.cos(s.a) * rad, y = cy + Math.sin(s.a) * rad;
      if (x < -20 || x > W + 20 || y < -20 || y > H + 20) continue;
      var br = (1 - s.z), size = (0.4 + br * 2.2) * (H / 1080);
      var tail = br * 26 * (H / 1080);
      var px = cx + Math.cos(s.a) * (rad - tail), py = cy + Math.sin(s.a) * (rad - tail);
      var col = s.c < 0.5 ? '#bcd4ff' : '#ffffff';
      ctx.strokeStyle = col + hx(0.15 + 0.65 * br); ctx.lineWidth = size;
      ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(x, y); ctx.stroke();
    }
    ctx.globalCompositeOperation = 'source-over';
    vignette(ctx, W, H, 0.45); dockShade(ctx, W, H);
  }

  /* 3) Flow: slow-morphing nebula blobs */
  var flowBlobs = null;
  function flow(ctx, W, H, t) {
    base(ctx, W, H, '#120a1f', '#05030a');
    drawStars(ctx, W, H, t, '#efe6ff');
    if (!flowBlobs) { flowBlobs = []; var cs = ['#7a3cf0', '#19a0e6', '#e0497f', '#2fcf86'];
      for (var i = 0; i < 6; i++) flowBlobs.push({ x: rand(0.2, 0.8), y: rand(0.2, 0.7), r: rand(0.18, 0.34), c: cs[i % cs.length], px: rand(0, 6.283), py: rand(0, 6.283), sp: rand(0.05, 0.12) }); }
    ctx.globalCompositeOperation = 'screen';
    for (var b = 0; b < flowBlobs.length; b++) {
      var o = flowBlobs[b];
      var x = (o.x + 0.08 * Math.sin(t * o.sp + o.px)) * W;
      var y = (o.y + 0.06 * Math.cos(t * o.sp * 1.3 + o.py)) * H;
      blob(ctx, W, H, x, y, o.r * H, o.c, 0.1 + 0.03 * Math.sin(t * 0.4 + b));
    }
    ctx.globalCompositeOperation = 'source-over';
    vignette(ctx, W, H, 0.55); dockShade(ctx, W, H);
  }

  function glow(ctx, x, y, r, col, a) {
    var g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, col + hx(a)); g.addColorStop(1, col + '00');
    ctx.fillStyle = g; ctx.fillRect(x - r, y - r, r * 2, r * 2);
  }

  /* 4) Cosmos: mystical deep space, drifting nebulae, parallax twinkling
     stars, and shooting stars (plus rare fireballs) streaking by at random. */
  var cNeb = null, cStars = null, meteors = [], mLast = -1, mNext = 1.1;
  function seedCosmos(W, H) {
    if (cNeb) return;
    var k = H / 1080, ncol = ['#1f5ae0', '#2a86c8', '#1a3f9a', '#1f9ac0'];
    cNeb = [];
    for (var i = 0; i < 4; i++) cNeb.push({ x: rand(0.14, 0.86), y: rand(0.14, 0.76), r: rand(0.26, 0.5), c: ncol[i % ncol.length], px: rand(0, 6.28), py: rand(0, 6.28), sp: rand(0.02, 0.045), a: rand(0.04, 0.075) });
    cStars = [];
    var layers = [[200, 0.3, 0.6], [95, 0.6, 1.0], [46, 1.0, 1.7]];
    for (var L = 0; L < 3; L++) for (var s = 0; s < layers[L][0]; s++)
      cStars.push({ x: Math.random(), y: Math.random(), r: rand(layers[L][1], layers[L][2]), p: rand(0, 6.28), sp: rand(0.5, 1.7), L: L, c: Math.random() < 0.12 ? (Math.random() < 0.5 ? '#bcd0ff' : '#ffe6bc') : '#ffffff' });
    meteors.push({ x: W * 0.64, y: H * 0.30, vx: -520 * k, vy: 300 * k, len: 260 * k, life: 1, age: 0.35, col: '#ffffff', fb: false, w: 2 * k });
    meteors.push({ x: W * 0.30, y: H * 0.16, vx: 600 * k, vy: 360 * k, len: 420 * k, life: 2.2, age: 0.9, col: '#ffd9a0', fb: true, w: 3.2 * k });
  }
  function spawnMeteor(W, H) {
    var k = H / 1080, fb = Math.random() < 0.14;
    var dx = (Math.random() < 0.5 ? -1 : 1) * rand(0.4, 1), dy = rand(0.35, 0.9), m = Math.sqrt(dx * dx + dy * dy); dx /= m; dy /= m;
    var sp = (fb ? rand(330, 520) : rand(700, 1150)) * k;
    var x = dx < 0 ? rand(0.4, 1.12) * W : rand(-0.12, 0.6) * W, y = rand(-0.05, 0.4) * H;
    var len = (fb ? rand(260, 440) : rand(130, 300)) * k, life = fb ? rand(1.8, 2.8) : rand(0.55, 1.05);
    var col = fb ? (Math.random() < 0.5 ? '#ffd9a0' : '#a6dcff') : (Math.random() < 0.7 ? '#ffffff' : (Math.random() < 0.5 ? '#c3d6ff' : '#ffe6c0'));
    meteors.push({ x: x, y: y, vx: dx * sp, vy: dy * sp, len: len, life: life, age: 0, col: col, fb: fb, w: (fb ? rand(2.6, 3.8) : rand(1.2, 2.2)) * k });
  }
  function cosmos(ctx, W, H, t) {
    seedCosmos(W, H);
    var k = H / 1080, dt = (mLast < 0 || t < mLast || t - mLast > 0.5) ? 0.016 : (t - mLast); mLast = t;
    base(ctx, W, H, '#04060f', '#010103');
    ctx.globalCompositeOperation = 'screen';
    glow(ctx, W * 0.5, H * 0.42, H * 0.95, '#102236', 0.32);
    for (var i = 0; i < cNeb.length; i++) {
      var o = cNeb[i], nx = (o.x + 0.05 * Math.sin(t * o.sp + o.px)) * W, ny = (o.y + 0.04 * Math.cos(t * o.sp * 1.2 + o.py)) * H;
      blob(ctx, W, H, nx, ny, o.r * H, o.c, o.a * (0.8 + 0.2 * Math.sin(t * 0.3 + i)));
    }
    ctx.globalCompositeOperation = 'source-over';
    var drift = t * 5 * k;
    for (var j = 0; j < cStars.length; j++) {
      var s = cStars[j], tw = 0.45 + 0.55 * Math.sin(t * s.sp + s.p);
      var px = s.x * W + (s.L * drift * 0.1) % W; if (px > W) px -= W;
      var py = s.y * H, rr = s.r * k;
      ctx.fillStyle = s.c + hx(0.1 + 0.6 * tw * (0.4 + 0.3 * s.L));
      ctx.beginPath(); ctx.arc(px, py, rr, 0, 6.283); ctx.fill();
      if (s.L === 2 && s.r > 1.35 && tw > 0.88) {
        ctx.strokeStyle = s.c + '55'; ctx.lineWidth = 0.6 * k; var gg = rr * 3.2;
        ctx.beginPath(); ctx.moveTo(px - gg, py); ctx.lineTo(px + gg, py); ctx.moveTo(px, py - gg); ctx.lineTo(px, py + gg); ctx.stroke();
      }
    }
    mNext -= dt;
    if (mNext <= 0) { spawnMeteor(W, H); mNext = Math.random() < 0.28 ? rand(0.2, 0.6) : rand(0.9, 2.8); }
    ctx.globalCompositeOperation = 'screen'; ctx.lineCap = 'round';
    for (var q = meteors.length - 1; q >= 0; q--) {
      var mt = meteors[q]; mt.x += mt.vx * dt; mt.y += mt.vy * dt; mt.age += dt;
      var life = 1 - mt.age / mt.life;
      if (life <= 0 || mt.x < -220 || mt.x > W + 220 || mt.y > H + 220) { meteors.splice(q, 1); continue; }
      var msp = Math.sqrt(mt.vx * mt.vx + mt.vy * mt.vy), tx = mt.x - mt.vx / msp * mt.len, ty = mt.y - mt.vy / msp * mt.len;
      var gr = ctx.createLinearGradient(mt.x, mt.y, tx, ty);
      gr.addColorStop(0, mt.col + hx(0.9 * life)); gr.addColorStop(0.4, mt.col + hx(0.3 * life)); gr.addColorStop(1, mt.col + '00');
      ctx.strokeStyle = gr; ctx.lineWidth = mt.w; ctx.beginPath(); ctx.moveTo(mt.x, mt.y); ctx.lineTo(tx, ty); ctx.stroke();
      glow(ctx, mt.x, mt.y, (mt.fb ? 30 : 15) * k, mt.col, 0.75 * life);
      if (mt.fb) glow(ctx, mt.x, mt.y, 72 * k, mt.col, 0.22 * life);
    }
    ctx.globalCompositeOperation = 'source-over';
    vignette(ctx, W, H, 0.5); dockShade(ctx, W, H);
  }

  window.CleanFrameAnims = { aurora: aurora, warp: warp, flow: flow, cosmos: cosmos };
}());

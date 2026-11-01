document.getElementById("year").textContent = new Date().getFullYear();

// Bubbles rise from the bottom of the screen; the deeper you scroll, the smaller they get.
(function () {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var canvas = document.createElement("canvas");
  canvas.className = "bubbles";
  canvas.setAttribute("aria-hidden", "true");
  document.body.appendChild(canvas);
  var ctx = canvas.getContext("2d");

  var vars = getComputedStyle(document.documentElement);
  var stroke = vars.getPropertyValue("--sage-deep").trim() || "#6f8c47";
  var fill = vars.getPropertyValue("--sage").trim() || "#cbda93";

  var w = 0, h = 0, bubbles = [], pops = [], kick = 0, lastY = window.scrollY, last = performance.now();
  var mx = -999, my = -999;

  function depth() {
    var max = document.documentElement.scrollHeight - window.innerHeight;
    return max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0;
  }

  function resize() {
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = window.innerWidth;
    h = window.innerHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function make(initial) {
    var r = 3 + Math.pow(Math.random(), 2.2) * 34;
    return {
      x: Math.random() * w,
      y: initial ? Math.random() * h : h + r + Math.random() * 60,
      r: r,
      speed: 0.25 + r / 45 + Math.random() * 0.3,
      freq: 0.4 + Math.random() * 0.9,
      sway: 6 + Math.random() * 16,
      phase: Math.random() * Math.PI * 2,
      ring: Math.random() < 0.5
    };
  }

  function init() {
    resize();
    var count = w < 700 ? 7 : 13;
    bubbles = [];
    for (var i = 0; i < count; i++) bubbles.push(make(true));
  }

  function frame(now) {
    var dt = Math.min(48, now - last) / 16.67;
    last = now;
    kick *= Math.pow(0.93, dt);
    var scale = 1 - 0.65 * depth();
    ctx.clearRect(0, 0, w, h);

    for (var i = 0; i < bubbles.length; i++) {
      var b = bubbles[i];
      b.y -= (b.speed + kick) * dt;
      var x = b.x + Math.sin(now / 1000 * b.freq + b.phase) * b.sway;
      var r = b.r * scale;
      if (b.y + r < -10) { bubbles[i] = make(false); continue; }

      var dx = mx - x, dy = my - b.y;
      if (dx * dx + dy * dy < (r + 4) * (r + 4)) {
        pops.push({ x: x, y: b.y, r: r, age: 0, ring: b.ring });
        bubbles[i] = make(false);
        continue;
      }

      ctx.beginPath();
      ctx.arc(x, b.y, r, 0, Math.PI * 2);
      if (b.ring) {
        ctx.lineWidth = 1.3;
        ctx.strokeStyle = stroke;
        ctx.globalAlpha = 0.5;
        ctx.stroke();
      } else {
        ctx.fillStyle = fill;
        ctx.globalAlpha = 0.5;
        ctx.fill();
      }
      if (r > 8) {
        ctx.beginPath();
        ctx.arc(x, b.y, r * 0.68, Math.PI * 1.1, Math.PI * 1.45);
        ctx.lineWidth = 1.2;
        ctx.strokeStyle = b.ring ? stroke : "#ffffff";
        ctx.globalAlpha = 0.55;
        ctx.stroke();
      }
    }

    // A popped bubble: a ring that swells and fades, with a few droplets flung outward.
    for (var j = pops.length - 1; j >= 0; j--) {
      var p = pops[j];
      p.age += dt / 20;
      if (p.age >= 1) { pops.splice(j, 1); continue; }
      var ease = 1 - Math.pow(1 - p.age, 3);
      ctx.globalAlpha = 0.6 * (1 - p.age);
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 1.3;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r * (1 + 0.5 * ease), 0, Math.PI * 2);
      ctx.stroke();
      ctx.fillStyle = p.ring ? stroke : fill;
      for (var k = 0; k < 7; k++) {
        var a = k * (Math.PI * 2 / 7) + p.r;
        var d = p.r * (0.9 + 1.1 * ease);
        ctx.beginPath();
        ctx.arc(p.x + Math.cos(a) * d, p.y + Math.sin(a) * d, Math.max(0.8, p.r * 0.12 * (1 - p.age)), 0, Math.PI * 2);
        ctx.fill();
      }
    }
    ctx.globalAlpha = 1;
    requestAnimationFrame(frame);
  }

  function track(e) { mx = e.clientX; my = e.clientY; }
  window.addEventListener("pointermove", track, { passive: true });
  window.addEventListener("pointerdown", track, { passive: true });
  document.addEventListener("pointerleave", function () { mx = my = -999; });
  window.addEventListener("pointerup", function (e) { if (e.pointerType !== "mouse") mx = my = -999; });

  window.addEventListener("scroll", function () {
    var y = window.scrollY;
    kick = Math.max(-2.5, Math.min(9, kick + (y - lastY) * 0.04));
    lastY = y;
  }, { passive: true });
  window.addEventListener("resize", init);

  init();
  requestAnimationFrame(frame);
})();

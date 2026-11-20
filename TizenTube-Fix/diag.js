(function () {
  var buf = [];
  function txt(a) { if (typeof a === 'string') return a; try { return JSON.stringify(a).slice(0, 300); } catch (e) { return String(a); } }
  function add(kind, args) {
    try {
      var s = kind + ' ' + Array.prototype.map.call(args, txt).join(' ');
      buf.push(new Date().toTimeString().slice(0, 8) + ' ' + s.slice(0, 500));
      if (buf.length > 500) buf.splice(0, buf.length - 500);
    } catch (e) {}
  }
  ['info', 'warn', 'error', 'log'].forEach(function (k) {
    var orig = console[k];
    console[k] = function () {
      if (k !== 'log' || /sponsor|hashchange|segment|skip/i.test(txt(arguments[0]))) add(k.toUpperCase(), arguments);
      return orig.apply(console, arguments);
    };
  });
  window.addEventListener('error', function (e) { add('ERR', [e.message, e.filename, e.lineno]); });
  window.addEventListener('unhandledrejection', function (e) { add('REJ', [e.reason && (e.reason.stack || e.reason.message || String(e.reason))]); });
  var last = '', tick = 0;
  setInterval(function () {
    try {
      var vs = document.querySelectorAll('video');
      var v = Array.prototype.map.call(vs, function (x, i) { return i + ':' + (x.paused ? 'P' : 'L') + (x.src ? ' src' : '') + ' ' + x.offsetWidth + 'x' + x.offsetHeight; }).join(' | ');
      var sb = window.sponsorblock;
      var s = sb ? (sb.videoID + ' seg=' + (sb.segments ? sb.segments.length : '-') + ' bound=' + (sb.video ? Array.prototype.indexOf.call(vs, sb.video) : '-') + ' active=' + sb.active + ' skip=' + JSON.stringify(sb.skippableCategories)) : 'null';
      var now = 'hash=' + location.hash + ' videos=[' + v + '] sb=' + s;
      if (now !== last) { add('STATE', [now]); last = now; }
      if (++tick % 10 === 0 && vs.length) add('TIME', [Array.prototype.map.call(vs, function (x) { return Math.round(x.currentTime) + '/' + Math.round(x.duration); }).join(' | ')]);
    } catch (e) { add('DIAGERR', [String(e)]); }
  }, 1000);
  setInterval(function () {
    if (!buf.length) return;
    var out = buf.splice(0, buf.length);
    try { var x = new XMLHttpRequest(); x.open('POST', '/__ttlog'); x.setRequestHeader('content-type', 'application/json'); x.send(JSON.stringify(out)); } catch (e) {}
  }, 2000);
  add('DIAG', ['geladen', location.href, navigator.userAgent]);
})();

"""FAH-Patch für TizenTube Cobalt 2.1.1 (Dienst service/dist/index.js).

Behebt: SponsorBlock liest die Video-ID aus location.hash per .search.replace("?v=","").split("&")[0].
Beim Start über DIAL/Dock lautet der Hash #/watch?&launch=dial&v=<ID> -> ID wird "?" und bleibt es,
also wird nie wieder abgefragt (upstream reisxd/TizenTube #730). Der Dienst liefert das Skript jetzt
selbst unter https://www.youtube.com/__tt/userScript.js aus (MITM-Ursprung) und ersetzt den Ausdruck.
Fehlt das Muster (z. B. weil upstream repariert hat), geht das Skript unverändert durch.
Aufruf: patch2.py <index.js> [diag.js]  (mit diag.js: Protokoll unter http://<TV>:8101/__ttlog)
"""
import json, sys, pathlib
quelle = pathlib.Path(sys.argv[1])
diag = pathlib.Path(sys.argv[2]).read_text(encoding='utf-8') if len(sys.argv) > 2 else ''
s = quelle.read_text(encoding='utf-8')

def ersetze(alt, neu):
    global s
    assert s.count(alt) == 1, ('nicht eindeutig', alt[:80], s.count(alt))
    s = s.replace(alt, neu)

US = 'https://cdn.jsdelivr.net/npm/@foxreis/tizentube/dist/userScript.js'
ersetze("  var ytCertWWW = createHostCertificate('www.youtube.com');",
"""  var ttLog = [];
  var TT_DIAG = %s;
  var ttCache = null;
  var TT_US = '%s';
  var TT_MUSTER = /new URL\\(location\\.hash\\.substring\\(1\\),location\\.href\\)\\.search\\.replace\\("\\?v=",""\\)\\.split\\("&"\\)\\[0\\]/g;
  var TT_ERSATZ = '((location.hash.match(/[?&]v=([\\\\w-]{11})/)||[])[1]||"")';
  function ttMerke(z) { ttLog.push(new Date().toTimeString().slice(0, 8) + ' ' + z); if (ttLog.length > 5000) ttLog.splice(0, ttLog.length - 5000); }
  function ttUserScript(fertig) {
    if (ttCache && Date.now() - ttCache.t < 30 * 60 * 1000) return fertig(ttCache.text);
    var mod = parseInt(process.version.split('.')[0].replace('v', '')) >= 13 ? ogHttps : https;
    var erledigt = false;
    function ende(text) { if (!erledigt) { erledigt = true; fertig(text); } }
    var req = mod.get(TT_US + '?ver=' + Date.now(), function (res) {
      if (res.statusCode !== 200) { res.resume(); ttMerke('PATCH jsdelivr ' + res.statusCode); return ende(null); }
      var teile = [];
      res.on('data', function (c) { teile.push(c); });
      res.on('end', function () {
        var text = Buffer.concat(teile).toString('utf8');
        var n = (text.match(TT_MUSTER) || []).length;
        text = text.replace(TT_MUSTER, function () { return TT_ERSATZ; });
        ttMerke('PATCH userScript ' + text.length + ' B, Video-ID-Korrektur ' + n + 'x');
        ttCache = { t: Date.now(), text: text };
        ende(text);
      });
      res.on('error', function () { ende(null); });
    });
    req.on('error', function (e) { ttMerke('PATCH Fehler ' + e.message); ende(null); });
    req.setTimeout(15000, function () { req.destroy(); });
  }
  var ytCertWWW = createHostCertificate('www.youtube.com');""" % (json.dumps(diag), US))

ersetze("        var isTvPath = request.url === '/tv' || request.url.startsWith('/tv?');",
"""        if (request.url.indexOf('/__tt/userScript.js') === 0) {
          return ttUserScript(function (text) {
            if (text === null) { response.writeHead(302, { location: TT_US + '?ver=' + Date.now() }); return response.end(); }
            response.writeHead(200, { 'content-type': 'application/javascript; charset=utf-8', 'cache-control': 'no-store', 'content-length': Buffer.byteLength(text, 'utf8') });
            response.end(text);
          });
        }
        if (TT_DIAG && request.url.indexOf('/__ttlog') === 0) {
          var ttb = [];
          request.on('data', function (c) { ttb.push(c); });
          request.on('end', function () {
            try { JSON.parse(Buffer.concat(ttb).toString('utf8')).forEach(function (l) { ttLog.push(String(l)); }); if (ttLog.length > 5000) ttLog.splice(0, ttLog.length - 5000); } catch (e) {}
            response.writeHead(204); response.end();
          });
          return;
        }
        var isTvPath = request.url === '/tv' || request.url.startsWith('/tv?');""")

ersetze("            body = body.replace('</body>', `<script src=\"https://cdn.jsdelivr.net/npm/@foxreis/tizentube/dist/userScript.js?ver=${Date.now()}\"></script></body>`);",
        "            body = body.replace('</body>', function () { return (TT_DIAG ? '<script>' + TT_DIAG + '</script>' : '') + '<script src=\"/__tt/userScript.js?ver=' + Date.now() + '\"></script></body>'; });")

ersetze("  var proxyServer = http.createServer(function (request, response) {\n    var targetUrl = url.parse(request.url);",
"""  var proxyServer = http.createServer(function (request, response) {
    if (TT_DIAG && request.url.indexOf('/__ttlog') === 0) {
      if (request.url.indexOf('clear') > 0) ttLog.length = 0;
      response.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' });
      return response.end(ttLog.join('\\n') + '\\n');
    }
    var targetUrl = url.parse(request.url);""")
quelle.write_text(s, encoding='utf-8')
print('gepatcht', 'mit Diagnose' if diag else 'ohne Diagnose')

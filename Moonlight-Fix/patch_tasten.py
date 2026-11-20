#!/usr/bin/env python3
"""FAH-Patch für Moonlight-tizen 1.20.0 (brightcraft): Esc der Tastatur im Spiel.

Der Samsung meldet die Esc-Taste einer Tastatur als Zurück-Taste der Fernbedienung (keyCode 10009,
Samsung-Doku „Keyboard/IME“, Tabelle 5) und schickt das keyup 2-6 ms nach dem keydown, egal wie
lange die Taste gehalten wird (gemessen 08.11.2026). Moonlight sandte Esc als Druck+Loslassen im
selben Moment, das verpassen Spiele wie StarRupture (Unreal). Der Patch fängt Esc in der
Capture-Phase am window ab, egal wo der Fokus liegt, und hält Esc 150 ms gedrückt.
Backspace kommt am TV normal an (keyCode 8, echte Haltezeit) und bleibt auf dem nativen Weg.

Aufruf: python3 patch_tasten.py <entpackter-wgt-ordner>/platform/index.js [diag-url]
Mit diag-url (z. B. http://192.168.1.23:8799/k) werden Sondertasten (keine Buchstaben) dorthin
gemeldet – nur zur Fehlersuche, danach ohne diag-url neu bauen.
"""
import sys

ALT = """  // Listen for keydown events on the video element
  videoElement.addEventListener('keydown', function(e) {
    // Check if the 'Back' key has been pressed and the streaming is currently active
    if (e.key === 'XF86Back' && isInGame === true) {
      // Send the Escape key (ESC) to the host while streaming
      sendEscapeKeyToHost();
      // Simulate mouse to move focus back to the streaming session
      videoElement.dispatchEvent(new MouseEvent('mousedown', {
        bubbles: true, cancelable: true, view: window, clientX: 0, clientY: 0
      }));
    }
  });
}"""

NEU = """  // FAH-Patch: Esc (am TV = Zurück-Taste 10009) immer an den PC, unabhängig vom Fokus. Der TV schickt
  // das keyup 2-6 ms nach dem keydown, egal wie lange die Taste gehalten wird; so kurze Drücke verpassen
  // Spiele, die die Tasten einmal pro Bild abfragen (Unreal). Deshalb Esc 150 ms gehalten senden.
  // Der native keydown-Weg bekäme 10009 & 0xFF = VK 0x19 (Kanji) und wird hier unterdrückt.
  var fahEscTimer = null;
  function fahIstEsc(e) {
    return e.keyCode === 10009 || e.key === 'XF86Back' || e.keyCode === 27 || e.key === 'Escape' || e.code === 'Escape';
  }
  function fahSende(aktion) {
    try { Module.sendKeyboardEvent(0x1B, aktion, 0); } catch (x) { /*FAH-DIAG-FEHLER*/ }
  }
  function fahWeiter(e) {
    /*FAH-DIAG*/
    if (isInGame !== true || !fahIstEsc(e)) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    if (e.type !== 'keydown') return;
    if (fahEscTimer) { clearTimeout(fahEscTimer); } else { fahSende(0x03); }
    fahEscTimer = setTimeout(function() { fahEscTimer = null; fahSende(0x04); }, 150);
  }
  window.addEventListener('keydown', fahWeiter, true);
  window.addEventListener('keyup', fahWeiter, true);
}"""

DIAG = """if (e.keyCode === 8 || e.keyCode === 27 || e.keyCode >= 10000 || (e.key && e.key.length > 1)) {
      try { fetch('%s', { method: 'POST', mode: 'no-cors', body: [e.type, e.key, e.code, e.keyCode, 'spiel=' + isInGame, 'fokus=' + (document.activeElement && document.activeElement.id)].join(' ') }); } catch (x) {}
    }"""

pfad = sys.argv[1]
s = open(pfad, encoding='utf-8').read()
if ALT not in s:
    sys.exit('Muster nicht gefunden – andere Moonlight-Version?')
DIAG_FEHLER = "try { fetch('%s', { method: 'POST', mode: 'no-cors', body: 'FEHLER sendKeyboardEvent ' + x }); } catch (y) {}"
url = sys.argv[2] if len(sys.argv) > 2 else None
neu = NEU.replace('/*FAH-DIAG*/', DIAG % url if url else '').replace('/*FAH-DIAG-FEHLER*/', DIAG_FEHLER % url if url else '')
open(pfad, 'w', encoding='utf-8').write(s.replace(ALT, neu))
print('gepatcht' + (' mit Diagnose' if len(sys.argv) > 2 else ''))

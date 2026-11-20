# Samsung Tizen TV

Anpassungen für den Samsung **QE55Q70CATXZT** (Q70C, Tizen 9.0, IP 192.168.1.75).
Stand 07.11.2026. Alle TV-Schritte laufen über den Entwicklermodus (am TV aktiv)
und einen Docker-Container auf dem NAS 192.168.1.23.

## Home-Umstellung/  — CleanFrame als Startbildschirm
Macht Home-Taste, Standby-An und Kaltstart zu CleanFrame. Jederzeit umkehrbar.
- Umstellen:   `python3 "Home-Umstellung/cf-home.py" apply`
- Zurück auf Samsung:  `python3 "Home-Umstellung/cf-home.py" restore`
- Zustand lesen:  `python3 "Home-Umstellung/cf-home.py" query`
- In Claude Code immer per `!` starten.
- `cfbuild/Control.cs` = .NET-6-Helfer (Firmware-Guard T-NKM2CDEUC-0090-2220.4).
- `cfbuild/original.json` = Rückweg-Sicherung (alles auf com.samsung.tv.csfs, auto_start=1).
- `cf-check.py` = reiner Lese-Check (verändert nichts).
- `wrapper` / `wrapper-off` = Home-Taste auf die Wrapper-Mini-App (Home-Wrapper/) bzw. zurück direkt auf CleanFrame. Behebt den „zwei Klicks"-Effekt (Tizen `__NO_RAISE_WINDOW`).
- Kaltstart dauert jetzt ~0,7 s (Wallpaper auf 1080p verkleinert, Schriften sofort). Standby ist sofort.

## Home-Wrapper/  — Mini-App für einen Klick auf die Home-Taste
Tizen startet die Home-App über `__NO_RAISE_WINDOW`, wodurch ein direkt als `home_appid` registrierter Launcher hinter dem Ladescreen hängenbleibt (man müsste zweimal drücken). Darum zeigt `home_appid` auf diese winzige App (`cfkeyHome1.key`), die CleanFrame normal (mit Vordergrund) startet und sich erst beendet, wenn CleanFrame wirklich vorne ist (sonst Kaltstart-Loop).
- Setzen: `python3 "Home-Umstellung/cf-home.py" wrapper`  ·  zurück: `… wrapper-off`.
- Package-ID muss **exakt 10 Zeichen** sein (`cfkeyHome1`), sonst „Load archive info fail".
- Bauen/Installieren wie CleanFrame (Signierung im NAS-Container, `Moonlight/cf-install.js`).

## CleanFrame-App/  — der Startbildschirm selbst
Angepasster CleanFrame-Quellcode (nthnclrk/CleanFrame, MIT) mit den 5 Apps
waipu.tv, YouTube, Plex, Prime Video, Moonlight + eigene weiße Logos.
- `CleanFrame.wgt` = fertig gebautes Paket (unsigniert; vor Installation mit
  Samsung-Zertifikat signieren, siehe Moonlight-Weg / NAS-Volume moonlight-config).
- Browser-Test: `python3 -m http.server` im Ordner `app/`, dann die Seite öffnen.

## Moonlight/  — Spiele-Streaming vom Kinder-PC
- `tvkey.py` = TV per Netzwerk fernsteuern (Tasten, Power). Token in `tv-token.txt`.
- `cf-install.js` = Moonlight signieren + installieren (im NAS-Container).
- `appid.js` = App-ID/Version aus einem .wgt lesen.
- App am TV: `MoonLightS.MoonlightWasm`. Host in Moonlight: 192.168.1.143:40989.

## App-IDs am Fernseher
- waipu.tv  `ndmbVBabXx.WaipuTV`
- YouTube   `9Ur5IzDKqV.TizenYouTube`
- Plex      `kIciSQlYEM.plex`
- Prime     `org.tizen.primevideo`
- Moonlight `MoonLightS.MoonlightWasm`

## Moonlight-Fix/  — Esc-Taste der Tastatur im Spiel (08.11.2026)
- Der TV meldet Esc als Zurück-Taste mit 2-6 ms Druck; Spiele verpassten ihn. Patch hält Esc
  150 ms. Bauweg, Messwerte und Rückweg in `LIESMICH.txt`.

## Tessel/  — Medienplayer für die NAS-Freigabe (08.11.2026)
- Tessel 1.35.0 (PatrickSt1991/tessel-tizen-tv, MIT): spielt SMB/DLNA/USB direkt
  über den TV-Decoder, App-ID `madebypatk.vlcweb`. Bauweg + Update in `LIESMICH.txt`.

## TizenTube-Fix/  — SponsorBlock-Reparatur (07.11.2026)
- `TizenTube-fix.wgt` = TizenTube Cobalt 2.1.1 mit FAH-Patch: Video-ID wird auch bei
  `#/watch?&launch=dial&v=…` richtig erkannt (upstream #730). Details + Bauweg in `LIESMICH.txt`.
- Rückweg: `Moonlight/TizenTubeCobalt.wgt` (Original) installieren.

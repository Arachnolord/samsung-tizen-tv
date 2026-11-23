# Samsung Tizen TV

Eine Sammlung eigener Anpassungen für einen Samsung-Fernseher mit **Tizen**:
ein eigener Startbildschirm (CleanFrame), die Umstellung der Home-Taste darauf,
Spiele-Streaming per Moonlight (inkl. Fix für die Esc-Taste), ein Medienplayer
(Tessel) und ein SponsorBlock-Fix für TizenTube.

Alle Pakete werden mit einem **Samsung-Signierzertifikat** signiert und über die
offene **Entwickler-Verbindung (sdb)** des Fernsehers installiert. Der Signier-
und Installationsvorgang läuft in einem Docker-Container, der auf einem beliebigen
Rechner im selben Netz liegen kann (bei der Entwicklung war das ein NAS).

> **Getestet auf:** Samsung **QE55Q70CATXZT** (Q70C), Tizen 9.0.
> Andere Modelle können abweichen – gerade die Home-Umstellung ist stark
> modell- und firmwareabhängig.

---

## ⚠️ Bitte zuerst lesen – Risiko

Dies ist die Dokumentation eines Experiments am **eigenen** Gerät, keine Empfehlung,
deinen Fernseher zu verändern. **Auf eigene Gefahr.**

- Entwicklermodus und das Installieren fremder Pakete sind von Samsung nicht als
  Dauerbetrieb vorgesehen.
- Die **Home-/Startbildschirm-Umstellung** schreibt in undokumentierte System-
  einstellungen. Das kann Home/Start vorübergehend unbrauchbar machen.
- **Firmware-Updates** können den Weg und die Rücksetz-Werkzeuge jederzeit brechen.
- Eine gespeicherte Rücksetzung ist **keine Garantie** auf Wiederherstellung.

Du brauchst dein **eigenes Samsung-Konto, eigene Signierzertifikate und eine eigene
App-Identität**. Übernimm keine fremden Zertifikate oder App-IDs.

---

## Überblick der Bausteine

| Ordner | Was es ist | Quelle / Lizenz |
|---|---|---|
| `CleanFrame-App/` | Eigener Startbildschirm (Dock mit Apps) | nthnclrk/CleanFrame, MIT (angepasst) |
| `Home-Umstellung/` | Macht Home-Taste, Standby-An und Kaltstart zu CleanFrame | eigen |
| `Home-Wrapper/` | Mini-App, damit die Home-Taste mit **einem** Druck wirkt | eigen |
| `Moonlight/` | Spiele-Streaming vom PC + TV-Fernsteuerung | moonlight-tizen; Skripte eigen |
| `Moonlight-Fix/` | Patch: Esc-Taste der Tastatur kommt im Spiel an | eigen auf moonlight-tizen |
| `Tessel/` | Medienplayer für Netzwerk-/USB-Medien | PatrickSt1991/tessel-tizen-tv, MIT |
| `TizenTube-Fix/` | Repariert SponsorBlock in TizenTube | eigen auf TizenTube Cobalt |

---

## Voraussetzungen

- Ein **Samsung-TV mit Tizen 5.0 oder neuer**. Die Home-Umstellung gelingt nur auf
  einem Teil der Geräte (siehe `CleanFrame-App/docs/compatibility.md`).
- Der **Entwicklermodus** des Fernsehers ist eingeschaltet (Schritt 1).
- Ein **Rechner mit Docker** im selben lokalen Netz wie der Fernseher
  (im Beispiel ein NAS). TV und Rechner müssen sich gegenseitig erreichen.
- Ein **Samsung-Signierzertifikat** in einem Docker-Volume `moonlight-config`
  (Schritt 2). Es wird einmalig angelegt und danach wiederverwendet.
- Grundlagen: Terminal/SSH auf dem Docker-Host, Umgang mit `docker`-Befehlen.

### Platzhalter in dieser Anleitung

Ersetze diese Platzhalter überall durch deine eigenen Werte:

| Platzhalter | Bedeutung |
|---|---|
| `<TV-IP>` | Lokale IP-Adresse deines Fernsehers, z. B. `192.168.1.75` |
| `<HOST-IP>` | Lokale IP des Rechners mit Docker, z. B. `192.168.1.50` |
| `<PC-IP>` | Lokale IP des Spiele-PCs (nur für Moonlight), z. B. `192.168.1.60` |

Die mitgelieferten Installationsskripte (`*-install.js`) haben die TV-Adresse oben
als Konstante `const TV = '…'`. **Trage dort deine `<TV-IP>` ein**, bevor du sie
startest.

---

## Schritt 1 – Entwicklermodus am Fernseher einschalten

1. Am TV **Smart Hub → Apps** öffnen.
2. Auf der Fernbedienung die Ziffern **1 2 3 4 5** eingeben. Es öffnet sich ein
   kleines Fenster „Developer mode".
3. Entwicklermodus auf **On** stellen und als **Host-PC-IP** die **`<HOST-IP>`**
   (den Docker-Host) eintragen, bestätigen.
4. Den Fernseher **neu starten** (aus- und einschalten).

Danach lauscht der Fernseher auf dem sdb-Port **26101**. Menüwortlaut und genaue
Schritte können je nach Modelljahr abweichen.

---

## Schritt 2 – Installer-Container und Zertifikat

Signieren und Installieren übernimmt der Moonlight-Tizen-Installer (SmookeyDev) in
einem Container. Das Samsung-Zertifikat liegt in einem **dauerhaften Volume**
`moonlight-config` und wird **einmalig** angelegt.

```sh
# Auf dem Docker-Host:
docker run -d --name moonlight-installer \
  -v moonlight-config:/root/share \
  ghcr.io/smookeydev/moonlighttizeninstaller:latest
```

Beim ersten Einrichten legst du über den Installer ein **Samsung-Zertifikat** an
(dazu sind ein Samsung-Konto und die **DUID** deines Fernsehers nötig). Es wird im
Volume `moonlight-config` gespeichert. Alle Skripte dieses Repos lesen das
Zertifikat von dort – ist es einmal vorhanden, brauchst du es nicht erneut
anzulegen. Lass das Volume bestehen; den Container selbst kannst du nach getaner
Arbeit löschen.

> Halte Zertifikate, Passwörter und Konto-Daten in privatem, lokalem Speicher.
> Melde dich bei Samsung selbst an – kein Skript braucht deine Zugangsdaten.

---

## Schritt 3 – Verbindung zum Fernseher prüfen

Der Installer-Container bringt `sdb` mit. Test:

```sh
docker exec moonlight-installer sh -c "sdb connect <TV-IP>:26101 && sdb devices"
```

Erscheint der Fernseher in der Liste, steht die Verbindung. Wenn nicht: Schritt 1
prüfen (Entwicklermodus an? richtige `<HOST-IP>`? TV neu gestartet?) und dass TV und
Host im selben Netz sind.

---

## Schritt 4 – Der allgemeine Ablauf: bauen → signieren → installieren

Alle Apps hier folgen demselben Muster. Am Beispiel von Tessel:

1. **IP eintragen:** In `Tessel/tessel-install.js` oben `const TV = '<TV-IP>'` setzen.
2. **Dateien in den Container kopieren:**
   ```sh
   docker exec -i moonlight-installer sh -c "cat > /tmp/tessel.wgt"        < Tessel/tessel-1.35.0.wgt
   docker exec -i moonlight-installer sh -c "cat > /tmp/tessel-install.js" < Tessel/tessel-install.js
   ```
3. **Signieren + installieren:**
   ```sh
   docker exec moonlight-installer node /tmp/tessel-install.js
   ```
   Das Skript signiert das `.wgt` mit dem Zertifikat aus `moonlight-config`, lädt es
   per sdb auf den Fernseher und installiert es.
4. **Aufräumen:** Container (und bei Bedarf das Image) wieder entfernen, **Volume
   `moonlight-config` behalten**.

Die einzelnen `LIESMICH.txt` je Ordner nennen Besonderheiten, SHA256-Summen und den
jeweiligen Rückweg.

---

## Die Bausteine im Einzelnen

### CleanFrame-App/ — der Startbildschirm
Angepasster CleanFrame-Quellcode (nthnclrk/CleanFrame, MIT) mit fünf Apps
(waipu.tv, YouTube, Plex, Prime Video, Moonlight) und eigenen weißen Logos.

- `CleanFrame.wgt` = fertiges Paket (unsigniert – vor der Installation signieren,
  siehe Schritt 4 mit `Moonlight/cf-install.js`).
- Vorschau im Browser ohne Fernseher: im Ordner `app/` `python3 -m http.server`
  starten und die Seite öffnen (Pfeiltasten, Enter, Escape).

### Moonlight/ — Spiele-Streaming vom PC
Streamt Spiele von einem PC mit Sunshine/Apollo auf den Fernseher.

- App-ID am TV: `MoonLightS.MoonlightWasm`.
- Host in Moonlight eintragen: `<PC-IP>` (Standardport des Streaming-Servers).
- `tvkey.py` / `tv.mjs` = Fernseher per Netzwerk fernsteuern (Tasten, Power).
  TV-IP oben im Skript eintragen; das Kopplungs-Token wird in `tv-token.txt`
  abgelegt (nicht eingecheckt).
- `cf-install.js`, `appid.js` = Hilfsskripte zum Installieren bzw. zum Auslesen der
  App-ID/Version aus einem `.wgt`.

### Moonlight-Fix/ — Esc-Taste im Spiel
Der Fernseher meldet Esc als Zurück-Taste mit nur 2–6 ms Druck; Spiele verpassen
ihn dann. Der Patch hält Esc 150 ms. Bauweg, Messwerte und Rückweg in
`Moonlight-Fix/LIESMICH.txt`.

### Tessel/ — Medienplayer
Tessel 1.35.0 (PatrickSt1991/tessel-tizen-tv, MIT) spielt SMB/DLNA/USB direkt über
den Decoder des Fernsehers, App-ID `madebypatk.vlcweb`. Details in
`Tessel/LIESMICH.txt`.

### TizenTube-Fix/ — SponsorBlock reparieren
`TizenTube-fix.wgt` = TizenTube Cobalt 2.1.1 mit einem Patch, der die Video-ID auch
bei `#/watch?&launch=dial&v=…` richtig erkennt (Upstream-Problem #730). Rückweg: das
Original aus `Moonlight/TizenTubeCobalt.wgt` genauso installieren. Details in
`TizenTube-Fix/LIESMICH.txt`.

---

## Home-Umstellung — CleanFrame als Startbildschirm

> **Fortgeschritten und modellabhängig.** Schreibt in undokumentierte System-
> einstellungen. Nur mit funktionierendem Rückweg (`restore`) durchführen und
> jemandem, der auf den Bildschirm sieht. Auf eigene Gefahr.

`Home-Umstellung/cf-home.py` macht Home-Taste, Standby-An und Kaltstart zu
CleanFrame. Das Skript baut sich seine Hilfs-Container selbst; es braucht nur den
Docker-Host (SSH) erreichbar und den Entwicklermodus am TV. TV-IP und Host-Zugang
stehen oben im Skript.

```sh
# 1) Ist-Zustand lesen UND als Rückweg sichern (verändert nichts):
python3 Home-Umstellung/cf-home.py query

# 2) Home-Taste / Start auf CleanFrame umstellen (braucht vorher 'query'):
python3 Home-Umstellung/cf-home.py apply

# Zurück auf den Samsung-Startbildschirm:
python3 Home-Umstellung/cf-home.py restore
```

- `query` schreibt den Originalzustand nach `cfbuild/original.json` – das ist dein
  Rückweg. **Immer zuerst `query`.**
- `cf-check.py` = reiner Lese-Check (verändert nichts).
- `wrapper` / `wrapper-off` = legt die Home-Taste auf die Mini-App aus
  `Home-Wrapper/` bzw. zurück direkt auf CleanFrame. Das behebt den „zwei
  Klicks"-Effekt (Tizen startet die Home-App über `__NO_RAISE_WINDOW`).
- Die Package-ID der Wrapper-App muss **exakt 10 Zeichen** sein, sonst meldet der
  Fernseher „Load archive info fail".
- `cfbuild/Control.cs` = .NET-Helfer mit Firmware-Prüfung; `cfbuild/original.json`
  = Rückweg-Sicherung.

Wenn etwas klemmt: **`restore`** ist der große Notausgang (alles zurück auf
Samsung).

---

## Rückweg / Deinstallation

- **Apps:** über die normale App-Verwaltung des Fernsehers entfernen, oder das
  jeweilige Original-`.wgt` (sofern genannt) neu installieren.
- **Home-Umstellung:** `python3 Home-Umstellung/cf-home.py restore`.
- **Entwicklermodus:** am TV wieder ausschalten (Schritt 1 rückwärts).

---

## App-IDs am Fernseher

| App | ID |
|---|---|
| waipu.tv | `ndmbVBabXx.WaipuTV` |
| YouTube | `9Ur5IzDKqV.TizenYouTube` |
| Plex | `kIciSQlYEM.plex` |
| Prime Video | `org.tizen.primevideo` |
| Moonlight | `MoonLightS.MoonlightWasm` |
| Tessel | `madebypatk.vlcweb` |

---

## Lizenzen / Quellen

- CleanFrame: [nthnclrk/CleanFrame](https://github.com/nthnclrk/CleanFrame) (MIT)
- Tessel: [PatrickSt1991/tessel-tizen-tv](https://github.com/PatrickSt1991/tessel-tizen-tv) (MIT)
- Moonlight-Tizen und der Installer-Container stammen aus den jeweiligen
  Open-Source-Projekten; die Skripte und Patches in diesem Repo sind eigene Arbeit.

Lizenzhinweise der übernommenen Projekte liegen in den jeweiligen Unterordnern
(`CleanFrame-App/`).

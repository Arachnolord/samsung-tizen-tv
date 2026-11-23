#!/usr/bin/env bash
# Samsung Tizen TV - gefuehrte Einrichtung.
# Fragt nach der TV-IP und installiert die gewaehlten Apps moeglichst automatisch.
# Laeuft auf macOS, Linux und Windows (dort ueber Git-Bash oder WSL; setup.cmd startet es).
#
# Voraussetzungen: Docker (laufend) auf diesem Rechner, TV im Entwicklermodus.
# Ein Samsung-Signierzertifikat wird beim ersten Lauf ueber eine Web-Oberflaeche
# erstellt (Samsung-Konto-Login im Browser) und im Docker-Volume gespeichert.
# Siehe README.md fuer Details und Risiko-Hinweise.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO"

CONTAINER="moonlight-installer"
VOLUME="moonlight-config"
IMAGE="ghcr.io/smookeydev/moonlighttizeninstaller:latest"
SERVICE="/app/client/services/tizenbrew-installer-service"
UI_URL="http://localhost:8091/ui/dist/index.html"
LOCAL_CONF="$REPO/setup.local"            # merkt sich TV-/Host-IP (nicht im Git)
DATA_DIR="$REPO/setup-data"               # gesicherter Projektstand (Zertifikat), nicht im Git
CERT_BACKUP="$DATA_DIR/tizenbrewInstallerConfig.json"
CONF_IN_CONTAINER="/root/share/tizenbrewInstallerConfig.json"   # = Volume moonlight-config

# node-Einzeiler: liegt im Volume ein gueltiges Zertifikat? -> CERT_OK / CERT_MISSING
CERTCHECK="node -e \"try{var c=require('$SERVICE/utils/configuration.js').readConfig()||{};process.stdout.write(c.authorCert&&c.distributorCert?'CERT_OK':'CERT_MISSING')}catch(e){process.stdout.write('CERT_MISSING')}\""

# ---------- Ausgabe-Helfer ----------
if [ -t 1 ]; then B="\033[1m"; G="\033[32m"; Y="\033[33m"; R="\033[31m"; C="\033[36m"; N="\033[0m"; else B=""; G=""; Y=""; R=""; C=""; N=""; fi
say()  { printf "%b\n" "$*"; }
hdr() { printf "\n%b\n" "${B}${C}== $* ==${N}"; }
ok()   { printf "%b\n" "${G}  OK${N} $*"; }
warn() { printf "%b\n" "${Y}  ! ${N} $*"; }
die()  { printf "%b\n" "${R}  ABBRUCH:${N} $*" >&2; exit 1; }

ask() { # ask "Frage" "vorgabe" -> Antwort auf stdout
  local p="$1" d="${2:-}" a
  if [ -n "$d" ]; then printf "%b" "${B}$p${N} [$d]: " >&2; else printf "%b" "${B}$p${N}: " >&2; fi
  read -r a || true
  printf "%s" "${a:-$d}"
}
ask_yn() { # ask_yn "Frage" -> 0 bei ja
  local a; a="$(ask "$1 (j/n)" "")"
  case "$a" in [jJyY]*) return 0;; *) return 1;; esac
}
valid_ip() { # grobe IPv4-Pruefung
  local ip="$1" IFS=. ; [ -n "$ip" ] || return 1
  set -- $ip; [ "$#" -eq 4 ] || return 1
  for o in "$1" "$2" "$3" "$4"; do case "$o" in ''|*[!0-9]*) return 1;; esac; [ "$o" -le 255 ] || return 1; done
  return 0
}
detect_host_ip() { # beste Quell-IP in Richtung TV; leer wenn unbekannt
  local tv="$1" ip=""
  if command -v ip >/dev/null 2>&1; then
    ip="$(ip -o route get "$tv" 2>/dev/null | sed -n 's/.* src \([0-9.]*\).*/\1/p' | head -1)"
  fi
  if [ -z "$ip" ] && command -v route >/dev/null 2>&1; then     # macOS/BSD
    local dev; dev="$(route -n get "$tv" 2>/dev/null | sed -n 's/.*interface: \(.*\)/\1/p')"
    [ -n "$dev" ] && command -v ipconfig >/dev/null 2>&1 && ip="$(ipconfig getifaddr "$dev" 2>/dev/null || true)"
  fi
  printf "%s" "$ip"
}
open_browser() { # Standardbrowser auf eine URL (mac/linux/windows)
  local url="$1"
  if   command -v open        >/dev/null 2>&1; then open "$url"        >/dev/null 2>&1 || true
  elif command -v xdg-open    >/dev/null 2>&1; then xdg-open "$url"    >/dev/null 2>&1 || true
  elif command -v cmd.exe     >/dev/null 2>&1; then cmd.exe /c start "" "$url" >/dev/null 2>&1 || true
  elif command -v powershell.exe >/dev/null 2>&1; then powershell.exe -NoProfile -Command "Start-Process '$url'" >/dev/null 2>&1 || true
  else warn "Konnte keinen Browser oeffnen. Bitte manuell oeffnen: $url"; fi
}
dex() { docker exec "$CONTAINER" sh -c "$1"; }   # Befehl im Container

ensure_container() { # Container ohne Ports (fuer Installationen)
  docker ps  --format '{{.Names}}' | grep -qx "$CONTAINER" && return 0
  if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then docker start "$CONTAINER" >/dev/null && return 0; fi
  say "  Lade/erzeuge Installer-Container (einmalig) ..."
  docker run -d --name "$CONTAINER" -v "$VOLUME:/root/share" "$IMAGE" >/dev/null \
    || die "Container liess sich nicht starten. Image erreichbar? Internet?"
}
start_container_ui() { # Container NEU mit Web-Oberflaeche (Ports 8091 Oberflaeche, 4794 Samsung-Login)
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  docker run -d --name "$CONTAINER" -p 8091:8091 -p 4794:4794 -v "$VOLUME:/root/share" "$IMAGE" >/dev/null \
    || die "Web-Oberflaeche liess sich nicht starten (Port 8091/4794 belegt?)."
}
ui_up() { command -v curl >/dev/null 2>&1 && curl -s -o /dev/null -m 2 "http://localhost:8091/ui/dist/index.html"; }

backup_cert() {  # Projektstand (Zertifikat) aus dem Volume lokal sichern
  mkdir -p "$DATA_DIR" 2>/dev/null || return 0
  if docker cp "$CONTAINER:$CONF_IN_CONTAINER" "$CERT_BACKUP" >/dev/null 2>&1; then
    chmod 600 "$CERT_BACKUP" 2>/dev/null || true
  fi
}
restore_cert() { # lokalen Projektstand ins Volume zurueckspielen (falls Volume leer)
  [ -f "$CERT_BACKUP" ] || return 0
  docker cp "$CERT_BACKUP" "$CONTAINER:$CONF_IN_CONTAINER" >/dev/null 2>&1 || true
}

# ---------- Start ----------
hdr "Samsung Tizen TV - Einrichtung"
say "Dieses Skript installiert die gewaehlten Apps auf deinem Fernseher."
say "${Y}Nur am eigenen Geraet, auf eigene Gefahr. Siehe README.md.${N}"

# 1) Docker vorhanden + laeuft?
hdr "1/7  Docker pruefen"
command -v docker >/dev/null 2>&1 || die "Docker ist nicht installiert / nicht im PATH.\n       macOS/Windows: Docker Desktop. Linux: docker-Paket."
docker info >/dev/null 2>&1 || die "Docker laeuft nicht. Bitte Docker (Desktop) starten und erneut versuchen."
ok "Docker ist bereit."

# 2) Fragerunde
hdr "2/7  Angaben zum Fernseher"
TV_IP=""; HOST_IP=""
if [ -f "$LOCAL_CONF" ]; then
  # shellcheck disable=SC1090
  . "$LOCAL_CONF" || true
  if [ -n "${TV_IP:-}" ] && ask_yn "Gemerkte TV-IP $TV_IP wiederverwenden?"; then :; else TV_IP=""; fi
fi

ask_yn "Ist der Fernseher eingeschaltet und mit demselben Netzwerk verbunden?" \
  || die "Bitte den Fernseher einschalten und ins Netzwerk bringen, dann erneut starten."

while :; do
  [ -n "$TV_IP" ] || TV_IP="$(ask "IP-Adresse des Fernsehers" "")"
  if valid_ip "$TV_IP"; then break; fi
  warn "Das sah nicht nach einer IPv4-Adresse aus (z. B. 192.168.1.75)."; TV_IP=""
done

if command -v ping >/dev/null 2>&1; then
  if ping -c1 -W2 "$TV_IP" >/dev/null 2>&1 || ping -n 1 -w 2000 "$TV_IP" >/dev/null 2>&1; then
    ok "Fernseher $TV_IP antwortet auf Ping."
  else
    warn "$TV_IP antwortet nicht auf Ping. Firewall? Dann trotzdem weiter versuchen."
    ask_yn "Trotzdem fortfahren?" || die "Abgebrochen. Bitte IP/Netzwerk pruefen."
  fi
fi

HOST_DETECTED="$(detect_host_ip "$TV_IP")"
HOST_IP="$(ask "IP dieses Rechners (fuer den Entwicklermodus am TV)" "${HOST_DETECTED:-}")"
valid_ip "$HOST_IP" || warn "Host-IP unklar - nur ein Hinweis fuer den TV-Entwicklermodus, kein Abbruchgrund."
say ""
say "  Im TV-Entwicklermodus als Host-PC-IP ${B}${HOST_IP:-<diese IP>}${N} eintragen,"
say "  falls noch nicht geschehen (Smart Hub -> Apps -> 1 2 3 4 5, siehe README)."

# 3) Installer-Container
hdr "3/7  Installer-Container"
ensure_container
ok "Container '$CONTAINER' laeuft."

# 4) sdb-Verbindung zum TV
hdr "4/7  Verbindung zum Fernseher"
dex "sdb connect $TV_IP:26101" >/dev/null 2>&1 || true
sleep 2
if dex "sdb devices" 2>/dev/null | grep -q "$TV_IP"; then
  ok "Fernseher per sdb verbunden."
else
  warn "sdb findet den Fernseher nicht."
  say  "  Pruefe: Entwicklermodus an? Host-IP $HOST_IP im TV eingetragen? TV neu gestartet?"
  ask_yn "Trotzdem weitermachen?" || die "Abgebrochen."
fi

# 5) Samsung-Zertifikat (pruefen, sonst im Browser erstellen)
hdr "5/7  Samsung-Zertifikat"
CERT="$(dex "$CERTCHECK" 2>/dev/null || echo CERT_MISSING)"
if [ "$CERT" != "CERT_OK" ] && [ -f "$CERT_BACKUP" ]; then
  say "  Spiele gesicherten Projektstand (Zertifikat) zurueck ..."
  restore_cert
  CERT="$(dex "$CERTCHECK" 2>/dev/null || echo CERT_MISSING)"
fi
if [ "$CERT" = "CERT_OK" ]; then
  ok "Zertifikat ist vorhanden."
  backup_cert
else
  warn "Im Volume '$VOLUME' liegt noch kein Samsung-Zertifikat."
  say  "  Es wird einmalig ueber die Web-Oberflaeche des Installers erstellt:"
  say  "  Anmeldung mit deinem Samsung-Konto (oder neues Konto), der Installer liest"
  say  "  die Geraete-ID (DUID) vom verbundenen Fernseher und erzeugt das Zertifikat."
  say  "  Es wird im Volume '$VOLUME' gespeichert und spaeter wiederverwendet."
  if ask_yn "Jetzt die Web-Oberflaeche oeffnen und das Zertifikat erstellen?"; then
    say "  Starte Web-Oberflaeche (Port 8091) ..."
    start_container_ui
    dex "sdb connect $TV_IP:26101" >/dev/null 2>&1 || true   # TV fuer DUID verbinden
    sleep 3
    if ! ui_up; then   # Dienst evtl. nicht automatisch gestartet -> anstossen
      docker exec -d "$CONTAINER" sh -c "cd $SERVICE && node ." >/dev/null 2>&1 || true
      i=0; while [ "$i" -lt 12 ]; do ui_up && break; sleep 2; i=$((i+1)); done
    fi
    open_browser "$UI_URL"
    say ""
    say "  >> Im Browser: mit Samsung-Konto ${B}anmelden oder registrieren${N} und den Schritten folgen."
    say "  >> Der Fernseher muss dabei an und verbunden bleiben (die DUID wird ausgelesen)."
    say "  >> Falls der Browser nicht aufging, oeffne von Hand:  ${B}$UI_URL${N}"
    say ""
    ask "ENTER druecken, sobald das Zertifikat in der Oberflaeche erstellt ist" >/dev/null
    CERT="$(dex "$CERTCHECK" 2>/dev/null || echo CERT_MISSING)"
    if [ "$CERT" = "CERT_OK" ]; then
      ok "Zertifikat erstellt und gespeichert."
      backup_cert
    else
      die "Es liegt weiterhin kein Zertifikat vor. Bitte die Web-Oberflaeche erneut durchlaufen: $UI_URL"
    fi
  else
    die "Ohne Zertifikat kann nicht signiert/installiert werden."
  fi
fi

# 6) Auswahl + Installation
hdr "6/7  Was soll installiert werden?"
say "  1) CleanFrame        - eigener Startbildschirm"
say "  2) Moonlight (+Fix)  - Spiele-Streaming, Esc-Taste repariert"
say "  3) Tessel            - Medienplayer"
say "  4) TizenTube-Fix     - YouTube mit funktionierendem SponsorBlock"
say "  H) Home-Umstellung   - ${Y}fortgeschritten${N}, macht CleanFrame zum Startbildschirm"
say "  (Mehrfachauswahl, z. B.:  1 2 4 )"
SEL="$(ask "Auswahl" "1 2 3 4")"

install_app() { # install_app "Name" wgt_quelle tmp_name installjs_quelle
  local name="$1" wgt="$2" tmpname="$3" js="$4" jsbase
  jsbase="$(basename "$js")"
  say "\n  -> $name"
  [ -f "$wgt" ] || { warn "Paket fehlt: $wgt - uebersprungen."; return 1; }
  [ -f "$js" ]  || { warn "Installer fehlt: $js - uebersprungen."; return 1; }
  docker cp "$wgt" "$CONTAINER:/tmp/$tmpname" >/dev/null
  docker cp "$js"  "$CONTAINER:/tmp/$jsbase" >/dev/null
  if docker exec -e TV_IP="$TV_IP" "$CONTAINER" node "/tmp/$jsbase"; then
    ok "$name installiert."
  else
    warn "$name: Installation meldete einen Fehler (siehe Ausgabe oben)."
    return 1
  fi
}

for tok in $SEL; do
  case "$tok" in
    1) install_app "CleanFrame"    "CleanFrame-App/CleanFrame.wgt"   "CleanFrame.wgt" "Moonlight/cf-install.js"     || true ;;
    2) install_app "Moonlight"     "Moonlight-Fix/Moonlight-fix.wgt" "moonlight.wgt"  "Moonlight-Fix/ml-install.js" || true ;;
    3) install_app "Tessel"        "Tessel/tessel-1.35.0.wgt"        "tessel.wgt"     "Tessel/tessel-install.js"    || true ;;
    4) install_app "TizenTube-Fix" "TizenTube-Fix/TizenTube-fix.wgt" "TizenTube.wgt"  "TizenTube-Fix/tt-install.js" || true ;;
    H|h)
       say "\n${Y}  Home-Umstellung ist fortgeschritten:${N} sie schreibt in System-"
       say "  einstellungen des Fernsehers. Rueckweg ist 'restore'. Auf eigene Gefahr."
       if ask_yn "Wirklich die Home-Umstellung ausfuehren?"; then
         command -v python3 >/dev/null 2>&1 || { warn "python3 fehlt - Home-Umstellung uebersprungen."; continue; }
         say "  Lese Ist-Zustand (Rueckweg-Sicherung) ..."
         CF_DOCKER=local TV_IP="$TV_IP" python3 Home-Umstellung/cf-home.py query || { warn "query fehlgeschlagen - abgebrochen."; continue; }
         if ask_yn "Jetzt umstellen (apply)?"; then
           CF_DOCKER=local TV_IP="$TV_IP" python3 Home-Umstellung/cf-home.py apply || warn "apply meldete einen Fehler."
           say "  Rueckweg jederzeit:  CF_DOCKER=local TV_IP=$TV_IP python3 Home-Umstellung/cf-home.py restore"
         fi
       fi ;;
    *) warn "Unbekannte Auswahl '$tok' - ignoriert." ;;
  esac
done

# 7) Merken + Abschluss (Wegwerf-Container entfernen, Projektstand sichern)
hdr "7/7  Fertig"
{ echo "# gemerkte Werte fuer setup.sh (nicht im Git)"; echo "TV_IP=$TV_IP"; echo "HOST_IP=$HOST_IP"; } > "$LOCAL_CONF" 2>/dev/null || true
backup_cert   # Projektstand sichern, falls noch nicht geschehen
ok "Durchlauf beendet."
say ""
if ask_yn "Wegwerf-Container jetzt entfernen? (empfohlen; Projektstand bleibt gesichert)"; then
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  ok "Container entfernt."
  say "  Der Projektstand (Zertifikat) bleibt im Docker-Volume '$VOLUME'"
  [ -f "$CERT_BACKUP" ] && say "  und zusaetzlich lokal gesichert in: $CERT_BACKUP"
  say "  Beim naechsten './setup.sh' wird er automatisch wiederverwendet - kein erneutes Samsung-Login noetig."
else
  say "  Container bleibt stehen. Spaeter entfernen mit:  docker rm -f $CONTAINER"
fi

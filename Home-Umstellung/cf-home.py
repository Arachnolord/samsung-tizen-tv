#!/usr/bin/env python3
# CleanFrame Home-Umstellung, vom Besitzer selbst ausgefuehrt.
#   python3 cf-home.py query     -> Ist-Zustand lesen + sichern (veraendert nichts)
#   python3 cf-home.py apply      -> Home-Taste/Start auf CleanFrame (braucht vorher query)
#   python3 cf-home.py restore    -> Originalzustand zurueck (braucht die Sicherung)
import base64, os, secrets, socket, subprocess, sys, threading

MODE = sys.argv[1] if len(sys.argv) > 1 else "query"
if MODE not in ("query", "apply", "restore", "fs-on", "fs-off", "wrapper", "wrapper-off"):
    sys.exit("Erlaubt: query | apply | restore | fs-on | fs-off | wrapper | wrapper-off")

TV = "192.168.1.75"
HERE = os.path.dirname(os.path.abspath(__file__))
CS = HERE + "/cfbuild/Control.cs"
PROJ = HERE + "/cfbuild/Control.csproj"
SNAP = HERE + "/cfbuild/original.json"
NAS = ["/usr/bin/ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
       "-p", "2222", "benutzer@192.168.1.23"]
SD = "/home/owner/share/tmp/sdk_tools"

def ssh(cmd, stdin=None):
    return subprocess.run(NAS + [cmd], input=stdin, text=True,
                          capture_output=True, timeout=240)

def clean(s):
    keep = []
    for ln in s.splitlines():
        low = ln.lower()
        if any(x in low for x in ("quantum", "pq.html", "upgraded", "store now")):
            continue
        keep.append(ln)
    return "\n".join(keep)

if MODE in ("apply", "restore", "fs-on", "fs-off", "wrapper", "wrapper-off") and not os.path.exists(SNAP):
    sys.exit("Keine Sicherung gefunden. Bitte zuerst: python3 cf-home.py query")

# 1) dll im .NET-Container auf dem NAS bauen (bleibt auf dem NAS)
print("1/4  baue Steuerprogramm (.NET 6) auf dem NAS ...")
cs = open(CS).read(); proj = open(PROJ).read()
build = ("set -e\n"
         "docker inspect cf-build >/dev/null 2>&1 || docker run -d --name cf-build "
         "--entrypoint sleep mcr.microsoft.com/dotnet/sdk:6.0 infinity >/dev/null\n"
         "docker exec cf-build sh -c 'mkdir -p /src /out'\n"
         "cat > /tmp/Control.cs <<'CSEOF'\n" + cs + "\nCSEOF\n"
         "cat > /tmp/Control.csproj <<'PJEOF'\n" + proj + "\nPJEOF\n"
         "docker cp /tmp/Control.cs cf-build:/src/Control.cs >/dev/null\n"
         "docker cp /tmp/Control.csproj cf-build:/src/Control.csproj >/dev/null\n"
         "docker exec cf-build sh -c 'cd /src && dotnet build -c Release -o /out >/dev/null 2>&1 "
         "&& ls /out/CleanFrameHomeControl.dll' \n")
r = ssh("bash -s", build)
if "CleanFrameHomeControl.dll" not in r.stdout:
    print(clean(r.stdout)); print(clean(r.stderr)); sys.exit("Bau fehlgeschlagen.")
print("     dll gebaut.")

# 2) sdb-Container + Dateien auf den TV schieben
print("2/4  Dateien auf den Fernseher schieben ...")
push = ("set -e\n"
        "docker inspect cf-tv >/dev/null 2>&1 || docker run -d --name cf-tv "
        "--entrypoint sleep ghcr.io/brightcraft/moonlight-tizen:master infinity >/dev/null\n"
        "for f in CleanFrameHomeControl.dll CleanFrameHomeControl.runtimeconfig.json CleanFrameHomeControl.deps.json; do "
        "docker cp cf-build:/out/$f /tmp/$f >/dev/null; docker cp /tmp/$f cf-tv:/tmp/$f >/dev/null; done\n")
if MODE in ("apply", "restore", "fs-on", "fs-off", "wrapper", "wrapper-off"):
    snap = open(SNAP).read()
    push += ("cat > /tmp/orig.json <<'OJEOF'\n" + snap + "\nOJEOF\n"
             "docker cp /tmp/orig.json cf-tv:/tmp/orig.json >/dev/null\n")
push += ("docker exec cf-tv sh -c 'sdb connect %s:26101 >/dev/null 2>&1; sleep 2; "
         "for f in CleanFrameHomeControl.dll CleanFrameHomeControl.runtimeconfig.json CleanFrameHomeControl.deps.json; do "
         "sdb -s %s:26101 push /tmp/$f %s/$f >/dev/null 2>&1; done" % (TV, TV, SD))
if MODE in ("apply", "restore", "fs-on", "fs-off", "wrapper", "wrapper-off"):
    push += ("; sdb -s %s:26101 push /tmp/orig.json %s/CleanFrameHomeOriginal.json >/dev/null 2>&1" % (TV, SD))
push += "'\n"
r = ssh("bash -s", push)
print(clean(r.stderr)[-400:] if r.returncode else "     Dateien auf dem TV.")

# 3) Rueckkanal aufbauen und mode-Skript auf dem TV als UID 901 laufen lassen
print("3/4  fuehre '%s' auf dem Fernseher aus ..." % MODE)
u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); u.connect((TV, 9))
MACIP = u.getsockname()[0]; u.close()
srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind((MACIP, 0)); srv.listen(1); srv.settimeout(30); PORT = srv.getsockname()[1]
out = {"data": b""}
def catcher():
    try:
        c, _ = srv.accept(); c.settimeout(12)
        while True:
            d = c.recv(65536)
            if not d: break
            out["data"] += d
        c.close()
    except Exception as e:
        out["err"] = str(e)
threading.Thread(target=catcher, daemon=True).start()

DLL = SD + "/CleanFrameHomeControl.dll"
ORIG = SD + "/CleanFrameHomeOriginal.json"
if MODE == "query":
    body = "/usr/bin/dotnet %s query" % DLL
else:
    body = "/usr/bin/dotnet %s %s %s" % (DLL, MODE, ORIG)
tok = secrets.token_hex(4); ri = "%s/cfm-%s.sh" % (SD, tok)
modesh = "printf 'CF_BEGIN\\n'\n%s\nprintf '\\nCF_END\\n'\n" % body
boot = "exec 3<>/dev/tcp/%s/%d;cat %s|bash >&3 2>&3;exec 3>&-" % (MACIP, PORT, ri)
b64 = base64.b64encode(boot.encode()).decode()
name = "new2.tpk`printf${IFS}%s${IFS}" + b64 + "|base64${IFS}-d|bash`.tpk"
run = ("cat > /tmp/cfm.sh <<'MEOF'\n" + modesh + "MEOF\n"
       "docker cp /tmp/cfm.sh cf-tv:/tmp/cfm.sh >/dev/null\n"
       "cat > /tmp/cfr.sh <<'REOF'\n"
       "sdb -s %s:26101 push /tmp/cfm.sh %s >/dev/null 2>&1\n"
       "sdb -s %s:26101 shell '0 appinstall tpk %s' 2>&1 | head -2\n"
       "REOF\n"
       "docker cp /tmp/cfr.sh cf-tv:/tmp/cfr.sh >/dev/null\n"
       "docker exec cf-tv bash /tmp/cfr.sh\n") % (TV, ri, TV, name)
r = ssh("bash -s", run)
print("     TV-Antwort:", clean(r.stdout).strip() or clean(r.stderr).strip())

# 4) Ergebnis auswerten
import time; time.sleep(2)
txt = out["data"].decode(errors="replace")
print("\n===== ERGEBNIS =====")
if "CF_BEGIN" not in txt:
    print(txt.strip() or "(keine Rueckmeldung)")
    sys.exit(">>> Kein Ergebnis vom Fernseher. Bitte Ausgabe an Claude schicken.")
print(txt)
import re, json
m = re.search(r"CLEANFRAME_HOME_(JSON|APPLIED|RESTORED|FSON|FSOFF|WRAPPERON|WRAPPEROFF)=(\{.*\})", txt)
SELF = os.path.abspath(__file__)
if MODE == "query" and m:
    open(SNAP, "w").write(m.group(2))
    print(">>> Ist-Zustand gesichert in:", SNAP)
    print(">>> Weiter mit:  python3 %s apply" % SELF)
elif MODE == "apply" and m:
    print(">>> UMGESTELLT. Teste: Home-Taste + einmal TV aus/an.")
    print(">>> Rueckweg jederzeit:  python3 %s restore" % SELF)
elif MODE == "restore" and m:
    print(">>> ZURUECKGESTELLT auf Samsung Home.")
elif MODE == "fs-on" and m:
    print(">>> TEST AN: Absturz-Rueckfall ist jetzt CleanFrame.")
    print(">>> Pruefe am TV:  (1) Home -> EIN Druck?   (2) App beenden/abstuerzen -> landet auf CleanFrame?")
    print(">>> Test zuruecknehmen (Rest bleibt CleanFrame):  python3 %s fs-off" % SELF)
elif MODE == "fs-off" and m:
    print(">>> TEST AUS: first_screen wieder Samsung. Home/Start bleiben CleanFrame (= Stand wie vorher).")
elif MODE == "wrapper" and m:
    print(">>> WRAPPER AN: Home-Taste ruft jetzt die Mini-App cfkey0001.key, die CleanFrame in den Vordergrund holt.")
    print(">>> Teste: aus einer App EINMAL Home -> CleanFrame sofort da?")
    print(">>> Rueckweg (Home direkt auf CleanFrame):  python3 %s wrapper-off" % SELF)
elif MODE == "wrapper-off" and m:
    print(">>> WRAPPER AUS: Home-Taste ruft wieder direkt CleanFrame (nClrkHome1.FrameHome).")
else:
    print(">>> Bitte diese Ausgabe an Claude schicken.")

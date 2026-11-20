# python3 -I tvkey.py KEY_X  press:KEY_POWER:5  wait:1000  text:abc
import socket,ssl,base64,os,time,json,sys,struct
ip,port='192.168.1.75',8002
name=base64.b64encode(b'FAH Steuerung').decode()
tok=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'tv-token.txt')).read().strip()
raw=socket.create_connection((ip,port),5)
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
s=ctx.wrap_socket(raw,server_hostname=ip)
key=base64.b64encode(os.urandom(16)).decode()
s.sendall(f"GET /api/v2/channels/samsung.remote.control?name={name}&token={tok} HTTP/1.1\r\nHost: {ip}:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n".encode())
s.settimeout(10); buf=b''
while b'ms.channel' not in buf: 
  d=s.recv(8192)
  if not d: sys.exit('TV schloss Verbindung')
  buf+=d
if b'unauthorized' in buf: sys.exit('nicht zugelassen')
def send(obj):
  p=json.dumps(obj).encode(); m=os.urandom(4)
  h=bytes([0x81]); n=len(p)
  h+= bytes([0x80|n]) if n<126 else bytes([0x80|126])+struct.pack('>H',n)
  s.sendall(h+m+bytes(b^m[i%4] for i,b in enumerate(p)))
def k(cmd,key): send({"method":"ms.remote.control","params":{"Cmd":cmd,"DataOfCmd":key,"Option":"false","TypeOfRemote":"SendRemoteKey"}})
for a in sys.argv[1:]:
  if a.startswith('wait:'): time.sleep(int(a[5:])/1000); continue
  if a.startswith('press:'):
    _,key,sec=a.split(':'); k('Press',key); time.sleep(float(sec)); k('Release',key)
  elif a.startswith('text:'):
    send({"method":"ms.remote.control","params":{"Cmd":base64.b64encode(a[5:].encode()).decode(),"DataOfCmd":"base64","TypeOfRemote":"SendInputString"}}); time.sleep(0.3)
    send({"method":"ms.remote.control","params":{"Cmd":"","DataOfCmd":"","TypeOfRemote":"SendInputEnd"}})
  else: k('Click',a)
  print('->',a); time.sleep(0.7)
s.close()

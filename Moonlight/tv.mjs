// Samsung-TV fernsteuern: node tv.mjs KEY_1 KEY_2 ... | text:192.168.1.23 | wait:1500
import fs from 'node:fs';
const DIR = new URL('.', import.meta.url).pathname;
const TOKFILE = DIR + 'tv-token.txt';
const ip = '192.168.1.75';
const name = Buffer.from('FAH Fernbedienung').toString('base64');
let token = '';
try { token = fs.readFileSync(TOKFILE, 'utf8').trim(); } catch {}
const url = `wss://${ip}:8002/api/v2/channels/samsung.remote.control?name=${name}` + (token ? `&token=${token}` : '');
const args = process.argv.slice(2);
const ws = new WebSocket(url);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const timer = setTimeout(() => { console.log('Zeitüberschreitung – keine Freigabe am TV'); process.exit(2); }, 40000);
ws.onmessage = async ev => {
  const m = JSON.parse(ev.data);
  console.log('<-', m.event, m.data && m.data.token ? '(Token erhalten)' : '');
  if (m.event === 'ms.channel.connect') {
    if (m.data && m.data.token) fs.writeFileSync(TOKFILE, String(m.data.token));
    clearTimeout(timer);
    for (const a of args) {
      if (a.startsWith('wait:')) { await sleep(+a.slice(5)); continue; }
      if (a.startsWith('text:')) {
        const t = Buffer.from(a.slice(5)).toString('base64');
        ws.send(JSON.stringify({ method: 'ms.remote.control', params: { Cmd: t, DataOfCmd: 'base64', TypeOfRemote: 'SendInputString' } }));
        await sleep(300);
        ws.send(JSON.stringify({ method: 'ms.remote.control', params: { Cmd: '', DataOfCmd: '', TypeOfRemote: 'SendInputEnd' } }));
      } else {
        ws.send(JSON.stringify({ method: 'ms.remote.control', params: { Cmd: 'Click', DataOfCmd: a, Option: 'false', TypeOfRemote: 'SendRemoteKey' } }));
      }
      console.log('->', a);
      await sleep(600);
    }
    await sleep(500);
    ws.close(); process.exit(0);
  }
  if (m.event === 'ms.channel.unauthorized') { console.log('abgelehnt'); process.exit(3); }
};
ws.onopen = () => console.log("Verbindung offen – warte auf Freigabe am TV");
ws.onclose = e => console.log("geschlossen", e.code, e.reason);
ws.onerror = e => { console.log('Fehler', e.message || e); };

process.chdir('/app/client/services/tizenbrew-installer-service');
const B = '/app/client/services/tizenbrew-installer-service/';
const fs = require('fs');
const adbhost = require(B + 'node_modules/adbhost');
const { readConfig } = require(B + 'utils/configuration.js');
const { resignPackage } = require(B + 'utils/SamsungCertificateCreation.js');
const { parsePackage, installPackage } = require(B + 'utils/PackageInstallation.js');
const PushFile = require(B + 'utils/FilePusher.js');
const TV = process.env.TV_IP || '192.168.1.75';
(async () => {
  const cfg = readConfig();
  if (!cfg.authorCert || !cfg.distributorCert) throw new Error('kein Zertifikat im Volume');
  const buf = fs.readFileSync('/tmp/CleanFrame.wgt');
  console.log('wgt geladen', buf.length);
  const signed = await resignPackage({
    authorCert: Buffer.from(cfg.authorCert, 'base64').toString('binary'),
    distributorCert: Buffer.from(cfg.distributorCert, 'base64').toString('binary'),
    password: cfg.password
  }, buf);
  const pkg = await parsePackage(signed);
  console.log('signiert', signed.length, 'Paket', pkg.packageId);
  const adb = adbhost.createConnection({ host: TV, port: 26101 });
  adb._stream.on('error', e => { console.log('sdb-Fehler', e.message); process.exit(1); });
  await new Promise(r => adb._stream.on('connect', r));
  await new Promise(r => setTimeout(r, 1500));
  console.log('sdb verbunden');
  const path = '/home/owner/share/tmp/sdk_tools/cleanframe.wgt';
  await new Promise(r => PushFile(adb, path, signed, r));
  console.log('hochgeladen');
  await new Promise(r => setTimeout(r, 4000));
  const res = await Promise.race([installPackage(path, pkg.packageId, adb), new Promise(r => setTimeout(() => r('(Zeitlimit)'), 180000))]);
  console.log('Ergebnis:\n' + res);
  process.exit(0);
})().catch(e => { console.log('FEHLER', e.message); process.exit(1); });

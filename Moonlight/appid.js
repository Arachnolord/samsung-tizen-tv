const B='/app/client/services/tizenbrew-installer-service/node_modules/';
const fetch=require(B+'node-fetch'), JSZip=require(B+'jszip');
(async()=>{const r=await (await fetch('https://github.com/brightcraft/moonlight-tizen/releases/download/v1.20.0/Moonlight.wgt')).buffer();
const z=await JSZip.loadAsync(r); const c=await z.files['config.xml'].async('string');
console.log((c.match(/<tizen:application[^>]*>/)||[''])[0]); console.log((c.match(/<widget[^>]*version="[^"]*"/)||[''])[0].slice(0,200));})();

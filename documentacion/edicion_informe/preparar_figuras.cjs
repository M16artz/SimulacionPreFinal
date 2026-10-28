const fs=require('node:fs');
const path=require('node:path');
const sharp=require('C:/Users/Det-Pc/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
(async()=>{
 for(const nombre of ['figura_1_permanencia','figura_2_cocina','figura_3_utilizacion']){
  let svg=fs.readFileSync(path.join(__dirname,'../analisis_informe',nombre+'.svg'),'utf8');
  svg=svg.replace(/font-size="([0-9.]+)"/g,(_,n)=>`font-size="${Number(n)<=13?17:Number(n)}"`);
  await sharp(Buffer.from(svg),{density:240}).resize({width:2400}).png().toFile(path.join(__dirname,nombre+'.png'));
 }
})();

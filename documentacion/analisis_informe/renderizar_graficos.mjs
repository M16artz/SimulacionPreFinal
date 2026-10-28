import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const require=createRequire(new URL('../../frontend/package.json',import.meta.url));
const {chromium}=require('playwright');
const navegador=await chromium.launch({headless:true});
try {
  for(const nombre of ['figura_1_permanencia','figura_2_cocina','figura_3_utilizacion']){
    const pagina=await navegador.newPage({viewport:{width:1050,height:600},deviceScaleFactor:1.5});
    const svg=await fs.readFile(new URL(`${nombre}.svg`,import.meta.url),'utf8');
    await pagina.setContent(`<html><head><meta charset="utf-8"/><style>body{margin:0;background:white}svg{display:block}</style></head><body>${svg}</body></html>`);
    await pagina.evaluate(()=>window.scrollTo(0,0));
    await pagina.locator('svg').screenshot({path:fileURLToPath(new URL(`${nombre}.png`,import.meta.url))});
    await pagina.close();
  }
} finally {await navegador.close();}

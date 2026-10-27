import {afterEach,describe,it,expect,vi} from 'vitest';
import {api,ErrorApi} from '../src/servicios/api';
afterEach(()=>vi.unstubAllGlobals());
describe('Errores comprensibles de la API',()=>{
  it('conserva los errores de negocio y el código HTTP',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:[{campo:'mesas',mensaje:'El valor debe ser mayor o igual a 1'}]}),{status:422})));
    await expect(api('/configuraciones')).rejects.toMatchObject({estado:422,message:'mesas: El valor debe ser mayor o igual a 1'});
  });
  it('explica una respuesta HTML de un proxy o servidor caído',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response('<html>Error</html>',{status:502})));
    await expect(api('/salud')).rejects.toMatchObject({estado:502,message:expect.stringContaining('respuesta no válida')});
  });
  it('explica la pérdida de conexión sin inventar resultados',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    await expect(api('/salud')).rejects.toBeInstanceOf(ErrorApi);
  });
});

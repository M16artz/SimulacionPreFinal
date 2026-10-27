// Node 22.18+ ejecuta directamente estos servicios TypeScript sin React ni npm.
import {afterEach,test} from 'node:test';
import assert from 'node:assert/strict';
import {api,enviar,ErrorApi} from '../../src/servicios/api.ts';
import {hora,indiceEnTiempo} from '../../src/servicios/reproduccion.ts';
const fetchOriginal=globalThis.fetch;
afterEach(()=>{globalThis.fetch=fetchOriginal;});

test('el cliente conserva las métricas del backend sin recalcularlas',async()=>{
  const metricas={personas_atendidas:219,tasa_abandono:65/158};
  globalThis.fetch=async()=>new Response(JSON.stringify({metricas}),{status:200});
  assert.deepEqual((await api('/simulaciones/ejemplo/resultados')).metricas,metricas);
});

test('envía configuración y semilla como JSON',async()=>{
  const solicitud={configuracion:{mesas:11},semilla:42};
  globalThis.fetch=async(ruta,opciones)=>{
    assert.equal(ruta,'/api/v1/simulaciones');
    assert.equal(opciones.method,'POST');
    assert.deepEqual(JSON.parse(opciones.body),solicitud);
    return new Response(JSON.stringify({id:'ejecucion',estado:'pendiente'}),{status:202});
  };
  assert.equal((await api('/simulaciones',enviar(solicitud))).estado,'pendiente');
});

test('los errores de validación conservan el campo y el código HTTP',async()=>{
  globalThis.fetch=async()=>new Response(JSON.stringify({detail:[{campo:'mesas',mensaje:'Debe ser mayor que cero'}]}),{status:422});
  await assert.rejects(api('/configuraciones'),error=>error instanceof ErrorApi&&error.estado===422&&error.message.includes('mesas: Debe ser mayor que cero'));
});

test('una respuesta HTML produce un error comprensible',async()=>{
  globalThis.fetch=async()=>new Response('<html>Error</html>',{status:502});
  await assert.rejects(api('/salud'),error=>error.estado===502&&error.message.includes('respuesta no válida'));
});

test('una caída de red no se presenta como resultado de simulación',async()=>{
  globalThis.fetch=async()=>{throw new TypeError('Failed to fetch');};
  await assert.rejects(api('/salud'),error=>error instanceof ErrorApi&&error.estado===0&&error.message.includes('conectar'));
});

test('la cancelación de una consulta conserva la señal de cancelación',async()=>{
  const controlador=new AbortController();controlador.abort();
  globalThis.fetch=async()=>{throw controlador.signal.reason;};
  await assert.rejects(api('/salud',{signal:controlador.signal}),error=>error.name==='AbortError');
});

test('el reloj representa la jornada y la atención después del cierre',()=>{
  assert.equal(hora(540),'09:00');
  assert.equal(hora(1272.99),'21:12');
});

test('la reproducción avanza y retrocede sobre eventos ya calculados',()=>{
  const eventos=[{tiempo:540},{tiempo:550},{tiempo:550},{tiempo:560}];
  assert.equal(indiceEnTiempo(eventos,555),2);
  assert.equal(indiceEnTiempo(eventos,545),0);
  assert.equal(indiceEnTiempo(eventos,600),3);
  assert.equal(indiceEnTiempo(eventos,550),2);
  assert.equal(indiceEnTiempo(eventos,500),0);
});

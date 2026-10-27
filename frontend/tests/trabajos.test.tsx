import {act,renderHook,waitFor,cleanup} from '@testing-library/react';
import {afterEach,beforeEach,describe,it,expect,vi} from 'vitest';
import {usarTrabajo} from '../src/servicios/usarTrabajo';
import {api,ErrorApi} from '../src/servicios/api';
vi.mock('../src/servicios/api',async importar=>{const original=await importar() as typeof import('../src/servicios/api');return {...original,api:vi.fn()};});
const id='af060e2b-e1d8-44d5-8313-c5a9e8640fb9';
beforeEach(()=>{localStorage.clear();vi.mocked(api).mockReset();});
afterEach(()=>{cleanup();vi.useRealTimers();});
describe('Seguimiento de trabajos independiente de la navegación',()=>{
  it('recupera una consulta guardada y muestra el resultado del backend',async()=>{
    localStorage.setItem('mesa.simulaciones.ultima',id);
    vi.mocked(api).mockResolvedValueOnce({id,estado:'completado'}).mockResolvedValueOnce({metricas:{personas_atendidas:219}});
    const {result}=renderHook(()=>usarTrabajo<{metricas:{personas_atendidas:number}}>('simulaciones'));
    await waitFor(()=>expect(result.current.resultado?.metricas.personas_atendidas).toBe(219));
    expect(result.current.ocupado).toBe(false);
  });
  it('evita enviar dos veces la misma solicitud mientras está en curso',async()=>{
    let resolver!:(datos:unknown)=>void;
    vi.mocked(api).mockImplementationOnce(()=>new Promise(resuelto=>{resolver=resuelto;}));
    const {result}=renderHook(()=>usarTrabajo('simulaciones'));
    let primero!:Promise<unknown>;
    act(()=>{primero=result.current.ejecutar({semilla:42});});
    await expect(result.current.ejecutar({semilla:42})).rejects.toThrow('ya se está enviando');
    vi.mocked(api).mockResolvedValue({id,estado:'error',error:'Ejecución interrumpida'});
    await act(async()=>{resolver({id,estado:'pendiente'});await primero;});
    await waitFor(()=>expect(result.current.error).toBe('Ejecución interrumpida'));
  });
  it('una pérdida de red conserva el identificador para recuperar la ejecución',async()=>{
    localStorage.setItem('mesa.simulaciones.ultima',id);
    vi.mocked(api).mockRejectedValueOnce(new ErrorApi('Conexión interrumpida'));
    const {result}=renderHook(()=>usarTrabajo('simulaciones'));
    await waitFor(()=>expect(result.current.error).toBe('Conexión interrumpida'));
    expect(result.current.trabajo?.id).toBe(id);
    expect(result.current.trabajo?.estado).toBe('pendiente');
    expect(localStorage.getItem('mesa.simulaciones.ultima')).toBe(id);
  });
});

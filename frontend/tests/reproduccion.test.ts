import {describe,it,expect} from 'vitest';
import {hora,indiceEnTiempo} from '../src/servicios/reproduccion';
import type {Evento} from '../src/tipos/contratos';
const eventos=[{tiempo:540,secuencia:0},{tiempo:550,secuencia:1},{tiempo:550,secuencia:2},{tiempo:560,secuencia:3}] as Evento[];
describe('Reproducción de eventos calculados',()=>{
  it('retrocede y avanza sin recalcular la simulación',()=>{expect(indiceEnTiempo(eventos,555)).toBe(2);expect(indiceEnTiempo(eventos,545)).toBe(0);expect(indiceEnTiempo(eventos,600)).toBe(3);});
  it('resuelve eventos simultáneos conservando el orden del backend',()=>{expect(indiceEnTiempo(eventos,550)).toBe(2);});
  it('formatea horas y la atención posterior al cierre',()=>{expect(hora(540)).toBe('09:00');expect(hora(1272.99)).toBe('21:12');});
});

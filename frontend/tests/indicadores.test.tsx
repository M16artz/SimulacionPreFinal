import {describe,it,expect} from 'vitest';
import {render,screen,cleanup} from '@testing-library/react';
import {afterEach} from 'vitest';
import {Indicadores} from '../src/modulos/resultados/Resultados';
import type {Resultado} from '../src/tipos/contratos';
afterEach(cleanup);
describe('Indicadores del backend',()=>{
  it('muestra las métricas recibidas con conversión porcentual explícita',()=>{const r={metricas:{personas_atendidas:219,espera_mesa_media:10.7,tasa_abandono:0.411,utilizacion_mesa:0.747}} as unknown as Resultado;render(<Indicadores resultado={r}/>);expect(screen.getByText('219')).toBeInTheDocument();expect(screen.getByText('10,7')).toBeInTheDocument();expect(screen.getByText('41,1')).toBeInTheDocument();expect(screen.getByText('74,7')).toBeInTheDocument();});
  it('no inventa indicadores antes de una ejecución',()=>{render(<Indicadores resultado={null}/>);expect(screen.getAllByText(/Ejecuta un escenario/)).toHaveLength(4);});
});

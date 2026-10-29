import {afterEach,describe,it,expect} from 'vitest';
import {render,screen,cleanup} from '@testing-library/react';
import FormulacionMatematica from '../src/modulos/resultados/FormulacionMatematica';
import type {AnalisisMatematico} from '../src/tipos/contratos';
afterEach(cleanup);
const analisis:AnalisisMatematico={inicio:0,fin:10,duracion:10,colas:[{estacion:'mesa',area_grupo_minutos:4,longitud_media:0.4,numero_entidades:2,espera_media:2}],little:[{ambito:'sistema',poblacion:'Todos los grupos llegados, incluidos abandonos',unidad_entidades:'grupos',unidad_tiempo:'minutos',numero_entidades:2,inicio:0,fin:10,longitud_media:1.4,tasa_efectiva:0.2,tiempo_medio:7,producto_lambda_w:1.4,error_absoluto:0,aplicable:true,coincide:true,observacion:'Balance finito'}]};
describe('Presentación de la formulación calculada por el backend',()=>{
  it('muestra las medias con sus unidades y el balance visual',()=>{
    render(<FormulacionMatematica analisis={analisis} id="ejemplo"/>);
    expect(screen.getByText('0,4 grupos en cola · 2 observados')).toBeInTheDocument();
    expect(screen.getByText('0,2')).toBeInTheDocument();
    expect(screen.getByText('Los valores coinciden')).toBeInTheDocument();
    expect(screen.getByRole('link',{name:'CSV de Little'})).toHaveAttribute('href','/api/v1/simulaciones/ejemplo/exportar?formato=csv&tabla=little');
  });
  it('no convierte una cohorte vacía en un contraste exitoso',()=>{
    const vacio={...analisis,colas:[],little:[{...analisis.little[0],numero_entidades:0,tiempo_medio:null,producto_lambda_w:null,error_absoluto:null,aplicable:false,coincide:null}]};
    render(<FormulacionMatematica analisis={vacio} id="ejemplo"/>);
    expect(screen.getByText('No aplicable')).toBeInTheDocument();
    expect(screen.queryByText('Los valores coinciden')).not.toBeInTheDocument();
  });
  it('identifica ejecuciones anteriores que no registraban estas poblaciones',()=>{
    render(<FormulacionMatematica id="anterior"/>);
    expect(screen.getByText(/Esta ejecución anterior no contiene/)).toBeInTheDocument();
    expect(screen.queryByRole('link',{name:'CSV de colas'})).not.toBeInTheDocument();
  });
});

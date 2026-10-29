import {afterEach,describe,it,expect,vi} from 'vitest';
import {render,screen,cleanup,fireEvent,within} from '@testing-library/react';
import type {ComponentProps} from 'react';
import type {Configuracion,Experimento,Resumen} from '../src/tipos/contratos';
import ResultadosExperimento from '../src/modulos/experimentos/ResultadosExperimento';
import DetalleComparacion from '../src/modulos/experimentos/DetalleComparacion';

// Give real charts a deterministic size in jsdom, which has no layout engine.
vi.mock('recharts',async()=>{
  const real=await vi.importActual<typeof import('recharts')>('recharts');
  return {...real,ResponsiveContainer:(props:ComponentProps<typeof real.ResponsiveContainer>)=><real.ResponsiveContainer {...props} width={800} height={350}/>};
});
afterEach(cleanup);
const resumen=(media:number):Resumen=>({media,ic95:[media-0.1,media+0.1],replicas:2});
const configuracion:Configuracion={version_esquema:'1.0',nombre:'Prueba',sintetica:true,notas:'',mesas:10,capacidad_mesa:4,meseros:2,cocineras:3,apertura:540,cierre:1200,llegadas:[{inicio:540,fin:1200,tasa:10}],probabilidades_grupo:[1,0,0,0,0,0,0,0],tiempos:{pedido:{tipo:'fija',valor:2},preparacion:{tipo:'fija',valor:5},entrega:{tipo:'fija',valor:2},consumo:{tipo:'fija',valor:20},cobro:{tipo:'fija',valor:2},paciencia:{tipo:'fija',valor:15}}};
const experimento:Experimento={version_modelo:'1.1',version_entorno:{python:'3.14'},semillas_replicas:[42,43],replicas:2,escenarios:Array.from({length:10},(_,i)=>({id:100+i,nombre:`Alternativa ${i}`,configuracion:{...configuracion,mesas:10+i},eficiente:i%2===0,resumen:{espera_mesa_media:resumen(i+1),tasa_abandono:resumen(i/100),personas_atendidas:resumen(200+i)}})),diferencias_pareadas:Array.from({length:9},(_,i)=>({escenario:101+i,base:100,metricas:{espera_mesa_media:resumen(-i),tasa_abandono:resumen(-i/100),personas_atendidas:resumen(i)}}))};

describe('Exploración de resultados experimentales',()=>{
  it('permite recorrer todas las alternativas y limita cada página',()=>{
    render(<ResultadosExperimento resultado={experimento} id="prueba"/>);
    expect(screen.getAllByRole('row')).toHaveLength(9);
    expect(screen.queryByRole('button',{name:'Seleccionar escenario #109'})).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Página siguiente de resultados experimentales'}));
    expect(screen.getAllByRole('row')).toHaveLength(3);
    expect(screen.getByRole('button',{name:'Seleccionar escenario #109'})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Página siguiente de resultados experimentales'})).toBeDisabled();
  });
  it('un punto abre la página de su fila y conserva la selección al volver a esa página',()=>{
    render(<ResultadosExperimento resultado={experimento} id="prueba"/>);
    fireEvent.click(screen.getByRole('button',{name:/Ver escenario #109:/}));
    const fila=screen.getByRole('button',{name:'Seleccionar escenario #109'}).closest('tr');
    expect(fila).toHaveClass('fila-seleccionada');
    expect(fila).toHaveFocus();
    expect(screen.getByRole('button',{name:/Ver escenario #109:/})).toHaveAttribute('aria-pressed','true');
    fireEvent.click(screen.getByRole('button',{name:'Página anterior de resultados experimentales'}));
    fireEvent.click(screen.getByRole('button',{name:'Página siguiente de resultados experimentales'}));
    expect(screen.getByRole('button',{name:'Seleccionar escenario #109'}).closest('tr')).toHaveClass('fila-seleccionada');
  });
  it('permite seleccionar puntos con teclado y localizar alternativas coincidentes',()=>{
    render(<ResultadosExperimento resultado={experimento} id="prueba"/>);
    fireEvent.keyDown(screen.getByRole('button',{name:/Ver escenario #108:/}),{key:'Enter'});
    expect(screen.getByRole('button',{name:'Seleccionar escenario #108'})).toHaveAttribute('aria-pressed','true');
    fireEvent.change(screen.getByRole('combobox',{name:'Localizar escenario en la tabla'}),{target:{value:'100'}});
    expect(screen.getByRole('button',{name:'Seleccionar escenario #100'})).toHaveAttribute('aria-pressed','true');
  });
  it('pagina las diferencias de manera independiente sin perder la última comparación',()=>{
    render(<DetalleComparacion resultado={experimento}/>);
    const nav=screen.getByRole('navigation',{name:'Paginación de cambios frente al primer escenario'});
    expect(within(nav).getByRole('button',{name:/Página anterior/})).toBeDisabled();
    expect(screen.queryByText('#109 frente a #100')).not.toBeInTheDocument();
    fireEvent.click(within(nav).getByRole('button',{name:/Página siguiente/}));
    expect(screen.getByText('#109 frente a #100')).toBeInTheDocument();
    expect(screen.getAllByRole('row')).toHaveLength(2);
  });
});

import {useEffect,useRef,useState} from 'react';
import {Download,CheckCircle2,MousePointer2} from 'lucide-react';
import {ScatterChart,Scatter,XAxis,YAxis,CartesianGrid,Tooltip,ResponsiveContainer,ZAxis,LabelList} from 'recharts';
import type {Experimento} from '../../tipos/contratos';
import {decimal} from '../resultados/Resultados';
import Paginacion,{FILAS_POR_PAGINA} from '../../componentes/Paginacion';

type Punto={id:number;nombre:string;espera:number;abandono:number;recursos:number;mesas:number;meseros:number;cocineras:number;eficiente:boolean};
function DetallePunto({active,payload}:{active?:boolean;payload?:readonly {payload?:Punto}[]}){
  const p=payload?.[0]?.payload;
  if(!active||!p)return null;
  return <div className="tooltip-grafico"><strong>Escenario #{p.id} · {p.nombre}</strong><div>Espera <b>{decimal(p.espera)} min</b></div><div>Abandono <b>{decimal(p.abandono)} %</b></div><div>{p.mesas} mesas · {p.meseros} meseros · {p.cocineras} cocineras</div><small>{p.eficiente?'Alternativa eficiente':'Alternativa dominada'} · Haz clic para ver su fila</small></div>;
}
export default function ResultadosExperimento({resultado,id}:{resultado:Experimento;id:string}){
  const [pagina,fijarPagina]=useState(0),[seleccionado,fijarSeleccionado]=useState<number|null>(null);
  const [localizacion,fijarLocalizacion]=useState(0);
  const tabla=useRef<HTMLDivElement>(null),desplazar=useRef(false);
  const puntos:Punto[]=resultado.escenarios.map(e=>({id:e.id,nombre:e.nombre,espera:e.resumen.espera_mesa_media.media,abandono:e.resumen.tasa_abandono.media*100,recursos:e.configuracion.mesas+e.configuracion.meseros+e.configuracion.cocineras,mesas:e.configuracion.mesas,meseros:e.configuracion.meseros,cocineras:e.configuracion.cocineras,eficiente:e.eficiente}));
  function seleccionar(id:number,desdeGrafico=false){
    const posicion=resultado.escenarios.findIndex(e=>e.id===id);
    if(posicion<0)return;
    desplazar.current=desdeGrafico;
    fijarPagina(Math.floor(posicion/FILAS_POR_PAGINA));
    fijarSeleccionado(id);
    if(desdeGrafico)fijarLocalizacion(v=>v+1);
  }
  useEffect(()=>{
    if(!desplazar.current||seleccionado===null)return;
    const fila=tabla.current?.querySelector<HTMLTableRowElement>(`[data-escenario="${seleccionado}"]`);
    fila?.scrollIntoView?.({behavior:window.matchMedia?.('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'center'});
    fila?.focus({preventScroll:true});
    desplazar.current=false;
  },[seleccionado,pagina,localizacion]);
  const elegidos=resultado.escenarios.slice(pagina*FILAS_POR_PAGINA,(pagina+1)*FILAS_POR_PAGINA);
  return <><section className="tarjeta resultados-experimentales"><div className="encabezado-tarjeta"><div><div className="ceja">RESULTADOS EXPERIMENTALES</div><h2>{resultado.escenarios.length} escenarios · {resultado.replicas} réplicas</h2></div><div className="acciones"><a className="boton secundario" href={`/api/v1/experimentos/${id}/exportar?formato=csv`}><Download size={16}/> CSV</a><a className="boton secundario" href={`/api/v1/experimentos/${id}/exportar?formato=json`}>JSON</a></div></div><div className="tabla-scroll" ref={tabla}><table><thead><tr><th>Escenario</th><th>Mesas / meseros / cocineras</th><th>Espera (min), IC 95 %</th><th>Abandono (%)</th><th>Personas atendidas</th><th>Pareto</th></tr></thead><tbody>{elegidos.map(e=><tr key={e.id} data-escenario={e.id} tabIndex={-1} className={seleccionado===e.id?'fila-seleccionada':''} aria-current={seleccionado===e.id?'true':undefined}><td><button className="seleccionar-escenario" aria-label={`Seleccionar escenario #${e.id}`} aria-pressed={seleccionado===e.id} onClick={()=>seleccionar(e.id)}>#{e.id} · {e.nombre}</button></td><td>{e.configuracion.mesas} / {e.configuracion.meseros} / {e.configuracion.cocineras}</td><td>{decimal(e.resumen.espera_mesa_media.media)}<small>{e.resumen.espera_mesa_media.ic95?.map(decimal).join(' – ')??'IC no estimable con una réplica'}</small></td><td>{decimal(e.resumen.tasa_abandono.media*100)}</td><td>{decimal(e.resumen.personas_atendidas.media)}</td><td>{e.eficiente?<span className="etiqueta"><CheckCircle2 size={12}/> Eficiente</span>:'Dominado'}</td></tr>)}</tbody></table></div><Paginacion total={resultado.escenarios.length} pagina={pagina} cambiar={fijarPagina} etiqueta="resultados experimentales"/></section>
  <section className="tarjeta"><div className="encabezado-tarjeta"><div><div className="ceja">COMPARACIÓN DE ESCENARIOS</div><h2>Espera y abandono</h2></div><span className="etiqueta"><MousePointer2 size={14}/> Selecciona un punto</span></div><p>Cada punto es un escenario. Las alternativas más cercanas a la esquina inferior izquierda combinan menor espera y menor abandono.</p><div className="leyenda-experimentos"><span><i className="punto eficiente"/> Eficiente</span><span><i className="punto dominado"/> Dominado</span><span><i className="punto seleccionado"/> Seleccionado</span></div>
  <ResponsiveContainer width="100%" height={350}><ScatterChart margin={{bottom:32,left:8,right:28,top:24}} accessibilityLayer={false}><CartesianGrid stroke="var(--borde)" strokeDasharray="3 6"/><XAxis type="number" dataKey="espera" name="Espera" unit=" min" domain={[0,'auto']} axisLine={false} tickLine={false} label={{value:'Espera media por mesa (min)',position:'bottom',offset:16}}/><YAxis type="number" dataKey="abandono" name="Abandono" unit=" %" domain={[0,Math.min(100,Math.max(5,...puntos.map(p=>p.abandono))*1.12)]} axisLine={false} tickLine={false} width={62} label={{value:'Grupos que abandonan (%)',angle:-90,position:'insideLeft',style:{textAnchor:'middle'}}}/><ZAxis type="number" dataKey="recursos" range={[110,400]} name="Recursos totales"/><Tooltip content={<DetallePunto/>} cursor={{strokeDasharray:'3 3'}}/><Scatter name="Escenarios" data={puntos} isAnimationActive={false} shape={(props:unknown)=>{
    const {cx,cy,size,payload}=props as {cx:number;cy:number;size:number;payload:Punto};
    const activo=payload.id===seleccionado;
    return <g role="button" tabIndex={0} aria-label={`Ver escenario #${payload.id}: ${decimal(payload.espera)} minutos de espera, ${decimal(payload.abandono)} % de abandono`} aria-pressed={activo} className="punto-escenario" onClick={()=>seleccionar(payload.id,true)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();seleccionar(payload.id,true);}}}><circle cx={cx} cy={cy} r={Math.max(7,Math.sqrt(size/Math.PI))+5} fill="transparent"/><circle cx={cx} cy={cy} r={Math.max(7,Math.sqrt(size/Math.PI))} fill={activo?'var(--color-acento)':payload.eficiente?'var(--color-primario)':'var(--color-lavanda-oscuro)'} stroke={activo?'var(--color-navegacion)':'var(--color-superficie)'} strokeWidth={activo?3:2} fillOpacity={activo?1:0.85}/></g>;
  }}>{puntos.length<=24&&<LabelList dataKey="id" position="top" formatter={v=>`#${v}`}/>}</Scatter></ScatterChart></ResponsiveContainer>
  <div className="seleccion-grafico"><label>Localizar escenario<select aria-label="Localizar escenario en la tabla" value={seleccionado??''} onChange={e=>{if(e.target.value!=='')seleccionar(Number(e.target.value),true);}}><option value="">Selecciona un escenario</option>{puntos.map(p=><option key={p.id} value={p.id}>#{p.id} · {p.mesas} mesas / {p.meseros} meseros / {p.cocineras} cocineras</option>)}</select></label><p role="status">{seleccionado===null?'Haz clic en un punto para resaltar su fila en la tabla.':`Escenario #${seleccionado} resaltado en la página ${Math.floor(resultado.escenarios.findIndex(e=>e.id===seleccionado)/FILAS_POR_PAGINA)+1} de resultados.`}</p></div><p className="ayuda">El área de cada círculo representa la cantidad total de recursos. Se muestran todos los escenarios, independientemente de la página de la tabla. Los puntos coincidentes también se pueden seleccionar desde el desplegable.</p></section></>;
}

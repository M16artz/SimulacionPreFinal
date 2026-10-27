import type {Trabajo} from '../tipos/contratos';
export default function ProgresoTrabajo({trabajo}:{trabajo:Trabajo|null}) {
  if(!trabajo||!['pendiente','ejecutando'].includes(trabajo.estado))return null;
  const progreso=trabajo.progreso;
  return <div className="aviso progreso-trabajo" role="status"><div><strong>{trabajo.estado==='pendiente'?'Esperando trabajador':'Cálculo en proceso'}</strong><span>{progreso?.total?`${progreso.completadas} de ${progreso.total} ejecuciones completadas`:'Preparando la ejecución…'}</span></div><progress aria-label="Progreso de ejecución" max={progreso?.total??1} value={progreso?.total?progreso.completadas:undefined}/><small>La consulta se recupera al recargar esta página.</small></div>;
}

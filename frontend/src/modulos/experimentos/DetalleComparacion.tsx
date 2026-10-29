import {useState} from 'react';
import Paginacion,{FILAS_POR_PAGINA} from '../../componentes/Paginacion';
import type {Experimento,Resumen} from '../../tipos/contratos';
import {decimal} from '../resultados/Resultados';
function intervalo(resumen:Resumen,escala=1) {
  return resumen.ic95?resumen.ic95.map(v=>decimal(v*escala)).join(' a '):'No estimable con una réplica';
}
export default function DetalleComparacion({resultado}:{resultado:Experimento}) {
  const [pagina,fijarPagina]=useState(0);
  return <>
    {resultado.diferencias_pareadas.length>0&&<section className="tarjeta"><div className="ceja">MISMAS SEMILLAS, DIFERENCIAS PAREADAS</div><h2>Cambio frente al primer escenario</h2><p>Un valor negativo indica una reducción frente al escenario #0. Los intervalos corresponden a las diferencias entre réplicas emparejadas.</p><div className="tabla-scroll"><table><thead><tr><th>Escenario</th><th>Espera (min), IC 95 %</th><th>Abandono (puntos porcentuales), IC 95 %</th><th>Personas atendidas, IC 95 %</th></tr></thead><tbody>{resultado.diferencias_pareadas.slice(pagina*FILAS_POR_PAGINA,(pagina+1)*FILAS_POR_PAGINA).map(d=><tr key={d.escenario}><td>#{d.escenario} frente a #{d.base}</td>{(['espera_mesa_media','tasa_abandono','personas_atendidas'] as const).map(clave=><td key={clave}>{decimal(d.metricas[clave].media*(clave==='tasa_abandono'?100:1))}<small>{intervalo(d.metricas[clave],clave==='tasa_abandono'?100:1)}</small></td>)}</tr>)}</tbody></table></div><Paginacion total={resultado.diferencias_pareadas.length} pagina={pagina} cambiar={fijarPagina} etiqueta="cambios frente al primer escenario"/></section>}
    <section className="tarjeta"><div className="ceja">CONDICIONES DE REPRODUCCIÓN</div><h2>Semillas y entorno registrados</h2><p className="mono">{resultado.semillas_replicas.join(', ')}</p><div className="campos cuatro">{Object.entries(resultado.version_entorno).map(([nombre,version])=><div key={nombre}><small>{nombre}</small><p>{version}</p></div>)}</div><p className="ayuda">Para reproducir una réplica individual utiliza su configuración exportada y la semilla correspondiente. Versión del modelo: {resultado.version_modelo}.</p></section>
  </>;
}

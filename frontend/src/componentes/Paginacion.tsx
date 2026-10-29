import {ChevronLeft,ChevronRight} from 'lucide-react';

export const FILAS_POR_PAGINA=8;
export default function Paginacion({total,pagina,cambiar,etiqueta,tamano=FILAS_POR_PAGINA}:{total:number;pagina:number;cambiar:(pagina:number)=>void;etiqueta:string;tamano?:number}){
  const paginas=Math.max(1,Math.ceil(total/tamano));
  return <nav className="paginacion" aria-label={`Paginación de ${etiqueta}`}>
    <span role="status">{total?pagina*tamano+1:0}–{Math.min((pagina+1)*tamano,total)} de {total}</span>
    <div><button className="secundario" aria-label={`Página anterior de ${etiqueta}`} disabled={pagina===0} onClick={()=>cambiar(pagina-1)}><ChevronLeft size={16}/></button><span>Página {pagina+1} de {paginas}</span><button className="secundario" aria-label={`Página siguiente de ${etiqueta}`} disabled={pagina>=paginas-1} onClick={()=>cambiar(pagina+1)}><ChevronRight size={16}/></button></div>
  </nav>;
}

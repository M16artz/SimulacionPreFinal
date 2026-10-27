import {useEffect,useRef,useState} from 'react';
import type {Trabajo} from '../tipos/contratos';
import {api,enviar,ErrorApi} from './api';

type Coleccion='simulaciones'|'experimentos';
function ultimaConsulta(coleccion:Coleccion):Trabajo|null {
  try {
    const id=localStorage.getItem(`mesa.${coleccion}.ultima`);
    return id&&/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(id)?{id,estado:'pendiente'}:null;
  } catch {return null;}
}

export function usarTrabajo<T>(coleccion:Coleccion) {
  const [trabajo,fijarTrabajo]=useState<Trabajo|null>(()=>ultimaConsulta(coleccion));
  const [resultado,fijarResultado]=useState<T|null>(null);
  const [error,fijarError]=useState('');
  const [enviando,fijarEnviando]=useState(false);
  const envioActivo=useRef(false);

  useEffect(()=>{
    if(!trabajo)return;
    const id=trabajo.id;
    const controlador=new AbortController();
    let temporizador:number;
    try {localStorage.setItem(`mesa.${coleccion}.ultima`,id);} catch { /* El historial del servidor sigue disponible. */ }
    async function consultar(){
      try {
        const datos=await api<Trabajo>(`/${coleccion}/${id}${coleccion==='experimentos'?'?incluir_resultado=false':''}`,{signal:controlador.signal});
        if(controlador.signal.aborted)return;
        fijarError('');fijarTrabajo(datos);
        if(datos.estado==='completado'){
          const completo=coleccion==='simulaciones'
            ? await api<T>(`/simulaciones/${id}/resultados`,{signal:controlador.signal})
            : (await api<{resultado:T}>(`/experimentos/${id}`,{signal:controlador.signal})).resultado;
          if(!controlador.signal.aborted)fijarResultado(completo);
        } else if(datos.estado==='error') fijarError(datos.error??'No se pudo completar la ejecución.');
        else temporizador=window.setTimeout(consultar,700);
      } catch(fallo) {
        if(controlador.signal.aborted)return;
        const error=fallo as ErrorApi;
        fijarError(error.message);
        // La desconexión del navegador no cambia el estado del trabajo en el servidor.
        if(error.estado===404){
          fijarTrabajo(null);
          try {localStorage.removeItem(`mesa.${coleccion}.ultima`);} catch { /* Almacenamiento local opcional. */ }
        } else temporizador=window.setTimeout(consultar,2500);
      }
    }
    consultar();
    return()=>{controlador.abort();clearTimeout(temporizador);};
  },[trabajo?.id,coleccion]);

  async function ejecutar(solicitud:unknown) {
    if(envioActivo.current)throw new Error('La solicitud ya se está enviando.');
    envioActivo.current=true;fijarEnviando(true);fijarError('');
    try {
      const creado=await api<Trabajo>(`/${coleccion}`,enviar(solicitud));
      try {localStorage.setItem(`mesa.${coleccion}.ultima`,creado.id);} catch { /* Se conserva también en el historial del servidor. */ }
      fijarResultado(null);fijarTrabajo(creado);
      return creado;
    } finally {envioActivo.current=false;fijarEnviando(false);}
  }

  function consultar(id:string) {
    if(id===trabajo?.id)return;
    fijarResultado(null);fijarError('');fijarTrabajo({id,estado:'pendiente'});
  }

  const ocupado=enviando||!!trabajo&&['pendiente','ejecutando'].includes(trabajo.estado);
  return {trabajo,resultado,error,ocupado,ejecutar,consultar};
}

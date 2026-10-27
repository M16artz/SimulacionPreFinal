export class ErrorApi extends Error {
  readonly estado:number;
  constructor(mensaje:string, estado:number=0) {super(mensaje);this.name='ErrorApi';this.estado=estado;}
}

export async function api<T>(ruta:string, opciones?:RequestInit):Promise<T> {
  let respuesta:Response;
  try {
    respuesta = await fetch('/api/v1'+ruta,{...opciones,headers:{'Content-Type':'application/json',...opciones?.headers}});
  } catch(error) {
    if(opciones?.signal?.aborted) throw error;
    throw new ErrorApi('No se pudo conectar con el servidor. Comprueba que la API está disponible.');
  }
  let datos;
  try {datos=await respuesta.json();}
  catch {throw new ErrorApi(`El servidor devolvió una respuesta no válida (HTTP ${respuesta.status}).`,respuesta.ok?502:respuesta.status);}
  if (!respuesta.ok) {
    const detalle = datos.detail;
    throw new ErrorApi(Array.isArray(detalle) ? detalle.map((e:{campo?:string;mensaje?:string;msg?:string})=>`${e.campo??''}: ${e.mensaje??e.msg}`).join('\n') : typeof detalle==='string'?detalle:'No se pudo completar la solicitud',respuesta.status);
  }
  return datos as T;
}
export const enviar = (datos:unknown):RequestInit => ({method:'POST',body:JSON.stringify(datos)});
export function descargar(datos:unknown,nombre:string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(datos,null,2)],{type:'application/json'}));
  const enlace = document.createElement('a'); enlace.href=url; enlace.download=nombre; document.body.append(enlace); enlace.click(); enlace.remove(); window.setTimeout(()=>URL.revokeObjectURL(url),1000);
}

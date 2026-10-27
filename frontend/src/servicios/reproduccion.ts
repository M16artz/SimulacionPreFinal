import type {Evento} from '../tipos/contratos';
export function indiceEnTiempo(eventos:Evento[], tiempo:number) {
  let izquierda=0, derecha=eventos.length-1, encontrado=0;
  while(izquierda<=derecha){const medio=Math.floor((izquierda+derecha)/2);if(eventos[medio].tiempo<=tiempo){encontrado=medio;izquierda=medio+1;}else derecha=medio-1;}
  return encontrado;
}
export function hora(minutos:number) {
  const total=Math.floor(minutos); return `${String(Math.floor(total/60)).padStart(2,'0')}:${String(total%60).padStart(2,'0')}`;
}

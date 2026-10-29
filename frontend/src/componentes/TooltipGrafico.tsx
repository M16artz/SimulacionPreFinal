type Entrada={name?:string|number;value?:unknown;color?:string;unit?:string|number};
export default function TooltipGrafico({active,payload,label}:{active?:boolean;payload?:readonly Entrada[];label?:unknown}){
  if(!active||!payload?.length)return null;
  return <div className="tooltip-grafico">{label!==undefined&&<strong>{String(label)}</strong>}{payload.map((p,i)=><div key={i}><span><i style={{background:p.color}}/>{p.name}</span><b>{typeof p.value==='number'?new Intl.NumberFormat('es-CO',{maximumFractionDigits:2}).format(p.value):String(p.value??'—')} {p.unit}</b></div>)}</div>;
}

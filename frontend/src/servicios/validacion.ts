import Ajv from 'ajv';
import type {Configuracion} from '../tipos/contratos';
const ajv = new Ajv({allErrors:true,strict:false});
export function crearValidador(esquema:object) {
  const validar=ajv.compile(esquema);
  return (datos:Configuracion):string[]=>{
    validar(datos);
    const errores=(validar.errors??[]).map(e=>`${e.instancePath || 'Configuración'}: ${e.keyword==='required'?'falta un campo obligatorio':e.keyword==='minimum'||e.keyword==='maximum'?'valor fuera del rango permitido':e.keyword==='type'?'tipo de dato inválido':'revise los parámetros'}`);
    return errores;
  };
}

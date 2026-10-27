import {test,expect} from '@playwright/test';
test('configurar, simular y reproducir los mismos resultados de la API',async({page,request})=>{
  await page.goto('/');
  await expect(page.getByRole('button',{name:'Ejecutar simulación',exact:true})).toBeEnabled();
  const respuesta=page.waitForResponse(r=>r.url().endsWith('/api/v1/simulaciones')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Ejecutar simulación',exact:true}).click();
  const trabajo=await (await respuesta).json();
  await expect(page.locator('.aviso.exito')).toContainText('Simulación completada',{timeout:60000});
  const resultado=await (await request.get(`http://127.0.0.1:8000/api/v1/simulaciones/${trabajo.id}/resultados`)).json();
  await expect(page.locator('.indicador').first()).toContainText(String(resultado.metricas.personas_atendidas));
  await page.getByRole('button',{name:'Restaurante en vivo',exact:true}).click();
  await expect(page.locator('.mesa')).toHaveCount(resultado.configuracion.mesas);
  const deslizador=page.getByRole('slider',{name:'Posición de reproducción'});
  await deslizador.focus();
  await deslizador.press('End');
  await expect(page.locator('.dato-fila').filter({hasText:'Personas atendidas'})).toContainText(String(resultado.metricas.personas_atendidas));
  await deslizador.press('Home');
  await expect(page.locator('.mesa.ocupada')).toHaveCount(0);
  await page.getByRole('button',{name:'Resultados',exact:true}).click();
  await expect(page.getByText('Resultados que puedes reproducir')).toBeVisible();
  await expect(page.getByRole('link',{name:'JSON completo'})).toHaveAttribute('href',`/api/v1/simulaciones/${trabajo.id}/exportar?formato=json`);
  await page.reload();
  await expect(page.locator('.indicador').first()).toContainText(String(resultado.metricas.personas_atendidas));
  await page.setViewportSize({width:390,height:844});
  await page.getByRole('button',{name:'Abrir navegación'}).click();
  await page.getByRole('button',{name:'Resultados',exact:true}).click();
  await expect(page.getByText('Resultados que puedes reproducir')).toBeVisible();
});

test('duplicar, guardar, restaurar y rechazar probabilidades inválidas',async({page})=>{
  await page.goto('/');
  await expect(page.getByRole('button',{name:'Ejecutar simulación',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Configuración',exact:true}).click();
  await page.getByRole('button',{name:'Duplicar',exact:true}).click();
  await expect(page.locator('.aviso.exito')).toContainText('Copia independiente creada');
  const nombre=page.getByLabel('Nombre del escenario');
  const etiqueta=`Escenario de prueba ${Date.now()}`;
  await nombre.fill(etiqueta);
  await page.getByRole('button',{name:'Guardar',exact:true}).click();
  await expect(page.locator('.aviso.exito')).toContainText('Configuración guardada');
  await nombre.fill('Cambio sin guardar');
  await page.getByRole('button',{name:'Restaurar versión guardada'}).click();
  await expect(nombre).toHaveValue(etiqueta);
  await page.getByLabel('1 persona (%)',{exact:true}).fill('100');
  await expect(page.getByRole('alert')).toContainText('probabilidades');
  await page.getByRole('button',{name:'Guardar',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('probabilidades');
});

test('importar pendientes conserva null y bloquea su ejecución',async({page,request})=>{
  const lista=await (await request.get('http://127.0.0.1:8000/api/v1/configuraciones')).json();
  const configuracion=structuredClone(lista.find((g:{configuracion:{sintetica:boolean}})=>g.configuracion.sintetica).configuracion);
  configuracion.nombre='Referencia importada con pedido pendiente';
  configuracion.tiempos.pedido=null;
  await page.goto('/');
  await expect(page.getByRole('button',{name:'Ejecutar simulación',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Configuración',exact:true}).click();
  await page.locator('input[type=file]').setInputFiles({name:'pendiente.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(configuracion))});
  await expect(page.getByLabel('Nombre del escenario')).toHaveValue(configuracion.nombre);
  await expect(page.getByRole('alert')).toContainText('pedido');
  await page.getByRole('button',{name:'Ejecutar simulación',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Faltan tiempos por aprobar');
});

test('comparar rangos con réplicas y consultar diferencias y sensibilidad',async({page})=>{
  await page.goto('/');
  await expect(page.getByRole('button',{name:'Ejecutar simulación',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Experimentos',exact:true}).click();
  await page.getByLabel('Réplicas por escenario').fill('2');
  await page.getByLabel('Evaluar combinaciones en rangos').check();
  for(const [recurso,minimo,maximo] of [['mesas','11','11'],['meseros','1','2'],['cocineras','3','3']]){
    await page.getByLabel(`${recurso} minimo`,{exact:true}).fill(minimo);
    await page.getByLabel(`${recurso} maximo`,{exact:true}).fill(maximo);
    await page.getByLabel(`${recurso} paso`,{exact:true}).fill('1');
  }
  await page.getByRole('button',{name:'Ejecutar experimento',exact:true}).click();
  await expect(page.getByRole('heading',{name:'2 escenarios · 2 réplicas'})).toBeVisible({timeout:60000});
  await expect(page.getByRole('heading',{name:'Cambio frente al primer escenario'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Qué cambia al añadir una unidad'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Semillas y entorno registrados'})).toBeVisible();
});

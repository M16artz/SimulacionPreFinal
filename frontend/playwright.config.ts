import {defineConfig} from '@playwright/test';
import {fileURLToPath} from 'node:url';
const python=process.env.RESTAURANTE_E2E_PYTHON??fileURLToPath(new URL(process.platform==='win32'?'../.venv/Scripts/python.exe':'../.venv/bin/python',import.meta.url));
const fuenteBackend=fileURLToPath(new URL('../backend/src',import.meta.url));
const puertoApi=Number(process.env.RESTAURANTE_E2E_PUERTO_API??18000);
const puertoWeb=Number(process.env.RESTAURANTE_E2E_PUERTO_WEB??15173);
const api=`http://127.0.0.1:${puertoApi}`,web=`http://127.0.0.1:${puertoWeb}`;
export default defineConfig({testDir:'./tests/e2e',workers:1,timeout:90000,use:{baseURL:web,headless:true,launchOptions:process.env.RESTAURANTE_E2E_CHROMIUM?{executablePath:process.env.RESTAURANTE_E2E_CHROMIUM}:undefined,trace:'retain-on-failure'},webServer:[{command:`"${python}" -m uvicorn restaurante.api.principal:app --app-dir "${fuenteBackend}" --host 127.0.0.1 --port ${puertoApi}`,env:{RESTAURANTE_DATOS:fileURLToPath(new URL('../datos/e2e',import.meta.url))},url:`${api}/api/v1/salud`,reuseExistingServer:false},{command:`npm run dev -- --port ${puertoWeb} --strictPort`,env:{RESTAURANTE_API_URL:api},url:web,reuseExistingServer:false}]});

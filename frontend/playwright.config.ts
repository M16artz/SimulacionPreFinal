import {defineConfig} from '@playwright/test';
import {fileURLToPath} from 'node:url';
const python=process.platform==='win32'?'../.venv/Scripts/python.exe':'../.venv/bin/python';
export default defineConfig({testDir:'./tests/e2e',workers:1,timeout:90000,use:{baseURL:'http://127.0.0.1:5173',headless:true,trace:'retain-on-failure'},webServer:[{command:`${python} -m uvicorn restaurante.api.principal:app --app-dir ../backend/src --host 127.0.0.1 --port 8000`,env:{RESTAURANTE_DATOS:fileURLToPath(new URL('../datos/e2e',import.meta.url))},url:'http://127.0.0.1:8000/api/v1/salud',reuseExistingServer:false},{command:'npm run dev',url:'http://127.0.0.1:5173',reuseExistingServer:false}]});

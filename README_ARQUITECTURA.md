# Manual Tecnico y Arquitectura del Sistema - Dulce Espera Inventario (Backend)

Este documento contiene las directrices de arquitectura, limites de seguridad y procedimientos de despliegue para el backend de Dulce Espera.

---

## 1. REGLA CRITICA: Aislamiento y Convivencia en el Servidor VPS (107.172.193.34)

El servidor VPS `107.172.193.34` aloja el CRM Hospitalario y admisiones de la clinica.

- **PROHIBIDO ejecutar `reboot`:** Apagara el servidor para todos los sistemas medicos.
- **PROHIBIDO ejecutar `killall python`:** Puede matar procesos del sistema operativo.
- **PROHIBIDO reiniciar MySQL o Apache globalmente (`systemctl restart mysqld` o `httpd`).**
- **SERVICIO SYSTEMD EXCLUSIVO:** `dulce_espera_backend.service`
- **DIRECTORIO EN VPS:** `/opt/dulce_espera_backend`
- **ENTORNO VIRTUAL PYTHON:** `/opt/dulce_espera_backend/venv`
- **ESQUEMA DE BASE DE DATOS:** Unicamente `dulce_espera`
- **USUARIO DB:** `app_dulce_espera`

### Comando Unico de Reinicio Autorizado:
```bash
sudo systemctl restart dulce_espera_backend
```

### Verificacion Obligatoria:
```bash
sudo systemctl status dulce_espera_backend --no-pager
curl -s http://127.0.0.1:8000/health
```

---

## 2. Motores de Reporte (OpenPyXL y xhtml2pdf)

El backend incorpora dos generadores oficiales de reportes:
1. **Excel nativo con OpenPyXL:**
   - `GET /pedidos/{id_publico}/reporte/excel`: Genera el archivo `.xlsx` estilizado con la paleta de Clinica Montalvo (`#006156`), tablas segmentadas por canal (`Mercado`, `Super Mercado`, `Proveedor`, `Otros`), formulas dinámicas de sumatoria `=SUM(...)`, casillas de control fisico y firmas.
   - `GET /api/pedidos/pendientes/excel`: Hoja maestra que consolida todos los requerimientos pendientes agrupados por canal para la gobernanta.
2. **PDF vectorial con xhtml2pdf:**
   - `GET /pedidos/{id_publico}/reporte/pdf`: Reporte en PDF estructurado por canal.

---

## 3. Procedimiento de Despliegue en Produccion (Runbook)

```bash
# 1. Desde tu estacion local:
git add .
git commit -m "feat: mejoras en backend"
git push origin main

# 2. En el servidor VPS:
ssh root@107.172.193.34
cd /opt/dulce_espera_backend
git pull origin main
/opt/dulce_espera_backend/venv/bin/pip install -r requirements.txt
sudo systemctl restart dulce_espera_backend
curl -s http://127.0.0.1:8000/health
```

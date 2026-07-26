# Guía de Despliegue — Backend FastAPI "Dulce Espera"

Este documento explica cómo configurar, ejecutar y desplegar el backend de la aplicación en entornos de desarrollo y producción.

---

## 1. Configuración de Variables de Entorno

El backend utiliza `pydantic-settings` para cargar la configuración. Las variables se leen del archivo `.env` en la raíz de la carpeta `backend`, pero las variables del sistema (definidas en el shell o en Systemd) tienen prioridad.

Hemos preparado tres archivos de entorno:
*   `.env`: Archivo activo que lee FastAPI.
*   `.env.development`: Plantilla con orígenes CORS permitidos para desarrollo (`localhost:3000`, `localhost:5173`).
*   `.env.production`: Plantilla lista para producción, limitando CORS al dominio real de la PWA.

### Para cambiar de entorno:
En **desarrollo**, copia el contenido correspondiente a `.env`:
```bash
cp .env.development .env
```
En **producción**, copia el contenido correspondiente a `.env` y edita la contraseña de base de datos con una segura:
```bash
cp .env.production .env
nano .env  # Reemplaza CAMBIAR_POR_UNA_CONTRASENA_PROD_MUY_SEGURA con el valor real
```

---

## 2. Ejecución en Desarrollo

Para ejecutar el servidor localmente con recarga automática:

```bash
# 1. Asegúrate de estar en el directorio /backend y tener el entorno virtual activado
cd /home/httpreen/Documentos/inventario/backend
source venv/bin/activate

# 2. Ejecuta uvicorn
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
La documentación interactiva de la API estará disponible en `http://127.0.0.1:8000/docs`.

---

## 3. Despliegue en Producción (Systemd + Nginx + HTTPS)

### Paso A: Configurar el Servicio en Linux (Systemd)

Para que el backend corra en segundo plano de manera persistente y se reinicie solo si el servidor se apaga o falla:

1.  Copia el archivo de servicio a systemd:
    ```bash
    sudo cp deployment/dulce_espera_backend.service /etc/systemd/system/dulce_espera_backend.service
    ```
2.  *(Opcional)* Edita el archivo en `/etc/systemd/system/dulce_espera_backend.service` si tu ruta de usuario o de instalación varía (actualmente configurado para el usuario `httpreen` y la ruta `/home/httpreen/Documentos/inventario/backend`).
3.  Habilita e inicia el servicio:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable dulce_espera_backend
    sudo systemctl start dulce_espera_backend
    ```
4.  Comprueba el estado del servicio:
    ```bash
    sudo systemctl status dulce_espera_backend
    ```

### Paso B: Configurar Nginx como Proxy Inverso

Nginx recibirá las conexiones del puerto 80 (HTTP) y 443 (HTTPS) y las redirigirá internamente al puerto 8000.

1.  Copia el archivo de configuración a Nginx:
    ```bash
    sudo cp deployment/nginx.conf /etc/nginx/sites-available/dulce_espera_backend
    ```
2.  Edita el archivo para configurar tu dominio real (reemplaza `api.dulceespera.yourdomain.com`):
    ```bash
    sudo nano /etc/nginx/sites-available/dulce_espera_backend
    ```
3.  Habilita el sitio creando un enlace simbólico a `sites-enabled`:
    ```bash
    sudo ln -s /etc/nginx/sites-available/dulce_espera_backend /etc/nginx/sites-enabled/
    ```
4.  Prueba que la sintaxis de Nginx sea correcta:
    ```bash
    sudo nginx -t
    ```
5.  Reinicia Nginx:
    ```bash
    sudo systemctl restart nginx
    ```

### Paso C: Habilitar HTTPS con Certbot (Let's Encrypt)

Para asegurar la conexión mediante TLS/SSL de forma gratuita y automática:

1.  Instala Certbot y el plugin de Nginx:
    ```bash
    sudo apt update
    sudo apt install certbot python3-certbot-nginx
    ```
2.  Genera el certificado SSL (Certbot modificará automáticamente tu archivo de Nginx para usar SSL):
    ```bash
    sudo certbot --nginx -d api.dulceespera.yourdomain.com
    ```
3.  Sigue las instrucciones en pantalla. Certbot renovará automáticamente tus certificados antes de que expiren. Puedes comprobarlo ejecutando:
    ```bash
    sudo certbot renew --dry-run
    ```

---

## 4. Notas Importantes sobre Seguridad y Red

*   **Acceso a MySQL (107.172.193.34):** Asegúrate de que el servidor donde corre FastAPI tiene su IP pública permitida en el firewall del servidor de MySQL en el puerto `3306`.
*   **Permisos de MySQL:** El usuario `app_dulce_espera` solo requiere permisos de `SELECT` para la tabla `insumos`, e `INSERT, UPDATE, SELECT` para las tablas `pedidos` y `detalle_pedido`. No debe otorgarse permisos de escritura sobre `insumos`.
*   **CORS (Cross-Origin Resource Sharing):** La PWA bloqueará las respuestas si su dominio no coincide exactamente con los dominios permitidos configurados en el `.env` (variable `CORS_ORIGINS`). Asegúrate de que estén correctamente configurados.

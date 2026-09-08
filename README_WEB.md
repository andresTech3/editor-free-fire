# 📱 Código Headshot Studio — Edición Móvil & Web

Plataforma web y móvil para generar videos profesionales y virales de **Free Fire** automáticamente a partir de un audio de locución y recursos de juego.

---

## 🚀 Inicio Rápido (En tu PC y Celular por Wi-Fi)

### 1. Iniciar con 1 Clic en PC
Haz doble clic sobre el archivo:
```
Iniciar_Web_Studio_Movil.bat
```
El script detectará automáticamente tu dirección IP local y abrirá la interfaz en tu navegador.

### 2. Abrir en tu Celular (iOS Safari o Android Chrome)
Asegúrate de que tu celular esté conectado a la **misma red Wi-Fi** que tu PC.
Abre el navegador en tu celular e ingresa la dirección mostrada en la consola, por ejemplo:
```
http://192.168.1.2:8000
```
> 💡 **Instalación como App Nativa (PWA):**  
> - En **iPhone / Safari**: Toca el botón **Compartir** y selecciona **"Agregar al Inicio"**.  
> - En **Android / Chrome**: Toca el menú (tres puntos) y selecciona **"Instalar aplicación"** o **"Agregar a pantalla principal"**.

---

## 🎯 Flujo de Uso

1. **Paso 1: Audio de Locución**  
   Sube tu archivo de narración (`.mp3`, `.wav`, `.m4a`). Puedes reproducirlo al instante en el reproductor integrado.
2. **Paso 2: Recursos Visuales**  
   - **Pack Oficial Maestro (Por defecto):** Utiliza los 37 clips de jugadas analizadas, 282 memes (con detección automática de fondo verde), armas evolutivas y diamantes ya integrados en el proyecto.  
   - **Subir Mis Recursos:** Sube tu propia carpeta de clips o imágenes. El motor investigará automáticamente la orientación (90°/180°), tiros a la cabeza (números rojos) y transparencias.
3. **Paso 3: Formato de Video**  
   - **Shorts / TikTok (9:16):** Pantalla completa con zoom adaptativo al personaje, sin franjas borrosas, con memes en pantalla y subtítulos dinámicos.  
   - **YouTube (16:9):** Widescreen panorámico 1080p con la **Intro Oficial completa de 10s** después del hook inicial.
4. **Paso 4: Crear Video**  
   Presiona **"CREAR VIDEO PROFESIONAL"**. Verás la barra de progreso en vivo, las etapas activas y la terminal con logs en tiempo real.
5. **Paso 5: Previsualizar y Descargar**  
   Al terminar, el reproductor de video te mostrará el resultado y podrás descargarlo directamente a la galería de tu celular o PC.

---

## ☁️ Despliegue en GitHub y la Nube

### 1. Subir a GitHub
```bash
git add .
git commit -m "Add mobile web studio and asset investigator"
git push origin main
```

### 2. Despliegue en Hugging Face Spaces (Docker Gratuito)
1. Crea un nuevo Space en [Hugging Face](https://huggingface.co/spaces).
2. Selecciona SDK: **Docker**.
3. Conecta tu repositorio de GitHub o sube este repositorio.
4. Hugging Face compilará automáticamente el `Dockerfile` con FFmpeg y expondrá la URL pública HTTPS accesible desde cualquier teléfono en el mundo.

### 3. Despliegue en Render / Railway / VPS
- Usa el `Dockerfile` provisto.
- Expone el puerto `8000` (definido en la variable `$PORT`).
- Comando de ejecución: `python web_server.py`.

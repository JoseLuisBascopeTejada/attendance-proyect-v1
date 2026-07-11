# FRONTEND_TASKS.md — Tareas del Frontend

> Todas las tareas del frontend organizadas por fase. Cada tarea incluye archivos a crear/modificar, que hacer, y criterios de aceptacion.

---

## FASE 1: Base (sin tareas frontend)

> No hay tareas frontend en FASE 1. El frontend espera a que el backend tenga DB y endpoints basicos.

---

## FASE 2: Registro de Estudiantes

### F1. Crear src/api/client.ts — instancia axios
- **Archivos:** src/api/client.ts (crear)
- **Descripcion:**
  - Instancia axios con baseURL apuntando al backend (http://localhost:8000)
  - Interceptor para manejar errores (mostrar alerta o toast)
  - Exportar apiClient para uso en toda la app
- **Criterio:** import { apiClient } from './api/client' funciona sin errores

### F2. Crear src/components/WebcamCapture.tsx — componente de camara
- **Archivos:** src/components/WebcamCapture.tsx (crear)
- **Descripcion:**
  - Componente reutilizable usando react-webcam
  - Props: onCapture(imageSrc: string), width?, height?
  - Boton "Capturar foto" que toma snapshot y retorna imagen como string (base64)
  - Mostrar preview de la foto capturada
  - **Mirror mode (modo espejo):** Aplicar `style={{ transform: 'scaleX(-1)' }}` al video de react-webcam para que la imagen se vea como un espejo (mas natural para el usuario). La imagen capturada se envia sin flip para que el backend la procese correctamente.
- **Criterio:** Componente renderiza camara con efecto espejo, captura foto, llama onCapture

### F3. Crear src/pages/Register.tsx — pagina de registro
- **Archivos:** src/pages/Register.tsx (crear)
- **Descripcion:**
  - Formulario: campo "Nombre" + componente WebcamCapture
  - Al enviar: convertir imagen base64 a Blob, enviar POST /register con FormData
  - **Headers explicitos:** Configurar `Content-Type: 'multipart/form-data'` en la peticion axios para que FastAPI interprete correctamente el FormData:
    ```typescript
    apiClient.post('/register', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    ```
  - Mostrar spinner durante envio
  - Mostrar mensaje de exito (con ID del estudiante) o error (sin cara, calidad baja)
  - Limpiar formulario despues de exito
- **Depende:** F1, F2
- **Criterio:** Flujo completo: escribir nombre, capturar foto, enviar, ver confirmacion

### F4. Reemplazar src/App.tsx con React Router
- **Archivos:**
  - src/App.tsx (modificar)
  - src/App.css (modificar o vaciar)
  - src/index.css (modificar estilos globales)
- **Descripcion:**
  - Configurar BrowserRouter con rutas:
    - /, Dashboard (FASE 4, por ahora placeholder)
    - /register, Register
    - /recognize, Recognize (FASE 3, por ahora placeholder)
  - Eliminar todo el scaffold Vite (counter, logos, links)
  - Estilos globales limpios (fondo, tipografia)
- **Criterio:** Navegar entre /register y / funciona, sin errores de consola

---

## FASE 3: Reconocimiento y Asistencia

### F5. Crear src/pages/Recognize.tsx — reconocimiento individual
- **Archivos:** src/pages/Recognize.tsx (crear)
- **Descripcion:**
  - WebcamCapture para tomar foto en vivo
  - Al capturar: enviar POST /recognize con imagen
  - **Headers explicitos:** Configurar `Content-Type: 'multipart/form-data'` en la peticion axios:
    ```typescript
    apiClient.post('/recognize', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    ```
  - Mostrar resultado: nombre del estudiante + distancia + confianza
  - Si no hay match: mostrar "Rostro no reconocido"
  - Mostrar estado: "Analizando..." durante la peticion
- **Depende:** F1, F2, F4
- **Criterio:** Capturar foto, ver nombre del estudiante reconocido

### F6. Crear src/pages/RecognizeGroup.tsx — reconocimiento grupal
- **Archivos:** src/pages/RecognizeGroup.tsx (crear)
- **Descripcion:**
  - Boton "Tomar foto grupal" (captura una imagen)
  - Enviar POST /recognize-group con imagen
  - Mostrar lista de personas reconocidas (nombre, distancia)
  - Contador: "X personas reconocidas de Y en la foto"
  - **Nota tecnica — Performance:** Redimensionar la imagen capturada a un maximo de 800px de ancho antes de enviarla al backend. Esto reduce significativamente el tiempo de inferencia de IA (DeepFace) y el ancho de banda. Usar canvas para redimensionar:
    ```typescript
    const canvas = document.createElement('canvas');
    const MAX_WIDTH = 800;
    const ratio = MAX_WIDTH / img.width;
    canvas.width = MAX_WIDTH;
    canvas.height = img.height * ratio;
    canvas.getContext('2d')?.drawImage(img, 0, 0, canvas.width, canvas.height);
    const resizedBlob = await new Promise<Blob>((resolve) =>
      canvas.toBlob((b) => resolve(b!), 'image/jpeg', 0.85)
    );
    ```
- **Depende:** F1, F2, F4
- **Criterio:** Foto grupal muestra todos los rostros reconocidos; imagen redimensionada se envia correctamente

---

## FASE 4: Dashboard y Reportes

### F7. Crear src/pages/Layout.tsx — layout con navegacion
- **Archivos:** src/pages/Layout.tsx (crear)
- **Descripcion:**
  - Header con nombre del sistema "Sistema de Asistencia"
  - Sidebar o barra de navegacion con links:
    - Dashboard (/)
    - Registrar (/register)
    - Reconocer (/recognize)
    - Reconocimiento Grupal (/recognize-group)
  - Outlet para contenido de rutas hijas
  - Estilo limpio y profesional
- **Depende:** F4
- **Criterio:** Navegacion funciona, layout se muestra en todas las paginas

### F8. Crear src/pages/Dashboard.tsx — tabla de asistencia
- **Archivos:** src/pages/Dashboard.tsx (crear)
- **Descripcion:**
  - Llamar GET /attendance?page=X&limit=10 al cargar y al cambiar pagina
  - Tabla con columnas: #, Nombre, Fecha, Hora
  - Paginacion: botones Anterior/Siguiente, indicador "Pagina X de Y"
  - Filtros: date_from (input date), date_to (input date), boton "Filtrar"
  - Loading spinner durante carga
  - Mensaje "No hay registros" si respuesta vacia
- **Depende:** F1, F7
- **Criterio:** Tabla muestra registros reales, paginacion funciona

### F9. Agregar boton de descarga PDF
- **Archivos:** src/pages/Dashboard.tsx (modificar)
- **Descripcion:**
  - Boton "Descargar PDF" en el header del dashboard
  - Al clickear: llamar GET /report/pdf con filtros actuales
  - Descargar archivo como asistencia_YYYY-MM-DD.pdf
  - Usar apiClient con responseType: 'blob'
- **Depende:** F1, F8
- **Criterio:** Boton descarga PDF con datos correctos

### F10. Agregar tarjetas de resumen
- **Archivos:** src/pages/Dashboard.tsx (modificar)
- **Descripcion:**
  - Dos tarjetas arriba de la tabla:
    - "Asistentes hoy: X" (contar registros de hoy)
    - "Estudiantes registrados: X" (llamar GET /students y contar)
  - Estilo: cards con fondo de color, numero grande, label pequeno
- **Depende:** F1, F8
- **Criterio:** Tarjetas muestran numeros reales actualizados

### F11. Verificar lint
- **Comando:**
  ```bash
  cd frontend && pnpm run lint
  ```
- **Depende:** F3, F5, F6, F7, F8
- **Criterio:** 0 errores, 0 warnings

### F12. Verificar build
- **Comando:**
  ```bash
  cd frontend && pnpm run build
  ```
- **Depende:** F11
- **Criterio:** Build exitoso, dist/ generado sin errores

---

## Resumen

| Fase | Tareas | Archivos a crear/modificar |
|------|--------|---------------------------|
| FASE 1 | — | — |
| FASE 2 | F1, F2, F3, F4 | api/client.ts, components/WebcamCapture.tsx, pages/Register.tsx, App.tsx |
| FASE 3 | F5, F6 | pages/Recognize.tsx, pages/RecognizeGroup.tsx |
| FASE 4 | F7, F8, F9, F10, F11, F12 | pages/Layout.tsx, pages/Dashboard.tsx |

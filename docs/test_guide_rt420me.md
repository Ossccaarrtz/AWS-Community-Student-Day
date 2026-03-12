# Guía de Validación para Impresora Ribetec RT-420ME

Esta guía está diseñada para la persona que tiene físicamente la impresora conectada y va a ejecutar las pruebas de compatibilidad. El objetivo es confirmar que la **Ribetec RT-420ME** puede recibir trabajos generados por nuestro sistema web usando el Driver de Sistema Windows.

---

## Prerrequisitos (Pasos 1 a 4)

### PASO 1: Instalar Driver de la Impresora
1. Descarga e instala los drivers oficiales de Ribetec RT-420ME (normalmente provistos con CD o descarga web del fabricante).
2. Sigue las instrucciones del instalador.

### PASO 2: Conectar la Impresora
1. Conecta el cable USB de la impresora a la PC Windows.
2. Asegúrate de que la impresora esté encendida.
3. Asegúrate de tener rollo de etiquetas de **3 x 2 pulgadas** cargado.

### PASO 3: Verificar en Windows
1. Ve a `Configuración > Dispositivos > Impresoras y escáneres` (o Panel de Control).
2. Revisa que la "Ribetec RT-420ME" (o un nombre similar) aparezca en la lista y no tenga advertencias de error.
3. Puedes hacer una "Impresión de página de prueba" desde las propiedades de Windows para confirmar.

### PASO 4: Levantar el Backend Localmente
Para ejecutar la prueba local, el backend debe estar corriendo.
1. Abre una terminal y dirígete a la carpeta `backend/` del proyecto.
2. Inicia el servidor (por ejemplo, `uvicorn main:app --reload`).
3. Comprueba que no hay errores en la consola y dice "Application startup complete".

---

## Ejecución de las Pruebas (Paso 5)

Hemos preparado un script interactivo para hacerte todo el trabajo pesado.
 
1. Abre otra ventana de terminal en la carpeta `backend/`.
2. Ejecuta el archivo:
   ```bash
   python scripts/validate_rt420me.py
   ```
3. El script buscará impresoras conectadas y te mostrará una lista numerada. 
   - **Ejemplo**: `[1] Ribetec RT-420ME (Tipo: system_queue, Detalles: ...)`
4. Selecciona el número correspondiente a la Ribetec RT-420ME.
5. Te preguntará el modo de ejecución:
   - Presiona `3` para **IMPRESIÓN REAL**.
6. El script ejecutará automáticamente 4 pruebas seguidas, y luego te preguntará si deseas hacer una prueba de estrés (5 etiquetas).

---

## Verificación Visual (Paso 6)

Por favor, inspecciona las etiquetas físicas que acaban de salir de la impresora usando el siguiente checklist:

- [ ] **TEST 1 (Simple):** ¿El texto "TEST RT-420ME" se ve grande y centrado? ¿El tamaño de letra es legible?
- [ ] **TEST 2 (QR):** Escanea el código QR con la cámara de tu celular. ¿Lee correctamente el código? ¿El margen es respetado de forma que el QR no se corte?
- [ ] **TEST 3 (Barcode):** Inspecciona el código de barras (Code128). ¿Tiene líneas nítidas sin artefactos térmicos por calor excesivo? (Si puedes probar leerlo con un scanner, hazlo).
- [ ] **TEST 4 (Layout de Evento):** ¿El nombre, datos de empresa y QR están encuadrados sin rebasar los límites del papel de 3x2?
- [ ] **Velocidad y Comportamiento General:** ¿La impresora imprime de inmediato o tiene retrasos notables al pausar/reiniciar entre etiquetas?

---

## Diagnóstico Interpretación

Cada prueba genera 3 archivos técnicos en la carpeta `backend/printer_jobs/` por si surge algún error (donde `job_ID` es un código de fecha y hora):

1. **`job_ID_preview.png`**: Una imagen exacta de lo que le enviamos a imprimir. *Si la imagen de este archivo se ve incorrecta, el fallo es de nuestro renderizador, no de la impresora.*
2. **`job_ID.prn`**: Los bytes crudos enviados al driver o a la impresora. Útil para debugear.
3. **`job_ID_metadata.json`**: El registro que indica desde qué puerto se conectó, si tuvo fallos y qué tamaño nosotros definimos (3x2 pulgadas, a 203 DPI).

### Tabla de Resolución de Errores

| Error Visible / Síntoma | Significado & Causa Posible | Acción Recomendada |
|-------------------------|------------------------------|--------------------|
| La impresora no sale en la lista script (Paso 5) | El backend no puede verla mediante el WMI o PyUsb | Asegura que en Panel de Control sí aparece y está enchufada. Corre el modo Administrador. |
| El script dice EXITO pero no imprime nada | Probablemente el driver retuvo la cola de impresión (`Spooler`) o el puerto local está mal configurado. | Abre la cola de Windows. Si el trabajo está atascado, checa el cable o el puerto asignado. |
| Imprime pero la etiqueta sale cortada o saltando páginas | El sensor de la impresora no detectó el "Gap" (separación) entre etiquetas. | Pulsa el botón "Feed" de la impresora un par de veces para que calibre el papel. |
| El código QR o Barcode escanean mal o se ven borrosos | La densidad de calor y velocidad o el tipo de rasterizado causó estiramiento. | Hay que revisar el archivo `job_ID.prn`. El DPI real quizás no coincide con 203. |
| Dice ERROR: USB/SPOOLER_ERROR | El transporte arrojó una excepción. | Revisa el `error_message` en la consola. Es frecuente si no se instaló Python pywin32 o el acceso fue bloqueado. |

---

## Reporte Final

Cuando termines:
1. Reúne las etiquetas impresas (incluso las malas si las hay).
2. Comprime (ZIP) la carpeta `backend/printer_jobs/` si hubo algún test que fallara de manera inexplicable.
3. Envía el Checklist (Paso 6) con tus observaciones al equipo de desarrollo para que verifiquen el resultado del Validation Plan.

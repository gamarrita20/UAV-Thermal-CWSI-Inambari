# Análisis de Estrés Hídrico (CWSI) con Drones Térmicos (DJI Mavic 2 Enterprise) en Zonas Degradadas por Minería (Inambari, Madre de Dios)

Este repositorio contiene el flujo de trabajo completo en Python para el procesamiento de imágenes térmicas capturadas con un vehículo aéreo no tripulado **DJI Mavic 2 Enterprise**, abarcando desde la decodificación radiométrica de archivos crudos R-JPEG y reconstrucción de metadatos geoespaciales, hasta la generación del **Índice de Estrés Hídrico de Cultivos/Vegetación (CWSI)** y extracción de estadísticas zonales en parcelas de restauración ecológica en Inambari (Madre de Dios, Perú).

---

## 🚁 Contexto Técnico: El Formato R-JPEG del DJI Mavic 2 Enterprise

El sensor dual del **DJI Mavic 2 Enterprise** almacena simultáneamente fotografías visibles (RGB) e imágenes térmicas en formato **R-JPEG (Radiometric JPEG)** con una resolución de **640x512 píxeles**. 

A diferencia de las cámaras FLIR tradicionales que entregan directamente un archivo TIFF de 1 banda con temperaturas, DJI encapsula la matriz radiométrica dentro de metadatos privados en un archivo JPG visual de 3 bandas (8 bits). Si estas imágenes se ingresan directamente a un software fotogramétrico (WebODM, Agisoft Metashape o Pix4D), el programa procesa únicamente los colores visuales (valores de 0 a 255) y **se pierde por completo la información de temperatura real en grados Celsius (°C)**.

Para solucionar esto y obtener un archivo equivalente a una **banda térmica pura (tipo FLIR de 32 bits)** apta para fotogrametría científica, este proyecto implementa un flujo de tres etapas:

---

## 📋 Etapas del Flujo de Trabajo

### Etapa 1: Separación de Imágenes, Conversión SDK y Restauración de Coordenadas (`01_preprocesamiento_sdk`)

1. **Separación Automática (RGB vs. Térmico)**: El script clasifica las fotografías originales del vuelo identificando la resolución nativa del sensor térmico (**640x512**) frente a la cámara RGB, separándolas en directorios independientes.
2. **Extracción de Banda Térmica Pura (`dji_irp.exe`)**: Se invoca por línea de comandos el **DJI Thermal SDK** aplicando los parámetros microclimáticos de Inambari (emisividad $\varepsilon = 0.96$, humedad relativa del **75%**, temperatura reflejada de **28.0°C**). El SDK decodifica cada R-JPEG y extrae un archivo binario (`.raw`) que luego se convierte en una matriz `.tif` de **1 sola banda en formato `float32`** (donde cada píxel contiene el valor exacto en °C).
3. **Re-inyección de Coordenadas GPS y Gimbal con ExifTool (`exiftool.exe`)**: Al crear un archivo `.tif` nuevo desde cero a partir de la matriz numérica, la imagen queda "ciega" (pierde la latitud, longitud, altitud y los ángulos de inclinación Roll/Pitch/Yaw del dron). El script ejecuta automáticamente **ExifTool** para clonar todas las etiquetas `EXIF`, `GPS` y `XMP-drone-dji` desde el archivo R-JPEG original hacia el nuevo `.tif` de 1 banda.

#### ⚠️ Requisitos Obligatorios en la Carpeta `01_preprocesamiento_sdk/`
Para que el script `01_separar_y_convertir_sdk.py` funcione sin errores de rutas, **los programas ejecutables deben estar ubicados exactamente dentro de la misma carpeta del script**:

1. **Configuración de ExifTool**:
   - Descargar la versión ejecutable para Windows (*Windows Executable*) desde [exiftool.org](https://exiftool.org/).
   - Descomprimir el archivo `.zip`. Adentro encontrarás un archivo llamado `exiftool(-k).exe` y una carpeta llamada `exiftool_files`.
   - **Renombrar** `exiftool(-k).exe` a **`exiftool.exe`**.
   - Copiar tanto **`exiftool.exe`** como la carpeta **`exiftool_files`** directamente dentro de la carpeta `01_preprocesamiento_sdk/`.

2. **Configuración del DJI Thermal SDK**:
   - Descargar el **DJI Thermal SDK** desde el portal de desarrolladores de DJI.
   - Ir a la subcarpeta del SDK: `utility/bin/windows/release_x64/`.
   - Copiar el ejecutable **`dji_irp.exe`** junto con todas sus librerías dinámicas (**`libdirp.dll`**, **`libv_dirp.dll`**, **`libv_girp.dll`**, **`libv_iirp.dll`** y **`libv_list.ini`**) y pegarlos directamente dentro de la carpeta `01_preprocesamiento_sdk/`.

---

### Etapa 2: Ortomosaico Fotogramétrico (`02_fotogrametria_odm`)

Una vez generados los archivos `.tif` de 1 banda con coordenadas GPS incrustadas, se procesan en **WebODM** (sistema de coordenadas **WGS 1984 UTM Zona 19S - EPSG:32719**). Debido a la baja resolución espacial del sensor térmico (**640x512**), se configura el alineamiento con `--feature-quality ultra` y `--radiometric-calibration none` para conservar intactos los grados Celsius en el ortomosaico final.

---

### Etapa 3: Cálculo del Índice CWSI y Estadísticas por Parcela (`03_analisis_cwsi`)

El script `02_diagnostico_y_cwsi.py` (y su versión para Google Colab) toma los ortomosaicos consolidados de cada fecha de vuelo (**08/09/2026** y **09/09/2026**) y ejecuta:

1. **Diagnóstico y Limpieza Radiométrica**: Eliminación de bordes fotogramétricos vacíos (`0` convertidos a `NaN`) y filtrado de reflejos especulares anómalos.
2. **Modelamiento del CWSI**: Normalización térmica píxel por píxel mediante la ecuación empírica:
   $$CWSI = \frac{T_{surf} - T_{wet}}{T_{dry} - T_{wet}}$$
   Donde $T_{surf}$ es la temperatura superficial del ortomosaico, $T_{wet}$ el límite inferior de referencia (vegetación con máxima transpiración / agua) y $T_{dry}$ el límite superior (suelo degradado desnudo sin transpiración).
3. **Extracción Zonal y Cartografía**: Cruce espacial con los polígonos de evaluación (`Parcelas_Camp1.shp` y `Parcelas_5.shp`), exportando tablas estadísticas (`.csv`) y mapas temáticos en alta resolución (**300 DPI**).

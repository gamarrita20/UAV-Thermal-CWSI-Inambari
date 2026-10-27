# Análisis de Estrés Hídrico (CWSI) mediante Termografía UAV en Zonas Degradadas por Minería Aurífera (Inambari, Madre de Dios)

Este repositorio contiene el flujo de trabajo automatizado para el procesamiento radiométrico, reconstrucción fotogramétrica y modelamiento del **Índice de Estrés Hídrico de Cultivos/Vegetación (CWSI)** a partir de imágenes térmicas capturadas con vehículos aéreos no tripulados (UAV) en áreas en proceso de restauración ecológica en el corredor minero de Inambari, Madre de Dios, Perú.

## 📋 Flujo de Trabajo Metodológico

1. **Separación y Decodificación Radiométrica (`01_preprocesamiento_sdk`)**:
   - Separación automatizada de fotogramas R-JPEG térmicos (`640x512`) y RGB.
   - Extracción de la matriz de temperatura superficial en grados Celsius (`float32` de 1 banda) mediante **DJI Thermal SDK (`dji_irp`)**, parametrizando emisividad ($\varepsilon = 0.96$), humedad relativa y distancia nadir.
   - Transferencia e inyección de etiquetas geoespaciales (`EXIF/GPS` y orientación `XMP` del gimbal) desde los archivos R-JPEG originales hacia las matrices `.tif` mediante **ExifTool**.

2. **Generación de Ortomosaicos Térmicos (`02_fotogrametria_odm`)**:
   - Alineación y ortorrectificación de >1,800 fotogramas térmicos en **WebODM** bajo el sistema de coordenadas `WGS 1984 UTM Zona 19S (EPSG:32719)`, conservando la profundidad radiométrica en 32 bits sin compresión de color.

3. **Cálculo de CWSI y Estadísticas Zonales (`03_analisis_cwsi`)**:
   - Limpieza de bordes fotogramétricos (`NoData`) y filtrado de valores atípicos por reflexión especular (techos metálicos/agua).
   - Cálculo del índice empírico de estrés hídrico (CWSI):
     $$CWSI = \frac{T_{surf} - T_{wet}}{T_{dry} - T_{wet}}$$
     Donde $T_{surf}$ es la temperatura superficial del píxel, $T_{wet}$ el límite inferior de referencia (transpiración máxima / cuerpos de agua) y $T_{dry}$ el límite superior (suelo aluvial desnudo sin transpiración).
   - Extracción de estadísticas zonales (`mean`, `max`, `min`, `std`, `count`) por parcela de restauración (`Parcelas_Camp1` y `Parcelas_5`) y generación de cartografía temática a 300 DPI.

## 🛠️ Requisitos e Instalación

Clonar el repositorio e instalar las dependencias de Python:

```bash
git clone [https://github.com/tu-usuario/UAV-Thermal-CWSI-Inambari.git](https://github.com/tu-usuario/UAV-Thermal-CWSI-Inambari.git)
cd UAV-Thermal-CWSI-Inambari
pip install -r requirements.txt

import os
import sys
import shutil
import subprocess
import numpy as np
import tifffile
from PIL import Image

# --- 1. DETECCIÓN AUTOMÁTICA DE LA CARPETA DEL PROYECTO ---
# Obtiene la ruta exacta donde se encuentra este script .py
DIR_PROYECTO = os.path.dirname(os.path.abspath(__file__))

# Rutas de los ejecutables (DEBEN estar en esta misma carpeta)
RUTA_DJI_IRP = os.path.join(DIR_PROYECTO, "dji_irp.exe")
RUTA_EXIFTOOL = os.path.join(DIR_PROYECTO, "exiftool.exe")

# Carpetas de trabajo para las imágenes del DJI Mavic 2 Enterprise
DIR_ENTRADA = os.path.join(DIR_PROYECTO, "00_Imagenes_Brutas_Mavic2")
DIR_RGB = os.path.join(DIR_PROYECTO, "01_Imagenes_RGB")
DIR_TERMAL_JPG = os.path.join(DIR_PROYECTO, "02_Termal_RJPEG")
DIR_TERMAL_TIF = os.path.join(DIR_PROYECTO, "03_Termal_TIF_1Banda_FLIR")

# Parámetros ambientales de calibración radiométrica (Inambari, Madre de Dios)
EMISIVIDAD = 0.96      # Vegetación / suelo aluvial húmedo-seco
HUMEDAD = 75           # Humedad relativa promedio (%)
DISTANCIA = 25         # Distancia nadir / altura de vuelo (m) - Máx. 25 en SDK
TEMP_REFLEJADA = 28.0  # Temperatura aparente reflejada (°C)

# --- 2. VERIFICACIÓN DE ARCHIVOS EJECUTABLES ---
if not os.path.exists(RUTA_DJI_IRP):
    sys.exit(f"❌ ERROR: No se encontró 'dji_irp.exe' en {DIR_PROYECTO}.\n"
             "Copia dji_irp.exe y sus archivos .dll dentro de la carpeta del script.")

if not os.path.exists(RUTA_EXIFTOOL):
    sys.exit(f"❌ ERROR: No se encontró 'exiftool.exe' en {DIR_PROYECTO}.\n"
             "Descarga ExifTool, renombra 'exiftool(-k).exe' a 'exiftool.exe' y ponlo en esta carpeta.")

os.makedirs(DIR_ENTRADA, exist_ok=True)
os.makedirs(DIR_RGB, exist_ok=True)
os.makedirs(DIR_TERMAL_JPG, exist_ok=True)
os.makedirs(DIR_TERMAL_TIF, exist_ok=True)

# --- 3. SEPARACIÓN DE IMÁGENES (RGB vs. TÉRMICO MAVIC 2 ENTERPRISE) ---
print("1. Clasificando imágenes del DJI Mavic 2 Enterprise (RGB vs. R-JPEG Térmico)...")
archivos_brutos = [f for f in os.listdir(DIR_ENTRADA) if f.lower().endswith(".jpg")]

if not archivos_brutos:
    sys.exit(f"⚠️ Coloca las fotos originales del dron en la carpeta:\n{DIR_ENTRADA}")

for archivo in archivos_brutos:
    ruta_completa = os.path.join(DIR_ENTRADA, archivo)
    with Image.open(ruta_completa) as img:
        ancho, alto = img.size
        # El sensor térmico del Mavic 2 Enterprise captura a 640x512 píxeles
        if (ancho == 640 and alto == 512) or "T" in archivo.upper():
            shutil.copy2(ruta_completa, os.path.join(DIR_TERMAL_JPG, archivo))
        else:
            shutil.copy2(ruta_completa, os.path.join(DIR_RGB, archivo))

# --- 4. CONVERSIÓN SDK A BANDA TÉRMICA (32-BIT) Y RESTAURACIÓN EXIF ---
archivos_termales = [f for f in os.listdir(DIR_TERMAL_JPG) if f.lower().endswith(".jpg")]
print(f"2. Procesando {len(archivos_termales)} imágenes térmicas R-JPEG...")

for idx, jpg_name in enumerate(archivos_termales, 1):
    base_name = os.path.splitext(jpg_name)[0]
    ruta_jpg = os.path.join(DIR_TERMAL_JPG, jpg_name)
    ruta_raw = os.path.join(DIR_TERMAL_TIF, f"{base_name}.raw")
    ruta_tif = os.path.join(DIR_TERMAL_TIF, f"{base_name}.tif")

    # A. Extraer matriz de temperatura real (°C) con DJI Thermal SDK
    cmd_sdk = [
        RUTA_DJI_IRP,
        "-s", ruta_jpg,
        "-a", "measure",
        "-o", ruta_raw,
        "--measurefmt", "float32",
        "--emissivity", str(EMISIVIDAD),
        "--humidity", str(HUMEDAD),
        "--distance", str(DISTANCIA),
        "--reflection", str(TEMP_REFLEJADA)
    ]
    subprocess.run(cmd_sdk, cwd=DIR_PROYECTO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # B. Transformar binario .raw a TIFF de 1 sola banda (640x512, 32-bit float)
    if os.path.exists(ruta_raw):
        matriz_temp = np.fromfile(ruta_raw, dtype=np.float32).reshape((512, 640))
        tifffile.imwrite(ruta_tif, matriz_temp, dtype=np.float32)
        os.remove(ruta_raw)

        # C. Inyectar coordenadas GPS y metadatos de vuelo DJI desde el JPG original
        cmd_exif = [
            RUTA_EXIFTOOL,
            "-TagsFromFile", ruta_jpg,
            "-all:all",
            "-gps:all",
            "-xmp:all",
            "-overwrite_original",
            ruta_tif
        ]
        subprocess.run(cmd_exif, cwd=DIR_PROYECTO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if idx % 100 == 0 or idx == len(archivos_termales):
        print(f"   [{idx}/{len(archivos_termales)}] TIF radiométrico generado y georreferenciado.")

print(f"\n✅ PROCESO COMPLETADO. Imágenes de 1 banda listas en:\n{DIR_TERMAL_TIF}")

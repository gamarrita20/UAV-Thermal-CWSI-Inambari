import os
import shutil
import subprocess
import numpy as np
import tifffile
from PIL import Image

# --- CONFIGURACIÓN DE RUTAS Y PARÁMETROS ---
DIR_ENTRADA = r"C:\Vuelos_Inambari\Bruto"
DIR_RGB = r"C:\Vuelos_Inambari\01_RGB"
DIR_TERMAL_JPG = r"C:\Vuelos_Inambari\02_Termal_RJPEG"
DIR_TERMAL_TIF = r"C:\Vuelos_Inambari\03_Termal_TIF_Georref"

# Rutas de ejecutables externos
RUTA_DJI_IRP = r"C:\dji_thermal_sdk\utility\bin\windows\release_x64\dji_irp.exe"
RUTA_EXIFTOOL = r"C:\exiftool\exiftool.exe"

# Parámetros ambientales de campo (Inambari - Madre de Dios)
EMISIVIDAD = 0.96      # Vegetación / suelo aluvial
HUMEDAD = 75           # Humedad relativa (%)
DISTANCIA = 25         # Altura de vuelo / distancia al objetivo (m)
TEMP_REFLEJADA = 28.0  # Temperatura atmosférica aparente (°C)

os.makedirs(DIR_RGB, exist_ok=True)
os.makedirs(DIR_TERMAL_JPG, exist_ok=True)
os.makedirs(DIR_TERMAL_TIF, exist_ok=True)

# --- PASO 1: SEPARAR IMÁGENES TÉRMICAS DE RGB ---
print("1. Clasificando imágenes térmicas y RGB...")
for archivo in os.listdir(DIR_ENTRADA):
    if archivo.lower().endswith(".jpg"):
        ruta_completa = os.path.join(DIR_ENTRADA, archivo)
        with Image.open(ruta_completa) as img:
            ancho, alto = img.size
            # Las cámaras térmicas (640x512) se separan de las RGB de alta resolución
            if (ancho == 640 and alto == 512) or "_T" in archivo.upper():
                shutil.copy2(ruta_completa, os.path.join(DIR_TERMAL_JPG, archivo))
            else:
                shutil.copy2(ruta_completa, os.path.join(DIR_RGB, archivo))

# --- PASO 2 Y 3: PASAR POR EL SDK (OBTENER BANDA TÉRMICA) Y RESTAURAR EXIF/GPS ---
print("2. Extrayendo matriz térmica (°C) e inyectando coordenadas GPS...")
archivos_termales = [f for f in os.listdir(DIR_TERMAL_JPG) if f.lower().endswith(".jpg")]

for idx, jpg_name in enumerate(archivos_termales, 1):
    base_name = os.path.splitext(jpg_name)[0]
    ruta_jpg = os.path.join(DIR_TERMAL_JPG, jpg_name)
    ruta_raw = os.path.join(DIR_TERMAL_TIF, f"{base_name}.raw")
    ruta_tif = os.path.join(DIR_TERMAL_TIF, f"{base_name}.tif")

    # A. Ejecutar DJI Thermal SDK para extraer temperatura en 32-bit float
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
    subprocess.run(cmd_sdk, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # B. Convertir binario .raw a imagen .tif de 1 banda (640x512)
    if os.path.exists(ruta_raw):
        matriz_temp = np.fromfile(ruta_raw, dtype=np.float32).reshape((512, 640))
        tifffile.imwrite(ruta_tif, matriz_temp, dtype=np.float32)
        os.remove(ruta_raw) # Limpiar archivo temporal .raw

        # C. Copiar coordenadas GPS y metadatos XMP/EXIF del JPG original al nuevo TIF
        cmd_exif = [
            RUTA_EXIFTOOL,
            "-TagsFromFile", ruta_jpg,
            "-all:all",
            "-gps:all",
            "-xmp:all",
            "-overwrite_original",
            ruta_tif
        ]
        subprocess.run(cmd_exif, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if idx % 100 == 0 or idx == len(archivos_termales):
        print(f"   Procesadas {idx}/{len(archivos_termales)} imágenes...")

print("✅ Preprocesamiento finalizado. Imágenes listas para WebODM / Metashape.")

import os
import gc
import rasterio
from rasterio.mask import mask
from rasterio.plot import show
from rasterstats import zonal_stats
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# --- 1. CONFIGURACIÓN DE DIRECTORIOS ---
BASE_DIR = '/content/drive/MyDrive/Colab Notebooks/Análisis Termal'

DATOS_VUELOS = {
    "Dia1_Camp1": {
        "raster": f"{BASE_DIR}/Inambari-8-9-2026-orthophoto.tif",
        "shapefile": f"{BASE_DIR}/Parcelas_Camp1.shp",
        "t_wet": 24.0,
        "t_dry": 38.0
    },
    "Dia2_Parcelas5": {
        "raster": f"{BASE_DIR}/Inambari-9-9-2026-orthophoto.tif",
        "shapefile": f"{BASE_DIR}/Parcelas_5.shp",
        "t_wet": 25.0,
        "t_dry": 40.0
    }
}

# --- 2. FUNCIÓN DE DIAGNÓSTICO RADIOMÉTRICO ---
def diagnosticar_raster(ruta, nombre):
    if not os.path.exists(ruta):
        print(f"❌ Archivo no encontrado: {ruta}")
        return
    with rasterio.open(ruta) as src:
        data = src.read(1).astype('float32')
        validos = data[(data > 5.0) & (data < 150.0) & (~np.isnan(data))]
        print(f"=== Diagnóstico: {nombre} ===")
        print(f"  Bandas: {src.count} | CRS: {src.crs}")
        print(f"  Temp Mínima:   {np.min(validos):.2f} °C")
        print(f"  Temp Máxima:   {np.max(validos):.2f} °C")
        print(f"  Temp Promedio: {np.mean(validos):.2f} °C\n")

# --- 3. FUNCIÓN DE PROCESAMIENTO CWSI Y EXPORTACIÓN ---
def procesar_lote(nombre, cfg):
    ruta_raster = cfg["raster"]
    ruta_shp = cfg["shapefile"]
    t_wet, t_dry = cfg["t_wet"], cfg["t_dry"]

    if not os.path.exists(ruta_raster) or not os.path.exists(ruta_shp):
        return

    ruta_cwsi = f"{BASE_DIR}/CWSI_Final_{nombre}.tif"
    ruta_csv = f"{BASE_DIR}/Resultados_{nombre}.csv"

    # A. Cálculo de CWSI y filtrado de bordes (NoData)
    with rasterio.open(ruta_raster) as src:
        data = src.read(1).astype('float32')
        mask_val = (data > 5.0) & (data < 150.0) & (~np.isnan(data))
        
        cwsi = np.full(data.shape, np.nan, dtype='float32')
        cwsi[mask_val] = (data[mask_val] - t_wet) / (t_dry - t_wet)
        cwsi[mask_val] = np.clip(cwsi[mask_val], 0.0, 1.0)

        out_meta = src.profile.copy()
        out_meta.update({"dtype": 'float32', "nodata": np.nan, "count": 1})
        with rasterio.open(ruta_cwsi, 'w', **out_meta) as dest:
            dest.write(cwsi, 1)

    # B. Estadísticas Zonales por Parcela
    parcelas = gpd.read_file(ruta_shp)
    stats = zonal_stats(parcelas, ruta_cwsi, stats="mean max min std count", nodata=np.nan)
    
    parcelas['CWSI_Prom'] = [s['mean'] for s in stats]
    parcelas['CWSI_Max']  = [s['max'] for s in stats]
    parcelas['CWSI_Min']  = [s['min'] for s in stats]
    parcelas['CWSI_Std']  = [s['std'] for s in stats]
    parcelas['Pixeles']   = [s['count'] for s in stats]

    df_res = pd.DataFrame(parcelas.drop(columns='geometry'))
    df_res.to_csv(ruta_csv, index=False)

    # C. Exportación de Mapa Espacial (300 DPI)
    with rasterio.open(ruta_cwsi) as src_cwsi:
        if parcelas.crs != src_cwsi.crs:
            parcelas = parcelas.to_crs(src_cwsi.crs)
        out_img, out_trans = mask(src_cwsi, parcelas.geometry, crop=True, nodata=np.nan)

    fig_m, ax_m = plt.subplots(figsize=(10, 8))
    img_plot = show(out_img, transform=out_trans, ax=ax_m, cmap='RdYlBu_r', vmin=0, vmax=1)
    parcelas.boundary.plot(ax=ax_m, color='black', linewidth=1.2)
    
    cbar = plt.colorbar(img_plot.get_images()[0], ax=ax_m, shrink=0.7)
    cbar.set_label('Índice CWSI (0 = Húmedo | 1 = Estrés Severo)', size=11)
    ax_m.set(title=f'Distribución Espacial del CWSI - {nombre}', xlabel='Este (UTM)', ylabel='Norte (UTM)')
    plt.savefig(f"{BASE_DIR}/Mapa_{nombre}.jpg", dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig_m)

    # D. Exportación de Gráfico de Barras
    df_plot = df_res.sort_values(by='CWSI_Prom', ascending=False).dropna(subset=['CWSI_Prom']).head(15)
    fig_b, ax_b = plt.subplots(figsize=(12, 6))
    sns.barplot(x=df_plot.columns[0], y='CWSI_Prom', data=df_plot, palette='Reds_r', ax=ax_b)
    ax_b.axhline(y=0.6, color='red', linestyle='--', label='Umbral de Estrés Severo (0.6)')
    ax_b.set(ylim=(0, 1), title=f'Estrés Hídrico Promedio por Parcela - {nombre}', ylabel='CWSI Promedio')
    plt.xticks(rotation=45)
    ax_b.legend()
    plt.savefig(f"{BASE_DIR}/Grafico_{nombre}.jpg", dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig_b)

    del data, cwsi, out_img, parcelas
    gc.collect()
    print(f"✅ Procesamiento y gráficos completados para: {nombre}")

if __name__ == "__main__":
    for nombre_vuelo, config in DATOS_VUELOS.items():
        diagnosticar_raster(config["raster"], nombre_vuelo)
        procesar_lote(nombre_vuelo, config)

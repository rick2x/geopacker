# Run this script in the QGIS Python Console to set up a test project for Geopacker.
# Plugins -> Python Console -> Show Editor -> Open this file -> Run

import os
import tempfile
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer, QgsFeature, QgsGeometry,
    QgsPointXY, QgsField, QgsSingleSymbolRenderer, QgsMarkerSymbol
)
from qgis.PyQt.QtCore import QVariant

def setup_test_project():
    project = QgsProject.instance()
    project.clear()
    
    # 1. Valid Local Vector Layer (Memory Layer with features)
    vl_memory = QgsVectorLayer("Point?crs=epsg:4326", "1_Local_Valid_Points", "memory")
    pr = vl_memory.dataProvider()
    pr.addAttributes([QgsField("name", QVariant.String)])
    vl_memory.updateFields()
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(120, 15)))
    feat.setAttributes(["Test Point"])
    pr.addFeatures([feat])
    vl_memory.updateExtents()
    project.addMapLayer(vl_memory)
    
    # 2. Empty Temporary Layer
    vl_empty = QgsVectorLayer("Polygon?crs=epsg:4326", "2_Empty_Temp_Polygon", "memory")
    project.addMapLayer(vl_empty)
    
    # 3. Duplicate Layer (Same source as #1)
    vl_dup = QgsVectorLayer(vl_memory.source(), "3_Duplicate_Points", "memory")
    project.addMapLayer(vl_dup)
    
    # 4. Remote Vector Layer (Online GeoJSON)
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson"
    vl_remote = QgsVectorLayer(url, "4_Remote_Earthquakes", "ogr")
    project.addMapLayer(vl_remote)
    
    # 5. Local Raster Layer (Create a tiny 10x10 dummy raster)
    temp_dir = tempfile.gettempdir()
    raster_path = os.path.join(temp_dir, "dummy_raster.tif")
    
    try:
        from osgeo import gdal, osr
        driver = gdal.GetDriverByName('GTiff')
        ds = driver.Create(raster_path, 10, 10, 1, gdal.GDT_Byte)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        ds.SetProjection(srs.ExportToWkt())
        ds.SetGeoTransform([120, 1, 0, 15, 0, -1])
        # Write some data so it's not completely empty
        band = ds.GetRasterBand(1)
        import numpy as np
        band.WriteArray(np.full((10, 10), 128, dtype=np.uint8))
        ds.FlushCache()
        ds = None
        
        rl = QgsRasterLayer(raster_path, "5_Local_Raster")
        if rl.isValid():
            project.addMapLayer(rl)
    except Exception as e:
        print(f"Skipping dummy raster creation: {e}")
            
    # 6. Styled Vector Layer
    vl_styled = QgsVectorLayer("Point?crs=epsg:4326", "6_Styled_Points", "memory")
    pr_styled = vl_styled.dataProvider()
    pr_styled.addAttributes([QgsField("id", QVariant.Int)])
    vl_styled.updateFields()
    feat_styled = QgsFeature()
    feat_styled.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(121, 16)))
    feat_styled.setAttributes([1])
    pr_styled.addFeatures([feat_styled])
    vl_styled.updateExtents()
    
    # Add some custom styling
    symbol = QgsMarkerSymbol.createSimple({'name': 'star', 'color': '255,0,0', 'size': '5'})
    renderer = QgsSingleSymbolRenderer(symbol)
    vl_styled.setRenderer(renderer)
    
    project.addMapLayer(vl_styled)
    
    # Save project to a temp file so it has a known state
    project_path = os.path.join(temp_dir, "geopacker_test_project.qgz")
    project.write(project_path)
    
    print("--- Geopacker Test Project Setup Complete ---")
    print(f"Project saved to: {project_path}")
    print("Layers added:")
    print("  1. 1_Local_Valid_Points       -> Should be packaged to GPKG")
    print("  2. 2_Empty_Temp_Polygon       -> Should be skipped (if 'Strip Empty' is True)")
    print("  3. 3_Duplicate_Points         -> Should be skipped (if 'Strip Duplicates' is True)")
    print("  4. 4_Remote_Earthquakes       -> Should be skipped (if 'Skip Remote' is True) but stay linked")
    print("  5. 5_Local_Raster             -> Should be copied to rasters/ directory")
    print("  6. 6_Styled_Points            -> Should be packaged to GPKG with embedded style")
    print("\nYou can now open the Geopacker plugin, select an output zip location, and click Run!")


setup_test_project()

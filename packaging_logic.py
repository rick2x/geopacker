# -*- coding: utf-8 -*-
import os
import tempfile
import shutil
import zipfile
import datetime
import math
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsRasterLayer,
    QgsVectorFileWriter,
    QgsMessageLog,
    Qgis
)
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QTextDocument
from qgis.PyQt.QtPrintSupport import QPrinter

class GeopackerLogic:
    def __init__(self, output_file, strip_duplicates=True, strip_empty=True, skip_remote=True, only_selected=False, group_gpkgs=False, progress_bar=None, status_label=None, project=None, feedback=None):
        self.output_file = output_file
        self.strip_duplicates = strip_duplicates
        self.strip_empty = strip_empty
        self.skip_remote = skip_remote
        self.only_selected = only_selected
        self.group_gpkgs = group_gpkgs
        self.progress_bar = progress_bar
        self.status_label = status_label
        self.project = project if project is not None else QgsProject.instance()
        self.feedback = feedback

    def update_status(self, message, progress=None):
        if self.feedback:
            self.feedback.pushInfo(message)
            if progress is not None:
                self.feedback.setProgress(progress)
                
        if self.status_label:
            self.status_label.setText(message)
        if self.progress_bar and progress is not None:
            self.progress_bar.setValue(progress)
        QgsMessageLog.logMessage(message, "Geopacker", Qgis.Info)
        
        # Keep UI responsive during long operations
        app = QCoreApplication.instance()
        if app:
            app.processEvents()

    def is_layer_empty_temp(self, layer):
        if not layer.isValid():
            return True
        if layer.type() == QgsVectorLayer.VectorLayer:
            if layer.dataProvider().name() == 'memory':
                if layer.featureCount() <= 0:
                    return True
        return False

    def _get_layer_group_path(self, layer, separator="-"):
        group_path = ""
        node = self.project.layerTreeRoot().findLayer(layer.id())
        if node:
            parent = node.parent()
            groups = []
            while parent and parent != self.project.layerTreeRoot():
                gname = "".join([c if c.isalnum() or c in (' ', '-', '_') else "_" for c in parent.name()]).strip()
                if gname:
                    groups.insert(0, gname)
                parent = parent.parent()
            if groups:
                group_path = separator.join(groups)
        return group_path

    def run(self):
        self.update_status("Starting packaging...", 0)
        
        output_dir = os.path.dirname(os.path.abspath(self.output_file)) if self.output_file else None
        try:
            temp_dir_ctx = tempfile.TemporaryDirectory(prefix="geopacker_", dir=output_dir if (output_dir and os.path.exists(output_dir)) else None)
        except OSError:
            temp_dir_ctx = tempfile.TemporaryDirectory(prefix="geopacker_")
        
        with temp_dir_ctx as temp_dir:
            
            rasters_dir = os.path.join(temp_dir, "rasters")
            os.makedirs(rasters_dir, exist_ok=True)
            media_dir = os.path.join(temp_dir, "media")
            os.makedirs(media_dir, exist_ok=True)
            styles_dir = os.path.join(temp_dir, "styles")
            os.makedirs(styles_dir, exist_ok=True)
            gpkg_path = os.path.join(temp_dir, "packaged_data.gpkg")
            
            layers = self.project.mapLayers().values()
            total_layers = len(layers)
            if total_layers == 0:
                self.update_status("No layers in project to package.", 100)
                return

            seen_sources = set()
            layers_to_package = []
            layers_to_remove = []
            
            skipped_layers_data = []
            success_layers_data = []
            failed_ops_data = []

            self.update_status("Filtering layers...", 5)
            for layer in layers:
                if self.strip_empty and self.is_layer_empty_temp(layer):
                    self.update_status(f"Skipping empty temporary layer: {layer.name()}")
                    layers_to_remove.append(layer.id())
                    skipped_layers_data.append({'name': layer.name(), 'reason': 'Empty temporary layer'})
                    continue

                source = layer.publicSource()
                if self.strip_duplicates:
                    if source in seen_sources:
                        self.update_status(f"Skipping duplicate layer: {layer.name()}")
                        layers_to_remove.append(layer.id())
                        skipped_layers_data.append({'name': layer.name(), 'reason': 'Duplicate source'})
                        continue
                    seen_sources.add(source)

                layers_to_package.append(layer)

            layer_mapping = {}
            used_layer_names = set()
            failed_layers = []

            for i, layer in enumerate(layers_to_package):
                progress = 5 + int(60 * (i / len(layers_to_package)))
                self.update_status(f"Processing layer: {layer.name()}", progress)
                
                if layer.type() == QgsVectorLayer.VectorLayer:
                    provider_name = layer.dataProvider().name() if layer.dataProvider() else ""
                    if self.skip_remote and provider_name not in ('ogr', 'memory', 'delimitedtext', 'gpx', 'spatialite'):
                        self.update_status(f"Skipping remote vector layer: {layer.name()} ({provider_name})")
                        failed_layers.append(f"• {layer.name()} (Skipped: remote/online provider '{provider_name}')")
                        skipped_layers_data.append({'name': layer.name(), 'reason': f"Remote vector ({provider_name})"})
                        continue

                    options = QgsVectorFileWriter.SaveVectorOptions()
                    options.driverName = "GPKG"
                    
                    if self.only_selected and layer.selectedFeatureCount() > 0:
                        options.onlySelectedFeatures = True
                    
                    base_safe_name = "".join([c if c.isalnum() else "_" for c in layer.name()])
                    if not base_safe_name:
                        base_safe_name = "layer"
                    if base_safe_name[0].isdigit():
                        base_safe_name = "layer_" + base_safe_name
                        
                    safe_name = base_safe_name
                    suffix = 1
                    while safe_name in used_layer_names:
                        safe_name = f"{base_safe_name}_{suffix}"
                        suffix += 1
                    
                    used_layer_names.add(safe_name)
                    options.layerName = safe_name
                    
                    target_gpkg = gpkg_path
                    gpkg_filename = "packaged_data.gpkg"
                    if self.group_gpkgs:
                        group_path = self._get_layer_group_path(layer, separator="-")
                        
                        if group_path:
                            gpkg_filename = f"{group_path}.gpkg"
                            target_gpkg = os.path.join(temp_dir, gpkg_filename)
                    
                    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
                    
                    if os.path.exists(target_gpkg):
                        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
                    
                    write_result = QgsVectorFileWriter.writeAsVectorFormatV3(
                        layer, target_gpkg, self.project.transformContext(), options)
                        
                    writer_err = write_result[0]
                    error_msg = write_result[1] if len(write_result) > 1 else str(writer_err)
                        
                    if writer_err == QgsVectorFileWriter.NoError:
                        new_source = f"./{gpkg_filename}|layername={options.layerName}"
                        layer_mapping[layer.id()] = {
                            'type': 'vector',
                            'source': new_source,
                            'provider': 'ogr'
                        }
                        success_layers_data.append({'name': layer.name(), 'type': 'Vector', 'dest': f"{gpkg_filename} ({options.layerName})"})
                        
                        # --- Embed Style to GeoPackage ---
                        try:
                            temp_style_file = os.path.join(temp_dir, f"temp_{options.layerName}.qml")
                            # Save style to temp file
                            layer.saveNamedStyle(temp_style_file)
                            
                            # Open Geopackage layer to save style internally
                            gpkg_layer_uri = f"{target_gpkg}|layername={options.layerName}"
                            gpkg_layer = QgsVectorLayer(gpkg_layer_uri, options.layerName, "ogr")
                            
                            if gpkg_layer.isValid():
                                gpkg_layer.loadNamedStyle(temp_style_file)
                                gpkg_layer.saveStyleToDatabase(options.layerName, "", True, "")
                                
                            del gpkg_layer
                            if os.path.exists(temp_style_file):
                                os.remove(temp_style_file)
                        except Exception as e:
                            QgsMessageLog.logMessage(f"Failed to save style to GeoPackage for {layer.name()}: {str(e)}", "Geopacker", Qgis.Warning)
                        # ---------------------------------
                        
                        # Pack loose .qml style files for vectors
                        source_path = layer.dataProvider().dataSourceUri()
                        if source_path and '|' in source_path:
                            source_path = source_path.split('|')[0]
                        if source_path and os.path.isfile(source_path):
                            filename = os.path.basename(source_path)
                            source_dir = os.path.dirname(source_path)
                            base_name, _ = os.path.splitext(filename)
                            qml_path = os.path.join(source_dir, f"{base_name}.qml")
                            
                            if os.path.isfile(qml_path):
                                dst_qml = os.path.join(styles_dir, f"{options.layerName}.qml")
                                try:
                                    shutil.copy2(qml_path, dst_qml)
                                except OSError as e:
                                    failed_ops_data.append({'name': f"{layer.name()} (.qml)", 'reason': str(e)})
                    else:
                        QgsMessageLog.logMessage(f"Failed to export {layer.name()}: {error_msg}", "Geopacker", Qgis.Warning)
                        failed_layers.append(f"• {layer.name()} (Failed export: {error_msg})")
                        failed_ops_data.append({'name': layer.name(), 'reason': f"Export failed: {error_msg}"})
                
                elif layer.type() == QgsRasterLayer.RasterLayer:
                    source_path = layer.dataProvider().dataSourceUri()
                    if os.path.isfile(source_path):
                        filename = os.path.basename(source_path)
                        source_dir = os.path.dirname(source_path)
                        base_name, _ = os.path.splitext(filename)
                        
                        group_path = self._get_layer_group_path(layer, separator="/")

                        raster_dest_dir = os.path.join(rasters_dir, os.path.normpath(group_path)) if group_path else rasters_dir
                        os.makedirs(raster_dest_dir, exist_ok=True)
                        
                        if os.path.isdir(source_dir):
                            try:
                                from osgeo import gdal
                                ds = gdal.Open(source_path)
                                if ds:
                                    file_list = ds.GetFileList()
                                    ds = None
                                    if file_list:
                                        for src_f in file_list:
                                            if os.path.isfile(src_f):
                                                dst_f = os.path.join(raster_dest_dir, os.path.basename(src_f))
                                                try:
                                                    shutil.copy2(src_f, dst_f)
                                                except shutil.SameFileError:
                                                    pass
                                                except OSError as e:
                                                    QgsMessageLog.logMessage(f"Failed to copy raster file {src_f}: {str(e)}", "Geopacker", Qgis.Warning)
                                else:
                                    raise Exception("gdal.Open failed")
                            except (ImportError, OSError, RuntimeError):
                                # Fallback to existing logic if GDAL unavailable or fails
                                for f in os.listdir(source_dir):
                                    if ".qgis_time_machine" in f or ".qgis_time_machine" in source_dir:
                                        continue
                                    if f == filename or f.startswith(base_name + '.') or f.startswith(filename + '.'):
                                        src_f = os.path.join(source_dir, f)
                                        if os.path.isfile(src_f):
                                            dst_f = os.path.join(raster_dest_dir, f)
                                            try:
                                                shutil.copy2(src_f, dst_f)
                                            except shutil.SameFileError:
                                                pass
                                            except OSError as e:
                                                QgsMessageLog.logMessage(f"Failed to copy raster file {src_f}: {str(e)}", "Geopacker", Qgis.Warning)
                                        
                        new_source = f"./rasters/{group_path}/{filename}" if group_path else f"./rasters/{filename}"
                        layer_mapping[layer.id()] = {
                            'type': 'raster',
                            'source': new_source,
                            'provider': 'gdal'
                        }
                        success_layers_data.append({'name': layer.name(), 'type': 'Raster', 'dest': 'Copied Local Raster'})
                    else:
                        QgsMessageLog.logMessage(f"Skipping raster copy for {layer.name()} (not a local file)", "Geopacker", Qgis.Info)
                        skipped_layers_data.append({'name': layer.name(), 'reason': 'Remote/Non-local Raster'})

            self.update_status("Saving project copy...", 70)
            
            # Cache original project state to avoid changing the active project's path
            original_file_name = self.project.fileName()
            original_is_dirty = self.project.isDirty()
            
            temp_qgz_path = os.path.join(temp_dir, "project.qgz")
            self.project.write(temp_qgz_path)
            
            # Restore original project state
            self.project.setFileName(original_file_name)
            if original_is_dirty:
                self.project.setDirty(True)
            
            self.update_status("Remapping project paths...", 75)
            
            qgz_extract_dir = os.path.join(temp_dir, "qgz_unpacked")
            os.makedirs(qgz_extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(temp_qgz_path, 'r') as zf:
                for member in zf.namelist():
                    member_path = os.path.normpath(os.path.join(qgz_extract_dir, member))
                    if not member_path.startswith(os.path.normpath(qgz_extract_dir) + os.sep) and member_path != os.path.normpath(qgz_extract_dir):
                        raise ValueError(f"Unsafe path in archive: {member}")
                    zf.extract(member, qgz_extract_dir)
                
            qgs_file = None
            for file in os.listdir(qgz_extract_dir):
                if file.endswith('.qgs'):
                    qgs_file = os.path.join(qgz_extract_dir, file)
                    break
                    
            if qgs_file:
                try:
                    import defusedxml.ElementTree as ET
                    import defusedxml
                    defusedxml.defuse_stdlib()
                    tree = ET.parse(qgs_file)
                except ImportError:
                    QgsMessageLog.logMessage(
                        "defusedxml not found — falling back to standard XML parser. "
                        "Install defusedxml for safer XML handling.",
                        "Geopacker", Qgis.Warning
                    )
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(qgs_file)
                
                root = tree.getroot()
                
                # --- Media Packaging Logic ---
                media_mapping = {}
                def process_media_path(path_str):
                    if not path_str or not isinstance(path_str, str):
                        return path_str
                        
                    # Prevent vector files from being accidentally swept up as media through generic 'source' tags
                    lower_path = path_str.lower()
                    if lower_path.endswith('.shp') or lower_path.endswith('.shx') or lower_path.endswith('.dbf') or lower_path.endswith('.geojson'):
                        return path_str
                        
                    if os.path.isabs(path_str) and os.path.isfile(path_str):
                        if path_str not in media_mapping:
                            filename = os.path.basename(path_str)
                            safe_name = filename
                            suffix = 1
                            dest_path = os.path.join(media_dir, safe_name)
                            while os.path.exists(dest_path):
                                base, ext = os.path.splitext(filename)
                                safe_name = f"{base}_{suffix}{ext}"
                                dest_path = os.path.join(media_dir, safe_name)
                                suffix += 1
                            try:
                                shutil.copy2(path_str, dest_path)
                                media_mapping[path_str] = f"./media/{safe_name}"
                            except Exception as e:
                                QgsMessageLog.logMessage(f"Failed to copy media {path_str}: {str(e)}", "Geopacker", Qgis.Warning)
                                return path_str
                        return media_mapping[path_str]
                    return path_str

                def process_style_path(path_str):
                    if not path_str or not isinstance(path_str, str):
                        return path_str
                    if os.path.isabs(path_str) and os.path.isfile(path_str) and path_str.endswith('.qml'):
                        filename = os.path.basename(path_str)
                        safe_name = filename
                        suffix = 1
                        dest_path = os.path.join(styles_dir, safe_name)
                        while os.path.exists(dest_path):
                            base, ext = os.path.splitext(filename)
                            safe_name = f"{base}_{suffix}{ext}"
                            dest_path = os.path.join(styles_dir, safe_name)
                            suffix += 1
                        try:
                            shutil.copy2(path_str, dest_path)
                            return f"./styles/{safe_name}"
                        except OSError as e:
                            QgsMessageLog.logMessage(f"Failed to copy style file {path_str}: {str(e)}", "Geopacker", Qgis.Warning)
                            return path_str
                    return path_str

                def remap_assets_in_element(element):
                    changed = False
                    
                    # 1. Direct Attribute Checks (Common in QGIS 3 Print Layouts and image fills)
                    for attr_name in ('picturePath', 'file', 'svgFile', 'source', 'pictureUrl', 'path', 'image_path'):
                        v = element.get(attr_name)
                        if v:
                            new_path = process_media_path(v)
                            if new_path != v:
                                element.set(attr_name, new_path)
                                changed = True
                                
                    # 2. Key-Value Tag Checks (Common in symbology)
                    if element.tag == 'prop' and element.get('k') in ('name', 'svgFile', 'file', 'styleUrl'):
                        v = element.get('v')
                        if v:
                            if element.get('k') == 'styleUrl':
                                new_path = process_style_path(v)
                            else:
                                new_path = process_media_path(v)
                            if new_path != v:
                                element.set('v', new_path)
                                changed = True
                    if element.tag == 'Option' and element.get('type') == 'QString':
                        name = element.get('name')
                        if name in ('pictureUrl', 'file', 'svgFile', 'path', 'sourceFile', 'styleUrl'):
                            v = element.get('value')
                            if v:
                                if name == 'styleUrl':
                                    new_path = process_style_path(v)
                                else:
                                    new_path = process_media_path(v)
                                if new_path != v:
                                    element.set('value', new_path)
                                    changed = True
                                    
                    # 3. Recursion
                    for child in list(element):
                        if remap_assets_in_element(child):
                            changed = True
                    return changed
                
                remap_assets_in_element(root)
                # -----------------------------
                
                project_layers = root.find('projectlayers')
                layer_tree = root.find('layer-tree-group')
                
                if project_layers is not None:
                    for maplayer in list(project_layers):
                        layer_id_elem = maplayer.find('id')
                        if layer_id_elem is not None:
                            lid = layer_id_elem.text
                            if lid in layers_to_remove:
                                project_layers.remove(maplayer)
                                continue
                                
                            if lid in layer_mapping:
                                ds_elem = maplayer.find('datasource')
                                if ds_elem is not None:
                                    ds_elem.text = layer_mapping[lid]['source']
                                
                                provider_elem = maplayer.find('provider')
                                if provider_elem is not None:
                                    provider_elem.text = layer_mapping[lid]['provider']
                
                def remove_from_layer_tree(group):
                    for child in list(group):
                        if child.tag == 'layer-tree-layer':
                            lid = child.get('id')
                            if lid in layers_to_remove:
                                group.remove(child)
                        elif child.tag == 'layer-tree-group':
                            remove_from_layer_tree(child)
                
                if layer_tree is not None:
                    remove_from_layer_tree(layer_tree)
                    
                    # Direct style-url check for tree layers
                    for child in layer_tree.iter('layer-tree-layer'):
                        style_url = child.get('style-url')
                        if style_url:
                            new_style = process_style_path(style_url)
                            if new_style != style_url:
                                child.set('style-url', new_style)
                    
                properties_elem = root.find('properties')
                if properties_elem is None:
                    properties_elem = ET.SubElement(root, 'properties')
                
                paths_elem = properties_elem.find('Paths')
                if paths_elem is None:
                    paths_elem = ET.SubElement(properties_elem, 'Paths')
                
                absolute_elem = paths_elem.find('Absolute')
                if absolute_elem is None:
                    absolute_elem = ET.SubElement(paths_elem, 'Absolute', type="bool")
                
                absolute_elem.text = 'false'
                
                tree.write(qgs_file, encoding='utf-8', xml_declaration=True)
                
                new_qgz_path = os.path.join(temp_dir, "project_remapped.qgz")
                with zipfile.ZipFile(new_qgz_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for root_dir, dirs, files in os.walk(qgz_extract_dir):
                        for file in files:
                            file_path = os.path.join(root_dir, file)
                            arcname = os.path.relpath(file_path, qgz_extract_dir)
                            zf.write(file_path, arcname)
                
                shutil.move(new_qgz_path, temp_qgz_path)
                shutil.rmtree(qgz_extract_dir, ignore_errors=True)

            self.update_status("Generating PDF Audit Report...", 82)
            
            # --- Gather PDF Report Data ---
            def get_dir_size(path):
                total = 0
                if os.path.exists(path):
                    if os.path.isfile(path):
                        return os.path.getsize(path)
                    for dirpath, _, filenames in os.walk(path):
                        for f in filenames:
                            fp = os.path.join(dirpath, f)
                            if not os.path.islink(fp):
                                total += os.path.getsize(fp)
                return total

            def format_sz(size_bytes):
                if size_bytes == 0:
                    return "0 B"
                size_name = ("B", "KB", "MB", "GB", "TB")
                i = int(math.floor(math.log(size_bytes, 1024)))
                p = math.pow(1024, i)
                s = round(size_bytes / p, 2)
                return f"{s} {size_name[i]}"

            proj_title = self.project.metadata().title() or "Untitled Project"
            proj_author = self.project.metadata().author() or "N/A"
            proj_crs = self.project.crs().authid()
            proj_crs_desc = self.project.crs().description()
            
            gpkg_total_size = 0
            for file in os.listdir(temp_dir):
                if file.endswith('.gpkg'):
                    gpkg_total_size += os.path.getsize(os.path.join(temp_dir, file))
            
            sizes = {
                'GeoPackage(s) (Vectors)': gpkg_total_size,
                'Rasters': get_dir_size(rasters_dir),
                'Media Assets': get_dir_size(media_dir),
                'Styles': get_dir_size(styles_dir),
                'Project File (.qgz)': get_dir_size(temp_qgz_path)
            }
            total_sz = sum(sizes.values())
            
            # Build HTML
            html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; color: #333; line-height: 1.4; }}
                    h1 {{ color: #2C3E50; font-size: 16pt; border-bottom: 1pt solid #3498DB; padding-bottom: 6pt; margin-bottom: 15pt; }}
                    h2 {{ color: #2980B9; font-size: 13pt; margin-top: 25pt; border-bottom: 1pt solid #ddd; padding-bottom: 4pt; margin-bottom: 10pt; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 15pt; font-size: 10pt; }}
                    th, td {{ padding: 12pt; text-align: left; border: 1pt solid #e0e0e0; }}
                    th {{ background-color: #F8FAFC; color: #2C3E50; font-weight: bold; padding-top: 14pt; padding-bottom: 14pt; }}
                    td {{ padding-top: 10pt; padding-bottom: 10pt; }}
                    .success {{ color: #27AE60; font-weight: bold; }}
                    .skipped {{ color: #F39C12; font-weight: bold; }}
                    .failed {{ color: #C0392B; font-weight: bold; }}
                    .right {{ text-align: right; }}
                </style>
            </head>
            <body>
                <h1>Geopacker Enterprise Audit Report</h1>
                
                <h2>Project Summary</h2>
                <table>
                    <tr><th>Project File</th><td>{os.path.basename(self.project.fileName())}</td></tr>
                    <tr><th>Project Title</th><td>{proj_title}</td></tr>
                    <tr><th>Author</th><td>{proj_author}</td></tr>
                    <tr><th>Timestamp</th><td>{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
                </table>
                
                <h2>CRS Details</h2>
                <table>
                    <tr><th>Authority ID</th><td>{proj_crs}</td></tr>
                    <tr><th>Description</th><td>{proj_crs_desc}</td></tr>
                </table>
                
                <h2>Data Size Breakdown</h2>
                <table>
                    <tr><th>Component</th><th class="right">Size</th></tr>
            """
            for comp, sz in sizes.items():
                if sz > 0:
                    html += f"<tr><td>{comp}</td><td class='right'>{format_sz(sz)}</td></tr>"
            html += f"<tr><th>Total Packaged Size</th><th class='right'>{format_sz(total_sz)}</th></tr>"
            html += "</table>"

            html += "<h2>Layer Inventory</h2>"
            if success_layers_data:
                html += """<table>
                    <tr><th>Layer Name</th><th>Type</th><th>Destination</th></tr>"""
                for lyr in success_layers_data:
                    html += f"<tr><td>{lyr['name']}</td><td>{lyr['type']}</td><td><span class='success'>✓ {lyr['dest']}</span></td></tr>"
                html += "</table>"
            else:
                html += "<p>No layers packaged.</p>"

            if skipped_layers_data:
                html += "<h2>Skipped Items</h2>"
                html += """<table>
                    <tr><th>Layer Name</th><th>Reason for Skipping</th></tr>"""
                for lyr in skipped_layers_data:
                    html += f"<tr><td>{lyr['name']}</td><td><span class='skipped'>{lyr['reason']}</span></td></tr>"
                html += "</table>"

            if failed_ops_data:
                html += "<h2>Failed Operations</h2>"
                html += """<table>
                    <tr><th>Item Name</th><th>Reason for Failure</th></tr>"""
                for r in failed_ops_data:
                    html += f"<tr><td>{r['name']}</td><td><span class='failed'>{r['reason']}</span></td></tr>"
                html += "</table>"
            
            html += "</body></html>"
            
            report_path = os.path.join(temp_dir, "packaging_report.pdf")
            try:
                doc = QTextDocument()
                doc.setHtml(html)
                printer = QPrinter(QPrinter.HighResolution)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setOutputFileName(report_path)
                doc.print_(printer)
            except Exception as e:
                QgsMessageLog.logMessage(f"Failed to generate PDF report: {e}", "Geopacker", Qgis.Warning)
                # Fallback to HTML if PDF generation fails
                report_path = os.path.join(temp_dir, "packaging_report.html")
                with open(report_path, "w", encoding="utf-8") as rf:
                    rf.write(html)

            self.update_status("Zipping final package...", 85)
            
            output_basename = os.path.basename(self.output_file)
            project_name, _ = os.path.splitext(output_basename)
            qgz_name_in_zip = f"{project_name}.qgz"
            
            with zipfile.ZipFile(self.output_file, 'w', zipfile.ZIP_DEFLATED) as final_zip:
                final_zip.write(temp_qgz_path, qgz_name_in_zip)
                
                for file in os.listdir(temp_dir):
                    if file.endswith('.gpkg'):
                        final_zip.write(os.path.join(temp_dir, file), file)
                
                if os.path.exists(os.path.join(temp_dir, "packaging_report.pdf")):
                    final_zip.write(os.path.join(temp_dir, "packaging_report.pdf"), "packaging_report.pdf")
                elif os.path.exists(os.path.join(temp_dir, "packaging_report.html")):
                    final_zip.write(os.path.join(temp_dir, "packaging_report.html"), "packaging_report.html")
                
                for root_dir, dirs, files in os.walk(rasters_dir):
                    for file in files:
                        file_path = os.path.join(root_dir, file)
                        rel_path = os.path.relpath(file_path, temp_dir)
                        final_zip.write(file_path, rel_path)

                if os.path.exists(media_dir):
                    for root_dir, dirs, files in os.walk(media_dir):
                        for file in files:
                            file_path = os.path.join(root_dir, file)
                            rel_path = os.path.relpath(file_path, temp_dir)
                            final_zip.write(file_path, rel_path)
                
                if os.path.exists(styles_dir):
                    for root_dir, dirs, files in os.walk(styles_dir):
                        for file in files:
                            file_path = os.path.join(root_dir, file)
                            rel_path = os.path.relpath(file_path, temp_dir)
                            final_zip.write(file_path, rel_path)

            self.update_status("Packaging complete!", 100)
            return failed_layers
            


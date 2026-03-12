<p align="center">
  <img src="icon.png" width="128" height="128" alt="Geopacker Logo">
</p>

# Geopacker QGIS Plugin

![Version](https://img.shields.io/badge/version-1.2.2-blue)

**Geopacker** is a QGIS plugin designed to solve the headache of broken paths when sharing QGIS projects. It bundles your entire current project (`.qgz`), vector layers, and raster layers into a single, clean `.zip` file ready to be shared. 

Unlike the native "Package Layers" tool, Geopacker actually modifies the bundled `.qgz` project to use relative paths, ensuring that whoever opens your packaged zip file will see exactly what you see, without a single broken link warning.

## Why Geopacker? (The Problem Solved)

Sharing QGIS projects often results in broken file paths because standard tools simply export data without updating the project file's references. Geopacker bridges this gap.

| Feature | QGIS "Package Layers" | Geopacker |
| --- | --- | --- |
| **Project Path Linking** | ❌ Leaves `.qgz` untouched (links break upon sharing). | ✅ Safely rewrites `.qgz` XML to use perfect **relative paths**. |
| **Raster Data Support** | ❌ Ignores raster files entirely. | ✅ Automatically copies and links local **rasters** safely. |
| **Raster Sidecar Files** | ❌ N/A. | ✅ Smartly packages `.tfw`, `.prj`, `.aux.xml` with rasters using verified GDAL associations so georeferencing isn't lost. |
| **Media Assets (SVGs, Logos, Backgrounds)** | ❌ Leaves absolute local paths that break print layouts. | ✅ Detects local Print Layout images, backgrounds, and SVG markers, packing them into a relative `media/` folder. |
| **Layer Styling (Colors/Categories)** | ❌ External `.qml` styles are left behind. | ✅ Automatically detects and packages associated `.qml` files so map layouts look identical. |
| **Duplicate Checking** | ❌ Blindly processes duplicates, inflating file size. | ✅ Actively detects and **strips duplicate** layer sources. |
| **Empty Layers** | ❌ Packages empty workspace/scratch layers. | ✅ Automatically **trims out empty** memory layers. |
| **Remote Layers** | ❌ Attempts to download massive WFS datasets. | ✅ Safely **skips remote vectors**, keeping them linked online. |
| **Final Output** | ❌ Yields a loose, unmanaged GeoPackage file. | ✅ Generates a **single, safe, email-ready `.zip`** archive containing a detailed Enterprise-Grade Audit Report (`packaging_report.pdf`). |

## Features
- **Headless & CLI Support**: Run Geopacker natively from the terminal (`qgis_process`) or stitch it into your QGIS Graphical Models via the standard QGIS Processing Toolbox.
- **Consolidates Vectors**: Exports all valid shapefiles, GeoJSONs, etc. into a single `packaged_data.gpkg`.
- **Grouped GeoPackages**: Optionally splits vector layers into multiple distinct `.gpkg` databases based on their QGIS Layer Tree Group mapping (e.g. `Water-System.gpkg`).
- **Collects Rasters & Sidecars**: Automatically bundles local rasters alongside any matching sidecar files (like `.tfw` or `.prj`) into a unified `rasters/` directory using GDAL associations.
- **Packages Layouts & SVGs**: Scans QGIS Projects for local custom SVGs, Print Layout images, and layout backgrounds, copying them to a `media/` folder and rewriting their paths to be relative.
- **Embedded Vector Styles**: Automatically detects and directly embeds vector layer styles (`.qml`) into the generated GeoPackage SQLite database, ensuring symbology immediately persists when users load the gpkg into a brand new QGIS project.
- **Preserves Layer Styles**: Detects and bundles loose `.qml` style files alongside vector datasets so your map categorization and layout colors never break.
- **Smart Path Remapping**: Behind the scenes, the plugin unzips a copy of your `.qgz` project, parses the underlying XML, and updates all layer and media data sources to point to the new relatively-pathed items.
- **Dynamic ZIP Naming**: The QGIS project file securely nested inside the ZIP archive takes on the same matching name as your exported zip file (e.g., `MyProject.zip` will contain `MyProject.qgz`).
- **Smart Trimming**: Optional checkboxes to strip out empty memory layers and duplicate layer sources to keep your packaged file size down.
- **Selected Features Only**: New granular control allows you to export *only* the specific highlighted/selected features of your vector layers, while still correctly exporting all other layers in full.
- **Remote Layer Protection**: Automatically detects remote vectors (e.g. WFS/Online) and securely skips downloading them while retaining their dynamic online links in the final project.
- **Graceful Error Handling**: Actively protects you by deleting partial ZIP exports if an unrecoverable system error occurs mid-process, ensuring no corrupt maps are sent.
- **Error Reporting**: Informs you of exactly which layers were skipped or failed to export.

## Installation
1. Download a Geopacker ZIP release from this repository.
2. In QGIS, navigate to **Plugins** > **Manage and Install Plugins...**
3. Select **Install from ZIP**, choose the downloaded file, and click Install.
4. The Geopacker icon will appear in your Plugins toolbar.

## Usage

### 1. Via the Legacy Plugin Dialog
1. Open your target mapping project in QGIS.
2. Click the Geopacker icon or find it under the **Plugins** > **Geopacker** menu.
3. Choose the destination path for your packaged `.zip` file.
4. Check the options to remove duplicates, empty temporary layers, or skip remote vectors if desired.
5. Click **Run**.
6. Wait for the success dialog (which will also list any skipped or failed layers).

### 2. Via the QGIS Processing Toolbox
1. In QGIS, open the **Processing Toolbox** panel (`Ctrl+Alt+T`).
2. Search for **Geopacker** -> **Package Project**.
3. Double click to run it. If you leave the `Input` project field empty, it will automatically package your currently active project canvas!
4. **Graphical Modeler**: Because it is a native algorithm, you can now drag-and-drop Geopacker to run at the absolute end of your custom graphical models.

### 3. Via the Command Line (Headless)
Geopacker can be automated without ever launching the QGIS GUI using the bundled `qgis_process` executable. This is perfect for nightly cron jobs or batch scripts.

Open your OSGeo4W Shell (or terminal with QGIS mapped to PATH) and run:
```bash
qgis_process run geopacker:package_project --INPUT="C:/maps/my_map.qgz" --OUTPUT="C:/temp/qwe.zip"
```
*(You can run `qgis_process help geopacker:package_project` to see all available CLI flags).*
7. Share the resulting `.zip` file with your colleagues or clients!

## Requirements
- QGIS 3.0 or higher.
- Python 3 environment (native to QGIS installations).
- **Recommended:** [`defusedxml`](https://pypi.org/project/defusedxml/) for hardened XML parsing. Install via `pip install defusedxml` in the QGIS Python console.

## Changelog

### 1.2.2
- **Bug Fix**: Fixed an issue where the active QGIS project's file path would be temporarily changed to the internal packaging directory, causing subsequent saves to fail or target a deleted folder.

### 1.2.1
- **Export Selected Features**: Added a new checkbox option (`Only export selected features if any are selected`). When extracting vector layers, Geopacker will now smartly check if the layer has an active selection and selectively export only those geometries, leaving unselected layers to export their full datasets normally.

### 1.2.0
- **Headless QGIS Execution & Processing Toolbox Integration**: Completely decoupled packaging logic from the Qt GUI, registering Geopacker as a native QGIS Processing Provider. It can now be chained in the Graphical Modeler or run headless via the `qgis_process` CLI.

### 1.1.4
- Embedded Vector Styles: Automatically saves and embeds vector layer styles directly into the output GeoPackage database so symbology persists when loaded into new projects.

### 1.1.3
- Added structured Enterprise-Grade Audit Report (PDF Output) replacing old text logs
- Added option to separate vector layers into multiple distinct GeoPackages based on QGIS Layer tree groups

### 1.1.2
- Added ZIP Slip (path traversal) protection during archive extraction
- Hardened XML parsing with `defusedxml` warning fallback
- Narrowed broad exception handlers to specific types (`OSError`, `SameFileError`, etc.)
- Logged previously silenced cleanup errors
- Replaced manual temp directory handling with `TemporaryDirectory` context manager
- Removed unused imports

### 1.1.1
- Added `.qml` style file packaging
- Fixed map layout background/image path mapping
- Robust destination drive temp staging
- Added dynamic ZIP packaging reports

### 1.1.0
- Experimental release

### 1.0.2
- Support for raster sidecar files
- Localized SVG/Print Layout media packaging
- Inner QGZ matched naming
- Graceful error handling

### 1.0.1
- Fix and remove `.qrc`

### 1.0.0
- Initial release of Geopacker

## Contributing and Bug Reports
Please report any bugs or feature requests on the [GitHub Issues tracker](https://github.com/rick2x/geopacker/issues).

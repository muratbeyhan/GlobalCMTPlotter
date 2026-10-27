## Global CMT Beachball Plotter (QGIS Plugin)

This QGIS plugin automates the process of importing and visualizing 
earthquake focal mechanism from Global CMT and AFAD (Türkiye) catalog files. 
It transforms raw text data into a spatial layer with high-quality,
magnitude-colored beachball (moment tensor) symbols.

## Key Features
- Dynamic **Mw calculation** from moment tensors.
- Automatic color-coding by magnitude.
- Seamless **SVG generation** and spatial mapping.
- Works as a Processing Algorithm in QGIS Toolbox.

📦 Requirements
To use this plugin, you must have the following Python libraries installed in your QGIS environment:

ObsPy: For moment tensor to beachball geometry conversion.

Matplotlib & NumPy: For data processing and rendering.

🛠 Installation
1. Download: Download this repository as a .zip file.

2. Open QGIS: Go to the Plugins menu -> Manage and Install Plugins...

3. Install from ZIP: * Click the Install from ZIP tab on the left sidebar.

    Select the downloaded .zip file.

    Click Install Plugin.

4. Activation: Once installed, a new Beachball Icon will appear in your Toolbar and under the Seismology Tools menu.

📖 How to Use
1. Launch: Click the beachball icon on the toolbar.

2. Select File: Browse for your catalog text file (e.g., events.txt).

3. Choose Format: Select the appropriate format from the dropdown:

    GMT psvelomeca

    GMT psmeca

    CMTSOLUTION

    Full format

    AFAD Format

4. Run: Click Run. The plugin will automatically:

Validate the file content.

Generate a GeoPackage (.gpkg) layer in your input directory.

Create a subfolder named focal_mech_svg/ containing all beachball images.

🎨 Visualization LogicThe plugin automatically colors beachballs based on their Moment Magnitude 
(Mw):Magnitude (Mw)Color
Mw < 5.0🔵 Blue5.0 ≤ 
Mw < 6.0🟢 Green6.0 ≤ 
Mw < 7.0🟣 Purple
Mw ≥ 7.0🔴 Red

## Contributing
Feel free to open issues or submit pull requests to improve the parsing logic for other formats!

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from qgis.core import (QgsProcessingAlgorithm, QgsProcessingParameterFile, 
                       QgsProcessingParameterEnum, QgsVectorLayer, QgsField, 
                       QgsFeature, QgsGeometry, QgsPointXY, QgsProject,
                       QgsProcessingProvider, QgsApplication, QgsVectorFileWriter)
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction
from PyQt5.QtCore import QVariant
from obspy.imaging.beachball import beachball

# PROVIDER Class ---
class GlobalCMTProvider(QgsProcessingProvider):
    def __init__(self):
        super().__init__()

    def loadAlgorithms(self):
        self.addAlgorithm(GlobalCMTPlotter())

    def id(self): return 'globalcmt'
    def name(self): return 'Global CMT Tools'
    def icon(self): return QgsProcessingProvider.icon(self)

# (GUI & Toolbar) ---
class GlobalCMTPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.action = None

    def initGui(self):
        self.provider = GlobalCMTProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        self.action = QAction(
            QIcon(icon_path),
            "Global CMT Beachball Plotter",
            self.iface.mainWindow()
        )
        self.action.triggered.connect(self.run)
        
        self.iface.addPluginToMenu("&Seismology Tools", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
        self.iface.removePluginMenu("&Seismology Tools", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        from qgis import processing
        processing.execAlgorithmDialog("globalcmt:global_cmt_plotter")

class GlobalCMTPlotter(QgsProcessingAlgorithm):
    INPUT_FILE = 'INPUT_FILE'
    FORMAT_TYPE = 'FORMAT_TYPE'
    FORMATS = ['GMT psvelomeca', 'GMT psmeca', 'CMTSOLUTION', 'Full format']

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile(self.INPUT_FILE, 'Select Global CMT Catalog File', extension='txt'))
        self.addParameter(QgsProcessingParameterEnum(self.FORMAT_TYPE, 'Choose Catalog Format', options=self.FORMATS))

    def createInstance(self): return GlobalCMTPlotter()
    def name(self): return 'global_cmt_plotter'
    def displayName(self): return 'Global CMT Beachball Plotter'
    def group(self): return 'Seismology'
    def groupId(self): return 'seismology'

    def get_mw_color(self, mw):
        if mw < 5.0: return "#0C36EE" # Blue
        elif mw < 6.0: return '#41E600' # Green
        elif mw < 7.0: return "#B01ADE" # Purple
        else: return "#F70000" # Red

    def processAlgorithm(self, parameters, context, feedback):
        file_path = self.parameterAsFile(parameters, self.INPUT_FILE, context)
        format_idx = self.parameterAsInt(parameters, self.FORMAT_TYPE, context)
        format_name = self.FORMATS[format_idx]
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        content_full = "".join(lines)

        is_valid = False
        try:
            if format_name == 'GMT psvelomeca' and len(lines) > 0:
                if len(lines[0].split()) >= 11: is_valid = True
            elif format_name == 'GMT psmeca' and len(lines) > 0:
                if len(lines[0].split()) >= 10: is_valid = True
            elif format_name == 'CMTSOLUTION':
                if "event name:" in content_full.lower() and "mrr:" in content_full.lower():
                    is_valid = True
            elif format_name == 'Full format':
                if "event name:" in content_full.lower() and "mw =" in content_full.lower():
                    is_valid = True
        except:
            is_valid = False

        if not is_valid:
            feedback.reportError(f"CRITICAL ERROR: The file content does not match the selected format: '{format_name}'. Please verify your input.", fatalError=True)
            return {}

        base_dir = os.path.dirname(file_path)
        svg_dir = os.path.join(base_dir, "focal_mech_svg")
        if not os.path.exists(svg_dir): os.makedirs(svg_dir)
        
        output_gpkg = os.path.join(base_dir, f"CMT_Results_{format_name}.gpkg")

        layer = QgsVectorLayer("Point?crs=epsg:4326", f"CMT_{format_name}", "memory")
        pr = layer.dataProvider()
        pr.addAttributes([
            QgsField("EventID", QVariant.String), 
            QgsField("Mw", QVariant.Double),
            QgsField("SVG_Path", QVariant.String)
        ])
        layer.updateFields()

        features = []
        
        if format_name in ['GMT psvelomeca', 'GMT psmeca']:
            for line_idx, line in enumerate(lines):
                p = line.strip().split()
                if not p: continue
                try:
                    feat = None
                    if format_name == 'GMT psvelomeca' and len(p) >= 11:
                        lon, lat = float(p[0]), float(p[1])
                        fm = [float(p[2]), float(p[3]), float(p[4])]
                        m0 = float(p[8]) * (10**float(p[9]))
                        mw = (2.0/3.0) * (np.log10(m0) - 16.1)
                        feat = self.create_event(lon, lat, mw, fm, p[10], svg_dir)
                        
                    elif format_name == 'GMT psmeca' and len(p) >= 10:
                        lon, lat = float(p[0]), float(p[1])
                        mt = [float(p[3]), float(p[4]), float(p[5]), float(p[6]), float(p[7]), float(p[8])]
                        m0 = np.sqrt(np.sum(np.square(mt)) / 2.0) * (10**float(p[9]))
                        mw = (2.0/3.0) * (np.log10(m0) - 16.1)
                        eid = p[-1] if len(p) > 9 else f"Line_{line_idx}"
                        feat = self.create_event(lon, lat, mw, mt, eid, svg_dir)

                    if feat is not None:
                        features.append(feat)
                    else:
                        feedback.pushInfo(f"SKIPPED: Line {line_idx} could not be drawn.")

                except Exception as e:
                    feedback.pushInfo(f"SKIPPED: Line {line_idx} error: {str(e)}")
                    continue
                    
        elif format_name == 'CMTSOLUTION':
            raw_blocks = content_full.split("event name:")
            for i in range(1, len(raw_blocks)):
                block = "event name:" + raw_blocks[i]
                eid = "Unknown" # Default name
                try:
                    lines_b = [l.strip() for l in block.split('\n') if ":" in l]
                    d = {lb.split(':', 1)[0].strip().lower(): lb.split(':', 1)[1].strip() for lb in lines_b if len(lb.split(':', 1)) == 2}
                    
                    eid = d.get('event name', f"Block_{i}")
                    
                    # Veri kontrolü
                    required = ['mrr', 'mtt', 'mpp', 'mrt', 'mrp', 'mtp', 'latitude', 'longitude']
                    missing = [k for k in required if k not in d]
                    
                    if missing:
                        feedback.pushInfo(f"SKIPPED: Event {eid} is missing fields: {', '.join(missing)}")
                        continue

                    mt = [float(d['mrr']), float(d['mtt']), float(d['mpp']), 
                          float(d['mrt']), float(d['mrp']), float(d['mtp'])]
                    lat, lon = float(d['latitude']), float(d['longitude'])
                    
                    # Mw calculation and checking
                    m0 = np.sqrt(np.sum(np.square(mt)) / 2.0)
                    if m0 <= 0:
                        feedback.pushInfo(f"SKIPPED: Event {eid} has zero or negative Scalar Moment.")
                        continue
                    
                    mw = (2.0/3.0) * (np.log10(m0) - 16.1)
                    
                    feat = self.create_event(lon, lat, mw, mt, eid, svg_dir)
                    if feat:
                        features.append(feat)
                    else:
                        feedback.pushInfo(f"SKIPPED: Event {eid} - Beachball drawing failed (check tensor values).")

                except Exception as e:
                    feedback.pushInfo(f"SKIPPED: Event {eid} due to parsing error: {str(e)}")

        elif format_name == 'Full format':
            for block in content_full.split("Event name:"):
                if "Scalar Moment =" not in block: continue
                try:
                    lines_b = block.strip().split('\n')
                    eid = lines_b[0].strip()
                    mw = float(block.split("Mw =")[1].split()[0])
                    cmt_line = [l for l in lines_b if "CMT " in l and "sec" not in l][0]
                    parts = cmt_line.split()
                    lat, lon = float(parts[4]), float(parts[5])
                    fp_line = [l for l in lines_b if "Fault plane:" in l][0]
                    fm = [float(fp_line.split("strike=")[1].split()[0]), 
                          float(fp_line.split("dip=")[1].split()[0]), 
                          float(fp_line.split("slip=")[1].split()[0])]
                    features.append(self.create_event(lon, lat, mw, fm, eid, svg_dir))
                except: continue

        if not features:
            feedback.reportError("No valid events parsed.", fatalError=True)
            return {}

        # memory layer
        layer.startEditing()
        # append data
        success = layer.addFeatures(features)
        layer.commitChanges()

        # count features
        feedback.pushInfo(f"Features added to memory layer: {layer.featureCount()}")

        pr.addFeatures(features)

        # --- Save Permanently (GEOPACKAGE) ---
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.fileEncoding = "UTF-8"
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        
        # GeoPackage start
        result = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer, 
            output_gpkg, 
            context.transformContext(), 
            options
        )

        # checking
        error_code = result[0]
        
        if error_code == QgsVectorFileWriter.NoError:
            feedback.pushInfo(f"SUCCESS: Layer saved permanently to: {output_gpkg}")
            # OGR 
            final_layer = QgsVectorLayer(output_gpkg, f"Permanent_CMT_{format_name}", "ogr")
            if final_layer.isValid():
                QgsProject.instance().addMapLayer(final_layer)
            else:
                feedback.reportError("Permanent layer was created but is not valid. Check file permissions.")
        else:
            error_message = result[1]
            feedback.reportError(f"Could not save permanent file: {error_message}. Displaying temporary layer instead.")
            QgsProject.instance().addMapLayer(layer)

        feedback.pushInfo(f"Finished: {len(features)} events processed successfully.")
        return {'OUTPUT': output_gpkg}

    def create_event(self, lon, lat, mw, fm, eid, s_dir):
        try:
            color = self.get_mw_color(mw)
            svg_path = os.path.abspath(os.path.join(s_dir, f"{eid}.svg")).replace('\\', '/')
            
            try:
                fig = beachball(fm, size=200, facecolor=color)
                fig.savefig(svg_path, format='svg', transparent=True)
                plt.close(fig)
            except Exception as e:
                # Obspy error 
                print(f"Beachball Error for {eid}: {str(e)}")
                return None

            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
            feat.setAttributes([str(eid), float(mw), str(svg_path)])
            return feat
        except:
            return None

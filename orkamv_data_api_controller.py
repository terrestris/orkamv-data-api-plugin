# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ORKa.MV Data API
                                 A QGIS plugin
 This plugin downloads a geopackage from the ORKa.MV Data API
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2022-01-19
        git sha              : $Format:%H$
        copyright            : (C) 2022 by terrestris GmbH & Co. KG
        email                : info@terrestris.de
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from typing import Optional, Dict, List
import os
import tempfile

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCheckBox

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.gui import QgisInterface, QgsFileWidget
from qgis.core import Qgis, QgsVectorLayer, QgsSettings, QgsApplication, QgsCoordinateReferenceSystem, \
    QgsDataProvider, QgsProject
from qgis.PyQt.QtWidgets import QMessageBox

from .network_request import get_json
from .types import TaskStatus, LayerSelectionMode, LayerGroup, ErrorReason, LAYER_GROUPS_PROP_NAME, LAYER_BASE_NAME
from .task_resources import ResourcesTask
from .orkamv_data_api_plugin_dialog import OrkamvDataApiPluginDialog
from .task_geopackage import GeopackageTask


class OrkamvDataApiController:

    iface: QgisInterface
    dlg: Optional[OrkamvDataApiPluginDialog] = None
    # tr: Callable = None

    geopackage_task: Optional[GeopackageTask] = None
    resources_task: Optional[ResourcesTask] = None
    geopackage_task_status: TaskStatus = TaskStatus.COMPLETED
    resources_task_status: TaskStatus = TaskStatus.COMPLETED

    result_layers: Dict[str, QgsVectorLayer]
    result_layer_order: List[str]
    result_style_files: Dict[str, str]
    result_symbols_dir: str

    selection_mode: LayerSelectionMode = LayerSelectionMode.ALL
    layer_groups_cache: Dict[str, List[LayerGroup]] = {}

    def __init__(self, iface: QgisInterface):
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'OrkamvDataApiPlugin_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        # return QCoreApplication.translate('OrkamvDataApiPlugin', message)
        return QCoreApplication.translate('OrkamvDataApiController', message)

    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        self.dlg = OrkamvDataApiPluginDialog()

        # connect handlers
        self.dlg.download_start_button.clicked.connect(self.start_download)
        self.dlg.persistance_radio_temporary.toggled.connect(self.toggle_persistance_mode)
        self.dlg.persistance_radio_todir.toggled.connect(self.check_required_for_download)
        self.dlg.svg_combo_box.currentIndexChanged.connect(self.check_required_for_download)
        self.dlg.server_url_edit.textChanged.connect(self.check_required_for_download)
        self.dlg.layer_radio_groups.toggled.connect(self.toggle_layer_selection_mode)
        self.dlg.layer_radio_all.toggled.connect(self.toggle_layer_selection_mode)

        # setup extent widget
        self.dlg.extent_widget.setOutputCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        self.dlg.extent_widget.setMapCanvas(self.iface.mapCanvas())
        self.dlg.extent_widget.extentChanged.connect(self.check_required_for_download)
        self.dlg.extent_widget.setNullValueAllowed(True, self.tr('Please choose an extent'))
        self.dlg.extent_widget.clear()

        # setup file widget
        home = os.path.expanduser('~')
        self.dlg.persistance_path_widget.setDefaultRoot(home)
        self.dlg.persistance_path_widget.setStorageMode(QgsFileWidget.GetDirectory)
        self.dlg.persistance_path_widget.fileChanged.connect(self.check_dir)
        self.dlg.persistance_path_widget.fileChanged.connect(self.check_required_for_download)
        self.dlg.persistance_path_widget.lineEdit().setEnabled(False)

        self.update_layer_group_selection_visibility()

        s = QgsSettings()
        server_url = s.value('orka_mv_data_api_plugin/server_url', '')
        self.dlg.server_url_edit.setText(server_url)

        self.check_required_for_download()

        self.read_svg_dirs()

        # show the dialog
        self.dlg.show()

        # Run the dialog event loop
        result = self.dlg.exec_()

        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    def read_svg_dirs(self):
        self.dlg.svg_combo_box.clear()

        folders = QgsApplication.instance().svgPaths()

        if len(folders) == 0:
            self.dlg.svg_combo_box.addItem(self.tr('WARNING: No SVG folder available! Please check your preferences.'),
                                           None)
        else:
            for folder in folders:
                self.dlg.svg_combo_box.addItem(folder, folder)
            self.dlg.svg_combo_box.setCurrentIndex(len(folders) - 1)

    def check_dir(self):
        if self.dlg.persistance_path_widget.filePath() != '' and \
                any(os.scandir(self.dlg.persistance_path_widget.filePath())):
            dialog = QMessageBox()
            dialog.setText(self.tr('The directory is not empty'))
            dialog.setInformativeText(self.tr('Do you want to overwrite the content?'))
            dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            dialog.setDefaultButton(QMessageBox.No)
            result = dialog.exec_()
            if result == QMessageBox.No:
                self.dlg.persistance_path_widget.setFilePath('')

    def toggle_persistance_mode(self):
        if self.dlg.persistance_radio_todir.isChecked():
            self.dlg.persistance_path_widget.setEnabled(True)
        else:
            self.dlg.persistance_path_widget.setEnabled(False)
        self.check_required_for_download()

    def check_required_for_download(self):
        path_valid = self.dlg.persistance_radio_temporary.isChecked() or \
                     self.dlg.persistance_path_widget.filePath()
        layer_selection_valid = self.is_layer_selection_valid()
        check = self.dlg.extent_widget.isValid() \
            and self.geopackage_task_status != TaskStatus.STARTED \
            and self.dlg.svg_combo_box.currentData() is not None \
            and path_valid \
            and self.dlg.server_url_edit.text() \
            and layer_selection_valid
        self.dlg.download_start_button.setEnabled(bool(check))

    def start_download(self):
        self.dlg.download_start_button.setEnabled(False)

        url = self.dlg.server_url_edit.text()

        s = QgsSettings()
        s.setValue('orka_mv_data_api_plugin/server_url', url)

        if self.dlg.persistance_radio_temporary.isChecked():
            target_dir = tempfile.mkdtemp()
        else:
            target_dir = self.dlg.persistance_path_widget.filePath()

        extent = self.dlg.extent_widget.outputExtent()

        svg_dir = self.dlg.svg_combo_box.currentData()

        if self.selection_mode == LayerSelectionMode.ALL:
            self.geopackage_task = GeopackageTask(url, target_dir, extent)
        elif self.selection_mode == LayerSelectionMode.GROUP:
            layers = self.get_flat_group_layers()
            self.geopackage_task = GeopackageTask(url, target_dir, extent, layers=layers)

        self.geopackage_task.progressChanged.connect(self.update_progress)
        self.geopackage_task.taskCompleted.connect(self.geopackage_completed)
        self.geopackage_task.taskTerminated.connect(self.geopackage_terminated)
        self.geopackage_task_status = TaskStatus.STARTED

        self.resources_task = ResourcesTask(url, target_dir, svg_dir)
        self.resources_task.progressChanged.connect(self.update_progress)
        self.resources_task.taskCompleted.connect(self.resources_completed)
        self.resources_task.taskTerminated.connect(self.resources_terminated)
        self.resources_task_status = TaskStatus.STARTED

        QgsApplication.taskManager().addTask(self.geopackage_task)
        QgsApplication.taskManager().addTask(self.resources_task)

    def geopackage_terminated(self):
        self.geopackage_task_status = TaskStatus.CANCELLED
        if self.resources_task_status == TaskStatus.STARTED:
            self.resources_task.cancel()
            self.show_message(self.geopackage_task.error_reason, self.geopackage_task.error_message)
        else:
            self.reset()

    def resources_terminated(self):
        self.resources_task_status = TaskStatus.CANCELLED
        if self.geopackage_task_status == TaskStatus.STARTED:
            self.geopackage_task.cancel()
            self.show_message(self.resources_task.error_reason, self.geopackage_task.error_message)
        else:
            self.reset()

    def geopackage_completed(self):
        self.geopackage_task_status = TaskStatus.COMPLETED
        # self.result_layers = self.geopackage_task.get_results()
        if self.resources_task_status == TaskStatus.COMPLETED:
            self.download_finished()

    def resources_completed(self):
        self.resources_task_status = TaskStatus.COMPLETED
        # self.result_layer_order, self.result_style_files = self.resources_task.get_results()
        if self.geopackage_task_status == TaskStatus.COMPLETED:
            self.download_finished()

    def download_finished(self):
        gpkg_layer = QgsVectorLayer(self.geopackage_task.file_name, 'parent', 'ogr')
        layers: Dict[str, QgsVectorLayer] = {}

        for sub_layer in gpkg_layer.dataProvider().subLayers():
            name = sub_layer.split(QgsDataProvider.SUBLAYER_SEPARATOR)[1]
            uri = f'{self.geopackage_task.file_name}|layername={name}'
            layers[name] = QgsVectorLayer(uri, name, 'ogr')

        root = QgsProject.instance().layerTreeRoot()
        group_name = self.generate_group_name()
        group = root.insertGroup(0, group_name)

        layer_groups = self.get_layer_groups()
        if self.selection_mode == LayerSelectionMode.ALL and len(layer_groups) == 0:
            try:
                api_url = self.get_groups_endpoint()
                self.download_group_config(api_url)
                layer_groups = self.get_layer_groups()
            except Exception:
                layer_groups = []
        if self.selection_mode == LayerSelectionMode.GROUP:
            layer_groups = self.get_selected_groups()
        group.setCustomProperty(LAYER_GROUPS_PROP_NAME, layer_groups)

        for layer_name in reversed(self.resources_task.layer_order):
            if layer_name in layers:
                layer = layers[layer_name]
                if layer_name in self.resources_task.style_files:
                    layer.loadNamedStyle(self.resources_task.style_files[layer_name])
                QgsProject.instance().addMapLayer(layer, False)
                group.addLayer(layer)

        self.dlg.done(True)

    def update_progress(self):
        if self.resources_task_status == TaskStatus.CANCELLED or self.geopackage_task_status == TaskStatus.CANCELLED:
            return

        if self.resources_task_status == TaskStatus.COMPLETED:
            progress = 25
        else:
            progress = self.resources_task.progress() / 4

        if self.geopackage_task_status == TaskStatus.COMPLETED:
            progress += 75
        else:
            progress += self.geopackage_task.progress() * 3 / 4

        self.dlg.download_progress_bar.setValue(progress)

    def reset(self):
        self.dlg.download_progress_bar.setValue(0)
        self.dlg.layer_radio_all.click()
        self.check_required_for_download()

    def show_message(self, reason: ErrorReason, message: Optional[str] = None):
        message: str
        level: Qgis.MessageLevel = Qgis.Warning

        if reason == ErrorReason.ERROR:
            message = self.tr('An error occurred. Please try again later and contact an ' +
                              'administrator if the error still occurs.')
            level = Qgis.Critical
        elif reason == ErrorReason.TIMEOUT:
            message = self.tr('The processing timed out. Please try again with a smaller area.')
        elif reason == ErrorReason.BBOX_TOO_BIG:
            message = self.tr('The chosen bounding box is too big.')
        elif reason == ErrorReason.NO_THREADS_AVAILABLE:
            message = self.tr('Current job limit is reached. Please try again in a few minutes.')
        elif reason == ErrorReason.NETWORK_ERROR:
            message = self.tr('Network error: {}').format(message)
        elif reason == ErrorReason.GROUPS_ERROR:
            message = self.tr('Could not download layer groups. Please make sure you entered ' +
                              'a correct server url and try again.')
        else:
            message = self.tr('Unknown message type: {}: {}').format(str(reason), message)
            level: Qgis.Critical

        self.iface.messageBar().pushMessage(message, level=level)

    def toggle_layer_selection_mode(self):
        if self.dlg.layer_radio_all.isChecked():
            self.enable_layer_selection_mode_all()
        elif self.dlg.layer_radio_groups.isChecked():
            self.enable_layer_selection_mode_group()
        self.check_required_for_download()

    def enable_layer_selection_mode_group(self):
        self.selection_mode = LayerSelectionMode.GROUP
        api_url = self.get_groups_endpoint()

        if api_url not in self.layer_groups_cache:
            try:
                self.download_group_config(api_url)
            except Exception:
                self.show_message(ErrorReason.GROUPS_ERROR)
                self.dlg.layer_radio_all.click()
                return

        self.refresh_layer_group_selection(self.layer_groups_cache[api_url])
        self.update_layer_group_selection_visibility()

    def download_group_config(self, api_url):
        data = get_json(api_url)
        self.layer_groups_cache[api_url] = data

    def enable_layer_selection_mode_all(self):
        self.selection_mode = LayerSelectionMode.ALL
        self.update_layer_group_selection_visibility()

    def refresh_layer_group_selection(self, group_config: List[LayerGroup]):
        layout = self.dlg.layer_select_groups.layout()
        for group in group_config:
            checkbox = QCheckBox(group['title'])
            checkbox.stateChanged.connect(self.check_required_for_download)
            layout.addWidget(checkbox)

    def update_layer_group_selection_visibility(self):
        visible = self.selection_mode == LayerSelectionMode.GROUP
        self.dlg.layer_select_groups_area.setVisible(visible)

    def is_layer_selection_valid(self) -> bool:
        """ Check if layer selection is valid.

        Layer selection is valid if either selection mode is ALL
        or at least on group was selected in selection mode GROUP.
        """
        if self.selection_mode == LayerSelectionMode.ALL:
            return True
        if self.selection_mode == LayerSelectionMode.GROUP:
            checkbox_container = self.dlg.layer_select_groups.layout()
            for itemIdx in range(checkbox_container.count()):
                checkbox = checkbox_container.itemAt(itemIdx).widget()
                if checkbox.checkState() == Qt.Checked:
                    return True
        return False

    def get_selected_group_names(self) -> List[str]:
        checkbox_container = self.dlg.layer_select_groups.layout()
        groups = []
        for itemIdx in range(checkbox_container.count()):
            checkbox = checkbox_container.itemAt(itemIdx).widget()
            if checkbox.checkState() == Qt.Checked:
                groups.append(checkbox.text())
        return groups

    def get_layer_groups(self) -> List[LayerGroup]:
        api_url = self.get_groups_endpoint()
        if api_url not in self.layer_groups_cache:
            return []
        return self.layer_groups_cache[api_url]

    def get_selected_groups(self) -> List[LayerGroup]:
        layer_groups = self.get_layer_groups()
        selected_group_names = self.get_selected_group_names()
        return [group for group in layer_groups if group['title'] in selected_group_names]

    def get_flat_group_layers(self) -> List[str]:
        """Get all layer names of all selected groups.
        """
        layers = []
        layer_groups = self.get_layer_groups()
        selected_group_names = self.get_selected_group_names()
        for group in layer_groups:
            if group['title'] in selected_group_names:
                layers = layers + group['layers']
        # make sure each layer name exists only once in list
        return list(set(layers))

    def get_groups_endpoint(self) -> str:
        base_url = self.dlg.server_url_edit.text()
        base_url = base_url[:-1] if base_url.endswith('/') else base_url
        return f'{base_url}/data/groups'

    def generate_group_name(self):
        """Generate a unique group name.

        Generates a unique group name by adding a number to the static group name.
        The number is determined by the highest suffix number that is found within
        the list of existing layer groups.
        """
        root = QgsProject.instance().layerTreeRoot()
        children = [child for child in root.children() if child.name().startswith(LAYER_BASE_NAME)]
        if len(children) == 0:
            return LAYER_BASE_NAME
        suffixes = []
        for child in children:
            suffix = child.name()[len(LAYER_BASE_NAME):]
            if len(suffix) == 0:
                suffixes.append(0)
                continue
            # strip the separator from the actual suffix
            suffixes.append(int(suffix[1:]))
        max_number = max(suffixes)
        return f'{LAYER_BASE_NAME} {max_number + 1}'

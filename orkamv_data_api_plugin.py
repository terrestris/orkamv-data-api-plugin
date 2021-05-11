# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ORKa.MV Data API
                                 A QGIS plugin
 This plugin downloads a geopackage from the ORKa.MV Data API
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-05-03
        git sha              : $Format:%H$
        copyright            : (C) 2021 by terrestris GmbH & Co. KG
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
import tempfile
from typing import Optional, Dict, List

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.gui import QgisInterface, QgsFileWidget

from qgis.core import Qgis, QgsProject, QgsApplication, \
    QgsCoordinateReferenceSystem, QgsVectorLayer

from .types import TaskStatus, ErrorReason
from .resources_task import ResourcesTask
from .geopackage_task import GeopackageTask

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .orkamv_data_api_plugin_dialog import OrkamvDataApiPluginDialog
import os.path


class OrkamvDataApiPlugin:
    """QGIS Plugin Implementation."""

    iface: QgisInterface
    dlg: Optional[OrkamvDataApiPluginDialog] = None

    geopackage_task: Optional[GeopackageTask] = None
    resources_task: Optional[ResourcesTask] = None
    geopackage_task_status: TaskStatus = TaskStatus.COMPLETED
    resources_task_status: TaskStatus = TaskStatus.COMPLETED

    result_layers: Dict[str, QgsVectorLayer]
    result_layer_order: List[str]
    result_style_files: Dict[str, str]
    result_symbols_dir: str

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            '{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&ORKa.MV Data API')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = False

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
        return QCoreApplication.translate('OrkamvDataApiPlugin', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/orkamv_data_api_plugin/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'ORKa.MV Data API'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&ORKa.MV Data API'),
                action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start:
            self.first_start = False
            self.dlg = OrkamvDataApiPluginDialog()

            self.dlg.server_url_edit.setText('http://orka-mv.terrestris.de/api/')

            # connect handlers
            self.dlg.download_start_button.clicked.connect(self.start_download)
            self.dlg.persistance_radio_temporary.toggled.connect(self.toggle_persistance_mode)
            self.dlg.svg_combo_box.currentIndexChanged.connect(self.check_required_for_download)

            # setup extent widget
            self.dlg.extent_widget.setOutputCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
            self.dlg.extent_widget.setMapCanvas(self.iface.mapCanvas())
            self.dlg.extent_widget.extentChanged.connect(self.check_required_for_download)
            self.dlg.extent_widget.setNullValueAllowed(True, 'Please choose an extent')
            self.dlg.extent_widget.clear()

            # setup file widget
            home = os.path.expanduser('~')
            self.dlg.persistance_path_widget.setDefaultRoot(home)
            self.dlg.persistance_path_widget.setStorageMode(QgsFileWidget.GetDirectory)
            self.dlg.persistance_path_widget.fileChanged.connect(self.check_dir)
            self.dlg.persistance_path_widget.fileChanged.connect(self.check_required_for_download)
            self.dlg.persistance_path_widget.lineEdit().setEnabled(False)

            self.check_required_for_download()
        else:
            self.reset()

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

    def check_required_for_download(self):
        path = self.dlg.persistance_path_widget.filePath()
        path_valid = self.dlg.persistance_radio_temporary.isChecked() or \
            (path is not None and path != '')
        check = self.dlg.extent_widget.isValid() \
            and self.geopackage_task_status != TaskStatus.STARTED \
            and self.dlg.svg_combo_box.currentData() is not None \
            and path_valid
        self.dlg.download_start_button.setEnabled(check)

    def start_download(self):
        self.dlg.download_start_button.setEnabled(False)

        url = self.dlg.server_url_edit.text()

        if self.dlg.persistance_radio_temporary.isChecked():
            target_dir = tempfile.mkdtemp()
        else:
            target_dir = self.dlg.persistance_path_widget.filePath()

        extent = self.dlg.extent_widget.outputExtent()

        svg_dir = self.dlg.svg_combo_box.currentData()

        self.geopackage_task = GeopackageTask(url, target_dir, extent)
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
            self.show_message(self.geopackage_task.error_reason)
        else:
            self.reset()

    def resources_terminated(self):
        self.resources_task_status = TaskStatus.CANCELLED
        if self.geopackage_task_status == TaskStatus.STARTED:
            self.geopackage_task.cancel()
            self.show_message(self.resources_task.error_reason)
        else:
            self.reset()

    def geopackage_completed(self):
        self.geopackage_task_status = TaskStatus.COMPLETED
        self.result_layers = self.geopackage_task.get_results()
        if self.resources_task_status == TaskStatus.COMPLETED:
            self.download_finished()

    def resources_completed(self):
        self.resources_task_status = TaskStatus.COMPLETED
        self.result_layer_order, self.result_style_files = self.resources_task.get_results()
        if self.geopackage_task_status == TaskStatus.COMPLETED:
            self.download_finished()

    def download_finished(self):
        root = QgsProject.instance().layerTreeRoot()
        group = root.insertGroup(0, 'ORKa.MV Data API')

        for layer_name in reversed(self.resources_task.layer_order):
            if layer_name in self.geopackage_task.layers:
                layer = self.geopackage_task.layers[layer_name]
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
        self.check_required_for_download()

    def show_message(self, reason: ErrorReason, message: Optional[str] = None):
        message: str
        level: Qgis.MessageLevel = Qgis.Warning

        if reason == ErrorReason.ERROR:
            message = self.tr('An error occured. Please try again layer and contact an ' +
                              'administrator if the error still occurs.')
            level = Qgis.Critical
        elif reason == ErrorReason.TIMEOUT:
            message = self.tr('The processing timed out. Please try again with a smaller area.')
        elif reason == ErrorReason.BBOX_TOO_BIG:
            message = self.tr('The chosen bounding box is too big.')
        elif reason == ErrorReason.NO_THREADS_AVAILABLE:
            message = self.tr('Current job limit is reached. Please try again in a few minutes.')
        else:
            message = self.tr('Unknown message type: {}: {}').format(str(reason), message)
            level: Qgis.Critical

        self.iface.messageBar().pushMessage(message, level=level)

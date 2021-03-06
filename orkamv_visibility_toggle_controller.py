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
import os
from typing import Optional, List, Dict

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from PyQt5.QtWidgets import QCheckBox, QWidget, QVBoxLayout, QSizePolicy
from PyQt5.QtCore import Qt
from qgis.gui import QgisInterface
from qgis.core import QgsProject, QgsLayerTreeGroup, QgsLayerTreeLayer

from .types import LAYER_GROUPS_PROP_NAME, LayerGroup
from .orkamv_visibility_toggle_plugin_dialog import OrkamvVisibilityTogglePluginDialog


class OrkamvVisibilityToggleController:

    iface: QgisInterface
    dlg: Optional[OrkamvVisibilityTogglePluginDialog] = None

    selected_layer_group: str = None
    selected_groups_hash: Dict[str, List[str]] = {}

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
        return QCoreApplication.translate('OrkamvDataApiPlugin', message)

    def run(self):
        self.dlg = OrkamvVisibilityTogglePluginDialog()

        self.refresh_groups_hash()
        self.populate_layer_combo()
        self.init_group_selection()
        self.connect_events()

        # show the dialog
        self.dlg.show()

        # Run the dialog event loop
        result = self.dlg.exec_()

        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    def connect_events(self):
        QgsProject.instance().layersAdded.connect(self.reset)
        QgsProject.instance().layersRemoved.connect(self.reset)
        self.dlg.layer_select_combo.activated.connect(self.on_combo_change)

    def reset(self):
        self.refresh_groups_hash()
        self.populate_layer_combo()
        config = self.get_groups_config()
        self.populate_group_selection(config)

    def refresh_groups_hash(self):
        layer_groups = self.get_layer_groups()
        layer_group_names = [layer_group.name() for layer_group in layer_groups]
        for group in layer_groups:
            if group.name() not in self.selected_groups_hash:
                group_config = group.customProperty(LAYER_GROUPS_PROP_NAME)
                self.selected_groups_hash[group.name()] = [g['title'] for g in group_config]
        to_delete = []
        for key in self.selected_groups_hash:
            if key not in layer_group_names:
                to_delete.append(key)
        for k in to_delete:
            if k in self.selected_groups_hash:
                del self.selected_groups_hash[k]

    def init_group_selection(self):
        config = self.get_groups_config()
        self.populate_group_selection(config)

    def populate_layer_combo(self):
        self.dlg.layer_select_combo.clear()
        layer_groups = self.get_layer_groups()
        for group in layer_groups:
            self.dlg.layer_select_combo.addItem(group.name())
        if self.selected_layer_group is not None and self.selected_layer_group in self.selected_groups_hash:
            self.dlg.layer_select_combo.setCurrentText(self.selected_layer_group)
        elif len(layer_groups) > 0:
            self.selected_layer_group = layer_groups[0].name()
            self.dlg.layer_select_combo.setCurrentText(self.selected_layer_group)

    def populate_group_selection(self, group_config: List[LayerGroup]):
        widget = QWidget()
        layout = QVBoxLayout()
        selected_groups = self.selected_groups_hash[self.selected_layer_group]
        for group in group_config:
            title = group['title']
            checkbox = QCheckBox(title)
            check_state = Qt.Checked if title in selected_groups else Qt.Unchecked
            checkbox.setCheckState(check_state)
            checkbox.stateChanged.connect(lambda state, t=title: self.update_visibility_for_group(t, state))
            layout.addWidget(checkbox)
        widget.setLayout(layout)
        widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.dlg.layer_select_groups_area.setWidget(widget)

    def get_layer_groups(self) -> List[QgsLayerTreeGroup]:
        root = QgsProject.instance().layerTreeRoot()
        children = root.children()
        layer_groups = []
        for child in children:
            is_group = root.isGroup(child)
            has_group_config = child.customProperty(LAYER_GROUPS_PROP_NAME) is not None
            if is_group and has_group_config:
                layer_groups.append(child)
        return layer_groups

    def get_layer_group_by_name(self, name: str) -> QgsLayerTreeGroup:
        root = QgsProject.instance().layerTreeRoot()
        children = root.children()
        for child in children:
            if child.name() == name:
                return child

    def on_combo_change(self):
        self.selected_layer_group = self.dlg.layer_select_combo.currentText()
        config = self.get_groups_config()
        self.populate_group_selection(config)

    def update_visibility_for_group(self, group_name: str, check_state: Qt.CheckState):
        layer_group_name = self.selected_layer_group
        groups_config = self.get_groups_config()
        layer_names_to_change = self.get_layers_names_for_group(group_name, groups_config)
        layers_to_change = self.get_layers_by_name(layer_group_name, layer_names_to_change)
        visible = check_state == Qt.Checked
        self.change_visibility_for_layers(layers_to_change, visible)
        if visible:
            self.selected_groups_hash[self.selected_layer_group].append(group_name)
        else:
            self.selected_groups_hash[self.selected_layer_group].remove(group_name)

    def get_groups_config(self) -> List[LayerGroup]:
        layer_group_name = self.selected_layer_group
        layer_group = self.get_layer_group_by_name(layer_group_name)
        if layer_group is None:
            return []
        return layer_group.customProperty(LAYER_GROUPS_PROP_NAME)

    def change_visibility_for_layers(self, layers: List[QgsLayerTreeLayer], visible: bool):
        for layer in layers:
            layer.setItemVisibilityChecked(visible)

    def get_layers_names_for_group(self, group_name: str, group_config: List[LayerGroup]):
        layer_names = []
        for group in group_config:
            if group['title'] == group_name:
                layer_names = layer_names + group['layers']
        return layer_names

    def get_layers_by_name(self, layer_group_name: str, layer_names: List[str]) -> List[QgsLayerTreeLayer]:
        layer_group = self.get_layer_group_by_name(layer_group_name)
        if layer_group is None:
            return []
        return [layer for layer in layer_group.findLayers() if layer.name() in layer_names]

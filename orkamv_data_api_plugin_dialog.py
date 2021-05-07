# -*- coding: utf-8 -*-
"""
/***************************************************************************
 OrkamvDataApiPluginDialog
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

import os
from typing import Optional

from PyQt5.QtWidgets import QPushButton, QLineEdit, QProgressBar, QComboBox, QRadioButton
from qgis.PyQt import uic
from qgis.PyQt import QtWidgets

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'orkamv_data_api_plugin_dialog_base.ui'))


class OrkamvDataApiPluginDialog(QtWidgets.QDialog, FORM_CLASS):
    draw_extent_button: QPushButton
    extent_edit: QLineEdit
    download_start_button: QPushButton
    download_cancel_button: QPushButton
    download_progress_bar: QProgressBar
    layer_extent_combo_box: QComboBox
    visible_extent_button: QPushButton
    server_url_edit: QLineEdit
    persistance_radio_temporary: QRadioButton
    persistance_radio_todir: QRadioButton
    persistance_path_edit: QLineEdit

    def __init__(self, parent=None):
        """Constructor."""
        super(OrkamvDataApiPluginDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

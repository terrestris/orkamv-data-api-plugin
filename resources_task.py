import json
import os
import shutil
import tempfile
import zipfile
from typing import Dict, List, Tuple

from PyQt5.QtCore import QUrl
from PyQt5.QtNetwork import QNetworkRequest
from qgis._core import QgsTask, QgsNetworkAccessManager, QgsSettings


class ResourcesTask(QgsTask):
    style_files: Dict[str, str] = {}
    layer_order: List[str]

    def __init__(self, base_url: str, target_dir: str):
        self.base_url = base_url[:-1] if base_url.endswith('/') else base_url
        self.target_dir = target_dir
        super().__init__('Download Resources Job', QgsTask.CanCancel)  # TODO: better description

    def run(self):
        req = QNetworkRequest()
        req.setUrl(QUrl(f'{self.base_url}/data/styles'))

        res = QgsNetworkAccessManager.blockingGet(req, forceRefresh=True)

        if self.isCanceled():
            return False

        self.setProgress(50)

        _, tmp_file_name = tempfile.mkstemp(suffix='.zip')

        with open(tmp_file_name, 'w+b') as fp:
            fp.write(res.content().data())

        with zipfile.ZipFile(tmp_file_name, 'r') as zip_ref:
            zip_ref.extractall(self.target_dir)

        os.remove(tmp_file_name)

        if self.isCanceled():
            return False

        styles_dir = os.path.join(self.target_dir, 'styles')

        for file_name in os.listdir(styles_dir):
            layer_name = os.path.splitext(file_name)[0]
            self.style_files[layer_name] = os.path.join(styles_dir, file_name)

        qs = QgsSettings()
        svg_folder = qs.value('svg/searchPathsForSVG')[-1]
        symbols_dir = os.path.join(self.target_dir, 'symbols')

        os.makedirs(svg_folder, exist_ok=True)

        for symbol_file_name in os.listdir(symbols_dir):
            shutil.copy(os.path.join(symbols_dir, symbol_file_name), svg_folder)

        with open(os.path.join(self.target_dir, 'layers.json'), 'r') as layer_order_file:
            data = json.loads(layer_order_file.read())
            self.layer_order = data

        if self.isCanceled():
            return False

        self.setProgress(100)

        return True

    def get_results(self) -> Tuple[List[str], Dict[str, str]]:
        return self.layer_order, self.style_files

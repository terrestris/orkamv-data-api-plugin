import json
import os
import tempfile
import zipfile
from typing import Dict, List

from PyQt5.QtCore import QUrl
from PyQt5.QtNetwork import QNetworkRequest
from qgis._core import QgsTask, QgsNetworkAccessManager


class ResourcesTask(QgsTask):
    style_files: Dict[str, str] = {}
    symbols_dir: str
    layer_order: List[str]

    def __init__(self, base_url: str, target_dir: str):
        self.base_url = base_url[:-1] if base_url.endswith('/') else base_url
        self.target_dir = target_dir
        super().__init__('Download Resources Job', QgsTask.CanCancel) # TODO: can cancel? better description

    def run(self):
        req = QNetworkRequest()
        req.setUrl(QUrl(f'{self.base_url}/data/styles'))

        res = QgsNetworkAccessManager.blockingGet(req, forceRefresh=True)

        self.setProgress(50)

        _, tmp_file_name = tempfile.mkstemp(prefix='.zip')

        with open(tmp_file_name, 'w+b') as fp:
            fp.write(res.content().data())

        styles_dir = os.path.join(self.target_dir, 'styles')

        with zipfile.ZipFile(tmp_file_name, 'r') as zip_ref:
            zip_ref.extractall(styles_dir)

        os.remove(tmp_file_name)

        self.setProgress(100)

        for file_name in os.listdir(styles_dir):
            layer_name = os.path.splitext(file_name)[0]
            self.style_files[layer_name] = os.path.join(styles_dir, file_name)

        self.symbols_dir = os.path.join(self.target_dir, 'symbols')

        with open(os.path.join(self.target_dir, 'layers.json'), 'r') as layer_order_file:
            data = json.loads(layer_order_file.read())
            self.layer_order = data

        return True
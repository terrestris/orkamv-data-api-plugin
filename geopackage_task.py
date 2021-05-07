import json
import os
import tempfile
from time import sleep
from typing import Tuple, Dict

from PyQt5.QtCore import QUrl
from PyQt5.QtNetwork import QNetworkRequest
from qgis._core import QgsNetworkAccessManager, QgsTask, QgsVectorLayer, QgsDataProvider


class GeopackageTask(QgsTask):

    job_id: int
    data_id: str
    layers: Dict[str, QgsVectorLayer] = []

    def __init__(self, base_url: str, extent: Tuple[float, float, float, float], target_dir: str):
        self.base_url = base_url[:-1] if base_url.endswith('/') else base_url
        self.extent = extent
        self.target_dir = target_dir
        super().__init__('Download Geopackage Job', QgsTask.CanCancel) # TODO: can cancel? better description

    def start_job(self):
        req_data = json.dumps({'bbox': self.extent}).encode('utf8')

        req = QNetworkRequest()
        req.setUrl(QUrl(f'{self.base_url}/jobs/'))
        req.setHeader(QNetworkRequest.ContentTypeHeader, 'application/json')

        res = QgsNetworkAccessManager.blockingPost(req, data=req_data, forceRefresh=True)
        res_data = json.loads(res.content().data().decode('utf8'))

        if not res_data['success']:
            raise Exception('not successful')

        self.job_id = res_data['job_id']

    def get_job_status(self) -> bool:
        req = QNetworkRequest()
        req.setUrl(QUrl(f'{self.base_url}/jobs/{self.job_id}'))
        # req.setHeader(QNetworkRequest.ContentTypeHeader, 'application/json')

        res = QgsNetworkAccessManager.blockingGet(req, forceRefresh=True)
        res_data = json.loads(res.content().data().decode('utf8'))

        if res_data['status'] == 'CREATED':
            self.data_id = res_data['data_id']
            return True
        elif res_data['status'] == 'ERROR':
            raise Exception('error')
        else:
            return False

    def run(self):
        self.setProgress(10)
        self.start_job()
        self.setProgress(20)
        while not self.get_job_status():
            sleep(0.5)
        self.setProgress(70)

        self.download_file()
        self.setProgress(100)

        return True

    def download_file(self):
        req = QNetworkRequest()
        req.setUrl(QUrl(f'{self.base_url}/data/{self.data_id}'))

        res = QgsNetworkAccessManager.blockingGet(req, forceRefresh=True)

        file_name = os.path.abspath(os.path.join(self.target_dir, 'geopackage.gpkg'))

        with open(file_name, 'w+b') as fp:
            fp.write(res.content().data())
            layer = QgsVectorLayer(file_name, 'parent', 'ogr')

            for sub_layer in layer.dataProvider().subLayers():
                name = sub_layer.split(QgsDataProvider.SUBLAYER_SEPARATOR)[1]
                uri = "%s|layername=%s" % (file_name, name,)
                self.layers[name] = QgsVectorLayer(uri, name, 'ogr')

        if self.target_dir is None:
            os.remove(file_name)

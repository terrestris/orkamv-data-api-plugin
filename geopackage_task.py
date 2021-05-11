import json
import os
from time import sleep
from typing import Dict, Optional

from PyQt5.QtCore import QUrl
from PyQt5.QtNetwork import QNetworkRequest
from qgis._core import QgsNetworkAccessManager, QgsTask, QgsVectorLayer, QgsDataProvider, QgsRectangle

from .types import ErrorReason, OrkamvApiException


class GeopackageTask(QgsTask):

    job_id: int
    data_id: str
    layers: Dict[str, QgsVectorLayer] = {}
    error_reason: Optional[ErrorReason] = None

    def __init__(self, base_url: str, target_dir: str, extent: QgsRectangle):
        self.base_url = base_url[:-1] if base_url.endswith('/') else base_url
        self.extent = (
            extent.xMinimum(),
            extent.yMinimum(),
            extent.xMaximum(),
            extent.yMaximum()
        )
        self.target_dir = target_dir
        super().__init__('ORKa.MV Data API Geopackage Job', QgsTask.Flag())

    def start_job(self):
        req_data = json.dumps({'bbox': self.extent}).encode('utf8')

        req = QNetworkRequest()
        req.setUrl(QUrl(f'{self.base_url}/jobs/'))
        req.setHeader(QNetworkRequest.ContentTypeHeader, 'application/json')

        res = QgsNetworkAccessManager.blockingPost(req, data=req_data, forceRefresh=True)

        res_data = json.loads(res.content().data().decode('utf8'))

        if not res_data.get('success'):
            self.handle_api_error(res_data)

        self.job_id = res_data['job_id']

        return True

    def get_job_status(self) -> bool:
        req = QNetworkRequest()
        req.setUrl(QUrl(f'{self.base_url}/jobs/{self.job_id}'))

        res = QgsNetworkAccessManager.blockingGet(req, forceRefresh=True)
        res_data = json.loads(res.content().data().decode('utf8'))

        if res_data.get('status') == 'CREATED':
            self.data_id = res_data['data_id']
            return True
        elif res_data.get('status') == 'RUNNING':
            return False
        else:
            self.handle_api_error(res_data)

    def handle_api_error(self, res_data: Dict):
        print(f'Status: {res_data.get("status")}, Message:{res_data.get("message")}')
        if 'message' in res_data:
            raise OrkamvApiException(ErrorReason(res_data['message']))
        if 'status' in res_data:
            raise OrkamvApiException(ErrorReason(res_data['status']))
        raise OrkamvApiException(ErrorReason.ERROR)

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

    def run(self):
        try:
            self.setProgress(10)
            self.start_job()

            if self.isCanceled():
                return False

            self.setProgress(20)
            while not self.get_job_status():
                if self.isCanceled():
                    return False
                sleep(0.5)

            if self.isCanceled():
                return False

            self.setProgress(80)
            self.download_file()

            if self.isCanceled():
                return False

            self.setProgress(100)
            return True

        except OrkamvApiException as e:
            self.error_reason = e.reason
            print(f'{self.error_reason}')
            return False

    def get_results(self) -> Dict[str, QgsVectorLayer]:
        return self.layers

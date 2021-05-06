from time import sleep
from urllib.request import urlopen

from qgis._core import QgsTask


class DownloadTask(QgsTask):

    def __init__(self, url: str):
        super().__init__(f'Downloading {url}', QgsTask.CanCancel)
        self.url = url

    def run(self):
        self.setProgress(30)
        sleep(2)
        self.setProgress(70)
        sleep(2)
        self.result = urlopen(self.url).read()

        return True

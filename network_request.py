import json
from typing import Dict, AnyStr, List, Union

from PyQt5.QtCore import QUrl
from PyQt5.QtNetwork import QNetworkRequest, QNetworkReply
from qgis._core import QgsNetworkAccessManager, QgsNetworkReplyContent

from .types import OrkamvApiException, ErrorReason


def check_response(res: QgsNetworkReplyContent) -> None:
    if res.error() == QNetworkReply.NoError:
        return

    if res.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 400:
        res_data = json.loads(res.content().data().decode('utf8'))
        print(f'Status: {res_data.get("status")}, Message:{res_data.get("message")}')
        if 'message' in res_data:
            raise OrkamvApiException(ErrorReason(res_data['message']))
        if 'status' in res_data:
            raise OrkamvApiException(ErrorReason(res_data['status']))

    raise OrkamvApiException(ErrorReason.NETWORK_ERROR, res.errorString())


def post_json(url: str, data: Dict) -> Dict:
    req_data = json.dumps(data).encode('utf8')

    req = QNetworkRequest()
    req.setUrl(QUrl(url))
    req.setHeader(QNetworkRequest.ContentTypeHeader, 'application/json')

    res = QgsNetworkAccessManager.blockingPost(req, data=req_data, forceRefresh=True)
    check_response(res)

    return json.loads(res.content().data().decode('utf8'))


def get_response(url: str) -> QgsNetworkReplyContent:
    req = QNetworkRequest()
    req.setUrl(QUrl(url))

    res = QgsNetworkAccessManager.blockingGet(req, forceRefresh=True)
    check_response(res)

    return res


def get_bytes(url: str) -> AnyStr:
    res = get_response(url)
    return res.content().data()


def get_json(url: str) -> Union[Dict, List]:
    res = get_response(url)
    return json.loads(res.content().data().decode('utf8'))

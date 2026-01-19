import json
from typing import Tuple

from requests.models import Response

from thsr_ticket.remote.http_request import HTTPRequest
from thsr_ticket.view_model.avail_trains import AvailTrains
from thsr_ticket.view.web.show_avail_trains import ShowAvailTrains
from thsr_ticket.configs.web.param_schema import ConfirmTrainModel
from thsr_ticket.controller.captcha_helper import (
    parse_error_feedback,
    is_no_train_error,
)


class ConfirmTrainFlow:
    def __init__(self, client: HTTPRequest, book_resp: Response):
        self.client = client
        self.book_resp = book_resp
        self.show_trains = ShowAvailTrains()

    def run(self) -> Tuple[Response, ConfirmTrainModel]:
        trains = AvailTrains().parse(self.book_resp.content)
        if not trains:
            # 檢查是否有錯誤訊息
            errors = parse_error_feedback(self.book_resp.content)
            if is_no_train_error(errors):
                raise ValueError('查無可售車次或車票已售完，請重新選擇日期或時間。')
            if errors:
                raise ValueError(f'訂票失敗：{"; ".join(errors)}')
            raise ValueError('沒有可用的班次！請確認日期和時間是否正確。')

        selection = self.show_trains.show(trains, select=True, default_value=1)
        selected_train = trains[selection - 1]

        confirm_model = ConfirmTrainModel(
            selected_train=selected_train.form_value,
        )
        json_params = confirm_model.json(by_alias=True)
        dict_params = json.loads(json_params)
        resp = self.client.submit_train(dict_params)
        return resp, confirm_model

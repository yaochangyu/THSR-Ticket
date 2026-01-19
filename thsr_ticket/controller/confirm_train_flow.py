import json
from typing import List, Tuple

from requests.models import Response

from thsr_ticket.remote.http_request import HTTPRequest
from thsr_ticket.view_model.avail_trains import AvailTrains
from thsr_ticket.view.web.show_avail_trains import ShowAvailTrains
from thsr_ticket.configs.web.param_schema import Train, ConfirmTrainModel



class ConfirmTrainFlow:
    def __init__(self, client: HTTPRequest, book_resp: Response):
        self.client = client
        self.book_resp = book_resp
        self.show_trains = ShowAvailTrains()

    def run(self) -> Tuple[Response, ConfirmTrainModel]:
        trains = AvailTrains().parse(self.book_resp.content)
        if not trains:
            raise ValueError('No available trains!')

        selection = self.show_trains.show(trains, select=True, default_value=1)
        selected_train = trains[selection - 1]

        confirm_model = ConfirmTrainModel(
            selected_train=selected_train.form_value,
        )
        json_params = confirm_model.json(by_alias=True)
        dict_params = json.loads(json_params)
        resp = self.client.submit_train(dict_params)
        return resp, confirm_model

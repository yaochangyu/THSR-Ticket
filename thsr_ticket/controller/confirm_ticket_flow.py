import json
from typing import Tuple

from bs4 import BeautifulSoup
from requests.models import Response
from thsr_ticket.configs.web.param_schema import ConfirmTicketModel

from thsr_ticket.model.db import Record
from thsr_ticket.remote.http_request import HTTPRequest
from thsr_ticket.controller.auto_booking_flow import _parse_passenger_id_fields


class ConfirmTicketFlow:
    def __init__(self, client: HTTPRequest, train_resp: Response, record: Record = None):
        self.client = client
        self.train_resp = train_resp
        self.record = record

    def run(self) -> Tuple[Response]:
        page = BeautifulSoup(self.train_resp.content, features='html.parser')
        personal_id = self.set_personal_id()
        ticket_model = ConfirmTicketModel(
            personal_id=personal_id,
            phone_num=self.set_phone_num(),
            member_radio=_parse_member_radio(page),
        )

        json_params = ticket_model.json(by_alias=True)
        dict_params = json.loads(json_params)

        # 解析並填入乘客身分證欄位（愛心票、敬老票等優惠票種）
        passenger_fields = _parse_passenger_id_fields(page)
        if passenger_fields:
            print(f"偵測到 {len(passenger_fields)} 位乘客需要填寫身分證")
            for field_name in passenger_fields:
                dict_params[field_name] = personal_id

        resp = self.client.submit_ticket(dict_params)
        return resp, ticket_model

    def set_personal_id(self) -> str:
        if self.record and (personal_id := self.record.personal_id):
            return personal_id

        return input(f'輸入身分證字號：\n')

    def set_phone_num(self) -> str:
        if self.record and (phone_num := self.record.phone):
            return phone_num

        if phone_num := input('輸入手機號碼（預設：""）：\n'):
            return phone_num
        return ''


def _parse_member_radio(page: BeautifulSoup) -> str:
    candidates = page.find_all(
        'input',
        attrs={
            'name': 'TicketMemberSystemInputPanel:TakerMemberSystemDataView:memberSystemRadioGroup'
        },
    )
    tag = next((cand for cand in candidates if 'checked' in cand.attrs))
    return tag.attrs['value']

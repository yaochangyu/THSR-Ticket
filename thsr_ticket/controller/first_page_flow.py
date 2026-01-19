import json
import time
from typing import Tuple
from datetime import date, timedelta

from bs4 import BeautifulSoup
from requests.models import Response

from thsr_ticket.model.db import Record
from thsr_ticket.remote.http_request import HTTPRequest
from thsr_ticket.configs.web.param_schema import BookingModel
from thsr_ticket.configs.web.parse_html_element import BOOKING_PAGE
from thsr_ticket.configs.web.enums import StationMapping, TicketType
from thsr_ticket.configs.common import (
    AVAILABLE_TIME_TABLE,
    DAYS_BEFORE_BOOKING_AVAILABLE,
    MAX_TICKET_NUM,
)
from thsr_ticket.configs.user_config import STATION_CHINESE_NAME, TICKET_TYPE_NAME_MAP
from thsr_ticket.controller.captcha_helper import (
    MAX_CAPTCHA_RETRY,
    CAPTCHA_RETRY_INTERVAL,
    input_captcha,
    parse_error_feedback,
    is_captcha_error,
    has_train_data,
)


class FirstPageFlow:
    def __init__(self, client: HTTPRequest, record: Record = None) -> None:
        self.client = client
        self.record = record

    def run(self) -> Tuple[Response, BookingModel]:
        # First page. Booking options
        print('請稍等...')
        book_page = self.client.request_booking_page().content
        img_resp = self.client.request_security_code_img(book_page).content
        page = BeautifulSoup(book_page, features='html.parser')

        # 收集用戶輸入的表單資料（驗證碼除外）
        form_data = {
            'start_station': self.select_station('啟程'),
            'dest_station': self.select_station('到達', default_value=StationMapping.Zuouing.value),
            'outbound_date': self.select_date('出發'),
            'outbound_time': self.select_time('啟程'),
            'adult_ticket_num': self.select_ticket_num(TicketType.ADULT, default_ticket_num=0),
            'child_ticket_num': self.select_ticket_num(TicketType.CHILD, default_ticket_num=0),
            'disabled_ticket_num': self.select_ticket_num(TicketType.DISABLED, default_ticket_num=2),
            'elder_ticket_num': self.select_ticket_num(TicketType.ELDER, default_ticket_num=0),
            'college_ticket_num': self.select_ticket_num(TicketType.COLLEGE, default_ticket_num=0),
            'youth_ticket_num': self.select_ticket_num(TicketType.YOUTH, default_ticket_num=1),
            'seat_prefer': _parse_seat_prefer_value(page),
            'types_of_trip': _parse_types_of_trip_value(page),
            'search_by': _parse_search_by(page),
        }

        # 驗證碼重試邏輯
        retry_count = 0
        while True:
            use_manual = retry_count >= MAX_CAPTCHA_RETRY
            security_code = input_captcha(img_resp, force_manual=use_manual)

            book_model = BookingModel(
                **form_data,
                security_code=security_code,
            )
            json_params = book_model.json(by_alias=True)
            dict_params = json.loads(json_params)
            resp = self.client.submit_booking_form(dict_params)

            # 檢查是否成功進入第二頁
            if has_train_data(resp.content):
                return resp, book_model

            # 檢查錯誤訊息
            errors = parse_error_feedback(resp.content)
            if not is_captcha_error(errors):
                # 不是驗證碼錯誤，返回讓上層處理
                return resp, book_model

            retry_count += 1
            if use_manual:
                # 手動輸入也失敗，直接返回讓上層處理
                return resp, book_model

            print(f'驗證碼錯誤，正在重試... ({retry_count}/{MAX_CAPTCHA_RETRY})')
            time.sleep(CAPTCHA_RETRY_INTERVAL)

            # 重新請求頁面和驗證碼
            book_page = self.client.request_booking_page().content
            img_resp = self.client.request_security_code_img(book_page).content
            page = BeautifulSoup(book_page, features='html.parser')
            # 更新頁面相關的值
            form_data['seat_prefer'] = _parse_seat_prefer_value(page)
            form_data['types_of_trip'] = _parse_types_of_trip_value(page)
            form_data['search_by'] = _parse_search_by(page)

    def select_station(self, travel_type: str, default_value: int = StationMapping.Taipei.value) -> int:
        if (
            self.record
            and (
                station := {
                    '啟程': self.record.start_station,
                    '到達': self.record.dest_station,
                }.get(travel_type)
            )
        ):
            return station

        print(f'選擇{travel_type}站：')
        for station in StationMapping:
            chinese_name = STATION_CHINESE_NAME.get(station, station.name)
            print(f'{station.value}. {chinese_name}')

        return int(
            input(f'輸入選擇(預設: {default_value})：')
            or default_value
        )

    def select_date(self, date_type: str) -> str:
        today = date.today()
        last_avail_date = today + timedelta(days=DAYS_BEFORE_BOOKING_AVAILABLE)
        print(f'選擇{date_type}日期（{today}~{last_avail_date}）（預設為今日）：')
        return input() or str(today)

    def select_time(self, time_type: str, default_value: int = 10) -> str:
        if self.record and (
            time_str := {
                '啟程': self.record.outbound_time,
                '回程': None,
            }.get(time_type)
        ):
            return time_str

        print('選擇出發時間：')
        for idx, t_str in enumerate(AVAILABLE_TIME_TABLE):
            t_int = int(t_str[:-1])
            if t_str[-1] == "A" and (t_int // 100) == 12:
                t_int = "{:04d}".format(t_int % 1200)  # type: ignore
            elif t_int != 1230 and t_str[-1] == "P":
                t_int += 1200
            t_str = str(t_int)
            print(f'{idx+1}. {t_str[:-2]}:{t_str[-2:]}')

        selected_opt = int(input(f'輸入選擇（預設：{default_value}）：') or default_value)
        return AVAILABLE_TIME_TABLE[selected_opt-1]

    def select_ticket_num(self, ticket_type: TicketType, default_ticket_num: int = 1) -> str:
        if self.record and (
            ticket_num_str := {
                TicketType.ADULT: self.record.adult_num,
                TicketType.CHILD: self.record.child_num,
                TicketType.DISABLED: self.record.disabled_num,
                TicketType.ELDER: self.record.elder_num,
                TicketType.COLLEGE: self.record.college_num,
                TicketType.YOUTH: self.record.youth_num,
            }.get(ticket_type)
        ):
            return ticket_num_str

        ticket_type_name = TICKET_TYPE_NAME_MAP.get(ticket_type, ticket_type.name)

        print(f'選擇{ticket_type_name}票數（0~{MAX_TICKET_NUM}）（預設：{default_ticket_num}）')
        ticket_num = int(input() or default_ticket_num)
        return f'{ticket_num}{ticket_type.value}'


def _parse_seat_prefer_value(page: BeautifulSoup) -> str:
    options = page.find(**BOOKING_PAGE["seat_prefer_radio"])
    preferred_seat = options.find_next(selected='selected')
    return preferred_seat.attrs['value']


def _parse_types_of_trip_value(page: BeautifulSoup) -> int:
    options = page.find(**BOOKING_PAGE["types_of_trip"])
    tag = options.find_next(selected='selected')
    return int(tag.attrs['value'])


def _parse_search_by(page: BeautifulSoup) -> str:
    candidates = page.find_all('input', {'name': 'bookingMethod'})
    tag = next((cand for cand in candidates if 'checked' in cand.attrs))
    return tag.attrs['value']

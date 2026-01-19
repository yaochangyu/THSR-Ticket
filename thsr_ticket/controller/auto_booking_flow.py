"""自動訂票流程控制器

從 config.json 讀取設定，自動完成訂票流程。
"""
import json
import time
from typing import Tuple

from bs4 import BeautifulSoup
from requests.models import Response

from thsr_ticket.remote.http_request import HTTPRequest
from thsr_ticket.configs.web.param_schema import BookingModel, ConfirmTrainModel, ConfirmTicketModel
from thsr_ticket.configs.web.parse_html_element import BOOKING_PAGE, ERROR_FEEDBACK
from thsr_ticket.configs.user_config import load_config, parse_config
from thsr_ticket.view_model.avail_trains import AvailTrains
from thsr_ticket.view_model.error_feedback import ErrorFeedback
from thsr_ticket.view_model.booking_result import BookingResult
from thsr_ticket.view.web.show_error_msg import ShowErrorMsg
from thsr_ticket.view.web.show_booking_result import ShowBookingResult
from thsr_ticket.view.web.show_avail_trains import ShowAvailTrains
from thsr_ticket.ml.ocr import recognize_captcha


MAX_CAPTCHA_RETRY = 3
CAPTCHA_RETRY_INTERVAL = 1
STEP_DELAY = 0.2  # 每個步驟之間的延遲（秒）


class AutoBookingFlow:
    """自動訂票流程"""

    def __init__(self) -> None:
        self.client = HTTPRequest()
        self.error_feedback = ErrorFeedback()
        self.show_error_msg = ShowErrorMsg()
        self.show_trains = ShowAvailTrains()
        self.config = None

    def run(self) -> Response:
        # 載入設定檔
        raw_config = load_config()
        if not raw_config:
            print("錯誤：找不到 config.json 設定檔")
            print("請複製 config.example.json 為 config.json 並填入設定")
            return None

        try:
            self.config = parse_config(raw_config)
        except ValueError as e:
            print(f"設定檔錯誤：{e}")
            return None

        print("=== 自動訂票模式 ===")
        print(f"出發站：{raw_config['start_station']}")
        print(f"到達站：{raw_config['dest_station']}")
        print(f"出發日期：{raw_config['outbound_date']}")
        print(f"出發時間：{raw_config['outbound_time']}")
        print()
        time.sleep(STEP_DELAY)

        # 第一頁：訂票表單
        book_resp, book_model = self._first_page_flow()
        if book_resp is None:
            return None
        if self._show_error(book_resp.content):
            return book_resp
        time.sleep(STEP_DELAY)

        # 第二頁：班次確認（自動選擇乘車時間最短）
        train_resp, train_model = self._confirm_train_flow(book_resp)
        if self._show_error(train_resp.content):
            return train_resp
        time.sleep(STEP_DELAY)

        # 第三頁：乘客資訊
        ticket_resp, ticket_model = self._confirm_ticket_flow(train_resp)
        if self._show_error(ticket_resp.content):
            return ticket_resp
        time.sleep(STEP_DELAY)

        # 結果頁面
        result_model = BookingResult().parse(ticket_resp.content)
        book = ShowBookingResult()
        book.show(result_model)
        print("\n請使用官方提供的管道完成後續付款以及取票!!")

        return ticket_resp

    def _first_page_flow(self) -> Tuple[Response, BookingModel]:
        """第一頁：訂票表單（自動填入）"""
        print("正在載入訂票頁面...")
        book_page = self.client.request_booking_page().content
        time.sleep(STEP_DELAY)
        img_resp = self.client.request_security_code_img(book_page).content
        time.sleep(STEP_DELAY)
        page = BeautifulSoup(book_page, features="html.parser")

        form_data = {
            "start_station": self.config["start_station"],
            "dest_station": self.config["dest_station"],
            "outbound_date": self.config["outbound_date"],
            "outbound_time": self.config["outbound_time"],
            "adult_ticket_num": self.config["adult_ticket_num"],
            "child_ticket_num": self.config["child_ticket_num"],
            "disabled_ticket_num": self.config["disabled_ticket_num"],
            "elder_ticket_num": self.config["elder_ticket_num"],
            "college_ticket_num": self.config["college_ticket_num"],
            "youth_ticket_num": self.config["youth_ticket_num"],
            "seat_prefer": _parse_seat_prefer_value(page),
            "types_of_trip": _parse_types_of_trip_value(page),
            "search_by": _parse_search_by(page),
        }

        # 驗證碼重試邏輯
        retry_count = 0
        while True:
            use_manual = retry_count >= MAX_CAPTCHA_RETRY
            security_code = _auto_input_security_code(img_resp, force_manual=use_manual)

            book_model = BookingModel(
                **form_data,
                security_code=security_code,
            )
            json_params = book_model.json(by_alias=True)
            dict_params = json.loads(json_params)
            print("正在提交訂票表單...")
            time.sleep(STEP_DELAY)
            resp = self.client.submit_booking_form(dict_params)

            # 檢查是否有驗證碼錯誤
            errors = _parse_error_feedback(resp.content)
            captcha_error = any("檢測碼" in err or "驗證碼" in err for err in errors)

            if not captcha_error:
                return resp, book_model

            retry_count += 1
            if use_manual:
                return resp, book_model

            print(f"驗證碼錯誤，正在重試... ({retry_count}/{MAX_CAPTCHA_RETRY})")
            time.sleep(CAPTCHA_RETRY_INTERVAL)

            book_page = self.client.request_booking_page().content
            img_resp = self.client.request_security_code_img(book_page).content
            page = BeautifulSoup(book_page, features="html.parser")
            form_data["seat_prefer"] = _parse_seat_prefer_value(page)
            form_data["types_of_trip"] = _parse_types_of_trip_value(page)
            form_data["search_by"] = _parse_search_by(page)

    def _confirm_train_flow(self, book_resp: Response) -> Tuple[Response, ConfirmTrainModel]:
        """第二頁：班次確認（自動選擇乘車時間最短）"""
        avail_trains = AvailTrains()
        trains = avail_trains.parse(book_resp.content)

        if not trains:
            raise ValueError("沒有可用的班次！")

        # 顯示所有可用班次（不需要使用者選擇）
        print("\n可用班次：")
        self.show_trains.show(trains, select=False)

        # 自動選擇乘車時間最短的班次
        selected_train = avail_trains.select_shortest_travel_time()
        print(f"\n自動選擇乘車時間最短的班次：{selected_train.id} ({selected_train.travel_time})")

        confirm_model = ConfirmTrainModel(selected_train=selected_train.form_value)
        json_params = confirm_model.json(by_alias=True)
        dict_params = json.loads(json_params)
        print("正在提交班次選擇...")
        time.sleep(STEP_DELAY)
        resp = self.client.submit_train(dict_params)
        return resp, confirm_model

    def _confirm_ticket_flow(self, train_resp: Response) -> Tuple[Response, ConfirmTicketModel]:
        """第三頁：乘客資訊（自動填入）"""
        page = BeautifulSoup(train_resp.content, features="html.parser")

        ticket_model = ConfirmTicketModel(
            personal_id=self.config["personal_id"],
            phone_num=self.config.get("phone", ""),
            member_radio=_parse_member_radio(page),
            email=self.config.get("email", ""),
        )

        json_params = ticket_model.json(by_alias=True)
        dict_params = json.loads(json_params)
        print("正在提交乘客資訊...")
        time.sleep(STEP_DELAY)
        resp = self.client.submit_ticket(dict_params)
        return resp, ticket_model

    def _show_error(self, html: bytes) -> bool:
        """顯示錯誤訊息"""
        errors = self.error_feedback.parse(html)
        if len(errors) == 0:
            return False
        self.show_error_msg.show(errors)
        return True


def _parse_seat_prefer_value(page: BeautifulSoup) -> str:
    options = page.find(**BOOKING_PAGE["seat_prefer_radio"])
    preferred_seat = options.find_next(selected="selected")
    return preferred_seat.attrs["value"]


def _parse_types_of_trip_value(page: BeautifulSoup) -> int:
    options = page.find(**BOOKING_PAGE["types_of_trip"])
    tag = options.find_next(selected="selected")
    return int(tag.attrs["value"])


def _parse_search_by(page: BeautifulSoup) -> str:
    candidates = page.find_all("input", {"name": "bookingMethod"})
    tag = next((cand for cand in candidates if "checked" in cand.attrs))
    return tag.attrs["value"]


def _parse_error_feedback(html: bytes) -> list:
    """解析頁面中的錯誤訊息"""
    page = BeautifulSoup(html, features="html.parser")
    error_elements = page.find_all(**ERROR_FEEDBACK)
    return [elem.get_text(strip=True) for elem in error_elements]


def _parse_member_radio(page: BeautifulSoup) -> str:
    candidates = page.find_all(
        "input",
        attrs={
            "name": "TicketMemberSystemInputPanel:TakerMemberSystemDataView:memberSystemRadioGroup"
        },
    )
    tag = next((cand for cand in candidates if "checked" in cand.attrs))
    return tag.attrs["value"]


def _auto_input_security_code(img_resp: bytes, force_manual: bool = False) -> str:
    """自動輸入驗證碼

    Args:
        img_resp: 驗證碼圖片的 bytes 資料
        force_manual: 是否強制手動輸入
    """
    import io
    from PIL import Image

    ocr_result = recognize_captcha(img_resp)

    if not force_manual and ocr_result:
        print(f"驗證碼自動識別: {ocr_result}")
        return ocr_result

    # 手動輸入模式
    image = Image.open(io.BytesIO(img_resp))
    image.show()

    if ocr_result:
        print(f"驗證碼識別結果: {ocr_result}")
        user_input = input("按 Enter 確認，或輸入正確的驗證碼：")
        return user_input if user_input else ocr_result
    else:
        print("OCR 識別失敗，請手動輸入驗證碼：")
        return input()

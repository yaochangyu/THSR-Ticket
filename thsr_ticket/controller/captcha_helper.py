"""驗證碼處理共用模組"""
import io
import time
from typing import Callable, List

from PIL import Image
from bs4 import BeautifulSoup

from thsr_ticket.ml.ocr import recognize_captcha
from thsr_ticket.configs.web.parse_html_element import ERROR_FEEDBACK

MAX_CAPTCHA_RETRY = 3
CAPTCHA_RETRY_INTERVAL = 1  # 秒


def parse_error_feedback(html: bytes) -> List[str]:
    """解析頁面中的錯誤訊息"""
    page = BeautifulSoup(html, features='html.parser')
    error_elements = page.find_all(**ERROR_FEEDBACK)
    return [elem.get_text(strip=True) for elem in error_elements]


def is_captcha_error(errors: List[str]) -> bool:
    """判斷是否為驗證碼相關錯誤"""
    return any('檢測碼' in err or '驗證碼' in err for err in errors)


def is_no_train_error(errors: List[str]) -> bool:
    """判斷是否為無可售車次錯誤"""
    return any('查無可售車次' in err or '車票已售完' in err for err in errors)


def has_train_data(html: bytes) -> bool:
    """檢查是否有班次資料（表示成功進入第二頁）"""
    return b'TrainQueryDataViewPanel' in html


def input_captcha(img_resp: bytes, force_manual: bool = False) -> str:
    """輸入驗證碼，支援 OCR 自動識別

    Args:
        img_resp: 驗證碼圖片的 bytes 資料
        force_manual: 是否強制手動輸入（OCR 重試次數用盡後使用）

    Returns:
        驗證碼字串
    """
    ocr_result = recognize_captcha(img_resp)

    # 自動模式：OCR 成功則直接使用
    if not force_manual and ocr_result:
        print(f'驗證碼自動識別: {ocr_result}')
        return ocr_result

    # 手動輸入模式：顯示圖片讓用戶輸入
    image = Image.open(io.BytesIO(img_resp))
    image.show()

    if ocr_result:
        print(f'驗證碼識別結果: {ocr_result}')
        user_input = input('按 Enter 確認，或輸入正確的驗證碼：')
        return user_input if user_input else ocr_result
    else:
        print('OCR 識別失敗，請手動輸入驗證碼：')
        return input()

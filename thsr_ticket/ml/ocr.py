"""驗證碼 OCR 識別模組"""
from typing import Optional

# 高鐵驗證碼可用字元（排除容易混淆的 0, 1, I, O）
CAPTCHA_CHARS = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


class CaptchaOCR:
    """驗證碼 OCR 識別器

    使用 ddddocr 進行驗證碼識別，採用延遲載入以避免啟動時的效能影響。
    """

    _instance: Optional['CaptchaOCR'] = None
    _ocr = None

    def __new__(cls) -> 'CaptchaOCR':
        """單例模式，避免重複初始化 OCR 引擎"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_ocr(self):
        """延遲載入 OCR 引擎"""
        if self._ocr is None:
            try:
                import ddddocr
                self._ocr = ddddocr.DdddOcr(show_ad=False)
                self._ocr.set_ranges(CAPTCHA_CHARS)
            except ImportError:
                print("警告: ddddocr 未安裝，OCR 功能將無法使用")
                print("請執行: pip install ddddocr")
                self._ocr = None
        return self._ocr

    def recognize(self, image_bytes: bytes) -> str:
        """識別驗證碼圖片

        Args:
            image_bytes: 圖片的 bytes 資料

        Returns:
            識別結果字串，若識別失敗則返回空字串
        """
        ocr = self._get_ocr()
        if ocr is None:
            return ""
        try:
            result = ocr.classification(image_bytes)
            return result.upper() if result else ""
        except Exception as e:
            print(f"OCR 識別失敗: {e}")
            return ""


def recognize_captcha(image_bytes: bytes) -> str:
    """便捷函數：識別驗證碼

    Args:
        image_bytes: 圖片的 bytes 資料

    Returns:
        識別結果字串
    """
    return CaptchaOCR().recognize(image_bytes)

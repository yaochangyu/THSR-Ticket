# OCR 驗證碼識別功能實作計畫

## 目標
修改 `first_page_flow.py` 中的 `_input_security_code` 函數，使用 ddddocr 自動識別驗證碼，並預填結果讓用戶確認或修改。

---

## 實作步驟

- [x] 步驟 1：新增依賴
  - 原因：引入 ddddocr OCR 套件
  - 檔案：`requirements.txt`
  - 內容：新增 `ddddocr>=1.4.0`

- [x] 步驟 2：建立 ML 套件初始化檔案
  - 原因：讓 `ml/` 目錄成為 Python 套件，方便 import
  - 檔案：`thsr_ticket/ml/__init__.py`

- [x] 步驟 3：建立 OCR 模組
  - 原因：封裝 OCR 識別邏輯，符合單一職責原則
  - 檔案：`thsr_ticket/ml/ocr.py`
  - 依賴：步驟 1、步驟 2
  - 設計要點：
    - 單例模式避免重複載入模型
    - 延遲載入優化啟動速度
    - 設定字元範圍 `23456789ABCDEFGHJKLMNPQRSTUVWXYZ`（與 `generate_captcha.py` 一致）
    - 錯誤處理：識別失敗返回空字串

- [x] 步驟 4：修改驗證碼輸入函數
  - 原因：整合 OCR 功能到現有流程
  - 檔案：`thsr_ticket/controller/first_page_flow.py`
  - 依賴：步驟 3
  - 修改內容：
    1. 新增 import `from thsr_ticket.ml.ocr import recognize_captcha`
    2. 修改 `_input_security_code` 函數：
       - 呼叫 OCR 識別驗證碼
       - 顯示驗證碼圖片
       - 若識別成功：顯示結果，用戶按 Enter 確認或輸入正確值覆蓋
       - 若識別失敗：退回手動輸入模式

---

## 關鍵檔案

| 檔案 | 動作 |
|------|------|
| `requirements.txt` | 修改：新增 ddddocr 依賴 |
| `thsr_ticket/ml/__init__.py` | 新增：套件初始化 |
| `thsr_ticket/ml/ocr.py` | 新增：OCR 模組 |
| `thsr_ticket/controller/first_page_flow.py` | 修改：`_input_security_code` 函數 |

---

## 驗證方式

1. 安裝依賴：`pip install -r requirements.txt`
2. 執行程式：`python -m thsr_ticket.main`
3. 觀察驗證碼輸入步驟：
   - 應顯示 OCR 識別結果
   - 按 Enter 應使用識別結果
   - 輸入其他值應覆蓋識別結果

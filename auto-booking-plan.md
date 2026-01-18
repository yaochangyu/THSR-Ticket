# 自動訂票流程實作計畫

## 需求摘要

在 main.py 執行時，讓用戶選擇自動流程或手動流程：
- **手動流程**：現有功能，逐步輸入參數
- **自動流程**：從 config.json 讀取設定，自動填入表單

## config.json 結構設計

```json
{
  "start_station": "台北",
  "dest_station": "台中",
  "outbound_date": "2025/01/25",
  "outbound_time": "06:00",
  "personal_id": "A123456789",
  "email": "example@email.com",
  "phone": "0912345678",
  "tgo_account": "",
  "tickets": {
    "adult": 1,
    "child": 0,
    "disabled": 0,
    "elder": 0,
    "college": 0,
    "youth": 0
  }
}
```

## 自動流程邏輯

1. 讀取 config.json
2. 轉換時間格式（24小時制 → 系統格式如 "600A"）
3. 自動填入訂票表單
4. 驗證碼使用現有 OCR 自動辨識
5. **班次選擇：自動選擇乘車時間最短的班次**
6. 自動填入乘客資訊
7. 顯示訂票結果

---

## 實作步驟

- [x] 步驟 1：設定檔基礎建設
  - 建立 `config.example.json` 範例檔案
  - 更新 `.gitignore` 排除 `config.json`
  - 檔案：`config.example.json`, `.gitignore`

- [x] 步驟 2：建立設定檔讀取模組
  - 建立 `thsr_ticket/configs/user_config.py`
  - 實作 `load_config()` 函數讀取 config.json
  - 實作站名與車站代碼的對應轉換
  - 實作 24 小時制轉系統時間格式
  - 檔案：`thsr_ticket/configs/user_config.py`
  - 依賴：步驟 1

- [x] 步驟 3：建立自動班次選擇邏輯
  - 在 `view_model/avail_trains.py` 新增方法
  - 實作「選擇乘車時間最短」的邏輯
  - 檔案：`thsr_ticket/view_model/avail_trains.py`

- [x] 步驟 4：建立自動訂票流程控制器
  - 建立 `thsr_ticket/controller/auto_booking_flow.py`
  - 繼承或參考 BookingFlow 的結構
  - 整合設定檔讀取與自動班次選擇
  - 檔案：`thsr_ticket/controller/auto_booking_flow.py`
  - 依賴：步驟 2, 步驟 3

- [x] 步驟 5：修改程式進入點
  - 修改 `main.py` 加入流程選擇選單
  - 根據用戶選擇執行對應流程
  - 檔案：`thsr_ticket/main.py`
  - 依賴：步驟 4

- [x] 步驟 6：更新文件
  - 更新 `README.md` 說明自動流程使用方式
  - 檔案：`README.md`
  - 依賴：步驟 5

---

## 車站名稱對照表

| 名稱 | 代碼 |
|------|------|
| 南港 | 1 |
| 台北 | 2 |
| 板橋 | 3 |
| 桃園 | 4 |
| 新竹 | 5 |
| 苗栗 | 6 |
| 台中 | 7 |
| 彰化 | 8 |
| 雲林 | 9 |
| 嘉義 | 10 |
| 台南 | 11 |
| 左營 | 12 |

## 時間格式對照範例

| 24小時制 | 系統格式 |
|----------|----------|
| 06:00 | 600A |
| 12:00 | 1200N |
| 13:30 | 130P |
| 00:01 | 1201A |

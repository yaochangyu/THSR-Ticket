# 高鐵訂票專案 - 架構文件

## 專案結構

```
THSR-Ticket/
├── 🔧 配置層 (configs/)
│   ├── common.py                    # 全局常數 (時間表, 預訂天數等)
│   └── web/
│       ├── http_config.py           # 高鐵網站 URL 和 Headers
│       ├── enums.py                 # 車站、票種映射
│       ├── param_schema.py          # Pydantic 參數模型與驗證
│       ├── parse_html_element.py    # HTML 元素選擇器配置
│       └── parse_avail_train.py     # 班次解析規則
│
├── 📡 遠程通訊層 (remote/)
│   └── http_request.py              # HTTP 客戶端 (會話管理、Cookie)
│
├── 🎮 控制層 (controller/)
│   ├── booking_flow.py              # 主控制流程協調
│   ├── first_page_flow.py           # 訂票表單 + OCR 驗證碼
│   ├── confirm_train_flow.py        # 班次選擇
│   └── confirm_ticket_flow.py       # 乘客資訊輸入
│
├── 🧠 機器學習層 (ml/)
│   ├── ocr.py                       # 驗證碼 OCR 識別 (ddddocr)
│   ├── image_process.py             # 圖像前處理
│   └── generate_captcha.py          # 驗證碼生成 (測試用)
│
├── 📊 數據層 (model/)
│   ├── db.py                        # 本地 TinyDB 歷史記錄存儲
│   ├── json/                        # REST API 模型
│   └── web/                         # 網頁爬取相關模型
│
├── 👁 視圖層 (view/ & view_model/)
│   ├── view/common.py               # 共通顯示功能 (歷史記錄展示)
│   ├── view/web/                    # CLI 輸出格式化
│   └── view_model/
│       ├── avail_trains.py          # 班次解析與展示
│       ├── booking_result.py        # 訂票結果解析
│       └── error_feedback.py        # 錯誤訊息解析
│
├── 🧪 測試層 (unittest/)
│   └── test_http_request.py
│
├── 📄 文件
│   ├── main.py                      # 程式入口
│   ├── requirements.txt             # 依賴清單
│   ├── setup.py                     # Python 套件配置
│   └── README.md                    # 專案說明
│
└── 💾 資料儲存
    └── .db/
        └── history.json             # 本地訂票歷史記錄 (TinyDB)
```

---

## 主程式流程

```
main.py
  └── BookingFlow.run()
        │
        ├── show_history()
        │   └── 從本地資料庫載入歷史紀錄，允許用戶快速選擇
        │
        ├── FirstPageFlow.run() 【第一頁：訂票表單】
        │   ├── 請求訂票頁面
        │   ├── 請求驗證碼圖片
        │   ├── 收集表單數據：
        │   │   ├── 出發站、到達站
        │   │   ├── 出發日期、出發時間
        │   │   ├── 各類別票數（成人、孩童、愛心、敬老、大學生、青年）
        │   │   ├── 座位偏好、行程類型、搜尋方式
        │   │   └── 驗證碼（支援 OCR 自動辨識 + 手動重試）
        │   └── 遞交訂票表單
        │
        ├── ConfirmTrainFlow.run() 【第二頁：班次確認】
        │   ├── 解析可用班次
        │   ├── 顯示班次資訊（班次號、出發時間、到達時間、旅程時間、優惠資訊）
        │   ├── 用戶選擇班次
        │   └── 遞交班次選擇
        │
        ├── ConfirmTicketFlow.run() 【第三頁：乘客資訊確認】
        │   ├── 輸入身分證字號（支援歷史記錄）
        │   ├── 輸入手機號碼（支援歷史記錄）
        │   ├── 選擇會員身分
        │   └── 遞交乘客資訊
        │
        ├── BookingResult.parse() 【結果頁面】
        │   ├── 解析預訂確認
        │   └── 顯示 PNR 碼、付款期限、座位資訊等
        │
        └── 儲存成功的訂單至歷史紀錄
```

---

## 數據流向

```
用戶輸入
  ├── 站點選擇 (1-12)
  ├── 日期選擇 (YYYY-MM-DD)
  ├── 時間選擇 (時間表)
  ├── 票種數量 (1F, 0H, 0W...)
  └── 驗證碼 (OCR 辨識 → 手動確認)
        ↓
  BookingModel (Pydantic 驗證)
        ↓
  HTTP POST 到高鐵網站
        ↓
  HTML 響應
        ↓
  BeautifulSoup 解析
        ├── AvailTrains (班次清單)
        ├── ErrorFeedback (錯誤訊息)
        └── BookingResult (成功結果)
        ↓
  CLI 顯示
        ↓
  ParamDB 儲存歷史紀錄
```

---

## 配置說明

### 全局常數 (configs/common.py)

```python
DAYS_BEFORE_BOOKING_AVAILABLE = 27  # 提前 27 天可訂票
MAX_TICKET_NUM = 10                  # 最多購買 10 張

AVAILABLE_TIME_TABLE = [             # 可選出發時間（共 41 個）
    '1201A', '1230A', '600A', '630A', '700A', ...
]
```

### 車站映射 (configs/web/enums.py)

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

### 票種映射

| 票種 | 代碼 | 說明 |
|------|------|------|
| 成人 | F | 一般成人 |
| 孩童 | H | 6-11 歲 |
| 愛心 | W | 身障人士 |
| 敬老 | E | 65 歲以上 |
| 大學生 | P | 在學學生 |
| 青年 | T | 12-25 歲 |

---

## 參數模型 (configs/web/param_schema.py)

### BookingModel - 訂票表單

| 參數 | 類型 | 說明 |
|------|------|------|
| start_station | int (1-12) | 出發站代碼 |
| dest_station | int (1-12) | 到達站代碼 |
| outbound_date | str | 出發日期 (yyyy/mm/dd) |
| outbound_time | str | 出發時間 (如 '600A') |
| security_code | str | 驗證碼 |
| adult_ticket_num | str | 成人票數 (如 '2F') |
| child_ticket_num | str | 孩童票數 (如 '0H') |
| disabled_ticket_num | str | 愛心票數 (如 '0W') |
| elder_ticket_num | str | 敬老票數 (如 '0E') |
| college_ticket_num | str | 大學生票數 (如 '0P') |
| youth_ticket_num | str | 青年票數 (如 '1T') |
| seat_prefer | str | 座位偏好 |
| types_of_trip | int | 行程類型 (0=單程, 1=來回) |
| search_by | str | 搜尋方式 (radio0/radio1) |

### ConfirmTicketModel - 乘客資訊

| 參數 | 類型 | 必填 |
|------|------|------|
| personal_id | str | 是 |
| phone_num | str | 否 |
| member_radio | str | 是 |
| id_input_radio | int | 是 (0=身分證, 1=護照) |
| email | str | 否 |

---

## OCR 驗證碼識別流程

```
_input_security_code(img_resp, force_manual=False)
├── 第 1-3 次嘗試：
│   ├── recognize_captcha(img_resp)  # OCR 自動識別
│   ├── 成功 → 返回結果
│   └── 失敗 → 重新請求驗證碼
│
└── 第 4 次嘗試：
    ├── 強制手動模式
    ├── image.show()  # 顯示驗證碼圖片
    ├── 顯示 OCR 建議結果
    └── 接收用戶手動輸入
```

---

## 主要依賴

| 套件 | 版本 | 用途 |
|------|------|------|
| requests | ≥2.21 | HTTP 通訊 |
| beautifulsoup4 | ≥4.8.2 | HTML 解析 |
| pydantic | <2.0 | 參數驗證 |
| tinydb | ≥3.15.2 | 本地資料庫 |
| pillow | ≥7.0 | 圖像處理 |
| ddddocr | ≥1.4.0 | OCR 驗證碼識別 |

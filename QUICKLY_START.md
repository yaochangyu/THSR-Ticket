# 快速開始

## 環境需求

- Python 3.8+

## 安裝步驟

### 1. 建立虛擬環境

```bash
python3 -m venv .venv
```

### 2. 啟用虛擬環境

Linux / macOS:
```bash
source .venv/bin/activate
```

Windows:
```bash
.venv\Scripts\activate
```

### 3. 安裝依賴套件

```bash
pip install -r requirements.txt
```

## 執行程式

```bash
python thsr_ticket/main.py
```

或直接使用虛擬環境執行（無需先啟用）：

```bash
# Linux / macOS
.venv/bin/python thsr_ticket/main.py

# Windows
.venv\Scripts\python thsr_ticket/main.py
```

## 使用說明

程式會以互動方式提示你輸入：
- 啟程站 / 到達站
- 搭乘日期 / 時間
- 乘客數量
- 其他訂票資訊

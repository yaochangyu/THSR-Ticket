"""用戶設定檔讀取模組"""
import json
import os
from typing import Optional

from .common import AVAILABLE_TIME_TABLE
from .web.enums import StationMapping, TicketType


# 車站中文名稱對照表（用於顯示）
STATION_CHINESE_NAME = {
    StationMapping.Nangang: "南港",
    StationMapping.Taipei: "台北",
    StationMapping.Banqiao: "板橋",
    StationMapping.Taoyuan: "桃園",
    StationMapping.Hsinchu: "新竹",
    StationMapping.Miaoli: "苗栗",
    StationMapping.Taichung: "台中",
    StationMapping.Changhua: "彰化",
    StationMapping.Yunlin: "雲林",
    StationMapping.Chiayi: "嘉義",
    StationMapping.Tainan: "台南",
    StationMapping.Zuouing: "左營",
}

# 票種中文名稱對照表
TICKET_TYPE_NAME_MAP = {
    TicketType.ADULT: "成人",
    TicketType.CHILD: "孩童",
    TicketType.DISABLED: "愛心",
    TicketType.ELDER: "敬老",
    TicketType.COLLEGE: "大學生",
    TicketType.YOUTH: "少年",
}


def get_config_path() -> str:
    """取得 config.json 的路徑"""
    # 專案根目錄
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, "config.json")


def load_config() -> Optional[dict]:
    """讀取 config.json 設定檔

    Returns:
        dict: 設定檔內容，若檔案不存在則回傳 None
    """
    config_path = get_config_path()
    if not os.path.exists(config_path):
        return None

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def station_name_to_code(name: str) -> int:
    """將車站名稱轉換為車站代碼

    Args:
        name: 車站中文名稱（如 "台北"）或英文名稱（如 "Taipei"）

    Returns:
        int: 車站代碼（1-12）

    Raises:
        ValueError: 若車站名稱無效
    """
    # 嘗試用中文名稱查詢（從 STATION_CHINESE_NAME 反向查詢）
    for station, chinese_name in STATION_CHINESE_NAME.items():
        if name == chinese_name:
            return station.value

    # 嘗試用英文名稱查詢 StationMapping enum
    try:
        return StationMapping[name].value
    except KeyError:
        pass

    # 嘗試直接用數字
    try:
        code = int(name)
        if 1 <= code <= 12:
            return code
    except ValueError:
        pass

    valid_names = ", ".join(STATION_CHINESE_NAME.values())
    raise ValueError(f"無效的車站名稱: {name}。有效選項: {valid_names}")


def time_to_system_format(time_str: str) -> str:
    """將 24 小時制時間轉換為系統時間格式

    Args:
        time_str: 24 小時制時間（如 "06:00", "13:30"）

    Returns:
        str: 系統時間格式（如 "600A", "130P"）

    Raises:
        ValueError: 若時間格式無效或不在可用時間表中
    """
    # 解析時間
    parts = time_str.split(":")
    if len(parts) != 2:
        raise ValueError(f"無效的時間格式: {time_str}，請使用 HH:MM 格式")

    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        raise ValueError(f"無效的時間格式: {time_str}")

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"無效的時間: {time_str}")

    # 轉換為系統格式
    if hour == 0:
        # 00:xx -> 12xxA
        system_time = f"12{minute:02d}A" if minute > 0 else "1200A"
        # 特殊處理: 00:01 -> 1201A, 00:30 -> 1230A
        system_time = f"12{minute:02d}A"
    elif hour < 12:
        # 01:00-11:59 -> 時分A
        system_time = f"{hour}{minute:02d}A" if minute > 0 else f"{hour}00A"
    elif hour == 12:
        if minute == 0:
            system_time = "1200N"
        else:
            system_time = f"12{minute:02d}P"
    else:
        # 13:00-23:59 -> (時-12)分P
        h = hour - 12
        system_time = f"{h}{minute:02d}P" if minute > 0 else f"{h}00P"

    # 驗證是否在可用時間表中
    if system_time not in AVAILABLE_TIME_TABLE:
        # 嘗試找最接近的時間
        available_times = ", ".join(_format_available_times())
        raise ValueError(f"時間 {time_str} 不在可用時間表中。可用時間: {available_times}")

    return system_time


def _format_available_times() -> list:
    """將系統時間格式轉回 24 小時制顯示"""
    result = []
    for t in AVAILABLE_TIME_TABLE:
        result.append(system_format_to_time(t))
    return result


def system_format_to_time(system_time: str) -> str:
    """將系統時間格式轉換為 24 小時制

    Args:
        system_time: 系統時間格式（如 "600A", "130P"）

    Returns:
        str: 24 小時制時間（如 "06:00", "13:30"）
    """
    suffix = system_time[-1]
    time_part = system_time[:-1]

    if len(time_part) == 3:
        hour = int(time_part[0])
        minute = int(time_part[1:])
    else:
        hour = int(time_part[:2])
        minute = int(time_part[2:])

    if suffix == "A":
        if hour == 12:
            hour = 0
    elif suffix == "N":
        hour = 12
    elif suffix == "P":
        if hour != 12:
            hour += 12

    return f"{hour:02d}:{minute:02d}"


def format_ticket_num(count: int, ticket_type: TicketType) -> str:
    """格式化票數

    Args:
        count: 票數
        ticket_type: 票種

    Returns:
        str: 格式化的票數字串（如 "1F", "0H"）
    """
    return f"{count}{ticket_type.value}"


def parse_config(config: dict) -> dict:
    """解析並驗證設定檔內容

    Args:
        config: 原始設定檔內容

    Returns:
        dict: 解析後的設定，包含轉換後的車站代碼和時間格式
    """
    tickets = config.get("tickets", {})

    return {
        "start_station": station_name_to_code(config["start_station"]),
        "dest_station": station_name_to_code(config["dest_station"]),
        "outbound_date": config["outbound_date"],
        "outbound_time": time_to_system_format(config["outbound_time"]),
        "personal_id": config["personal_id"],
        "email": config.get("email", ""),
        "phone": config.get("phone", ""),
        "tgo_account": config.get("tgo_account", ""),
        "adult_ticket_num": format_ticket_num(tickets.get("adult", 1), TicketType.ADULT),
        "child_ticket_num": format_ticket_num(tickets.get("child", 0), TicketType.CHILD),
        "disabled_ticket_num": format_ticket_num(tickets.get("disabled", 0), TicketType.DISABLED),
        "elder_ticket_num": format_ticket_num(tickets.get("elder", 0), TicketType.ELDER),
        "college_ticket_num": format_ticket_num(tickets.get("college", 0), TicketType.COLLEGE),
        "youth_ticket_num": format_ticket_num(tickets.get("youth", 0), TicketType.YOUTH),
    }

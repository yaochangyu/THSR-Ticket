import sys
sys.path.append("./")

from thsr_ticket.controller.booking_flow import BookingFlow
from thsr_ticket.controller.auto_booking_flow import AutoBookingFlow


def main():
    print("=== 高鐵訂票小幫手 ===")
    print("1. 自動訂票（使用 config.json 設定）")
    print("2. 手動訂票")
    print()

    choice = input("請選擇模式 (預設: 1): ") or "1"

    if choice == "1":
        flow = AutoBookingFlow()
    else:
        flow = BookingFlow()

    flow.run()


if __name__ == "__main__":
    main()

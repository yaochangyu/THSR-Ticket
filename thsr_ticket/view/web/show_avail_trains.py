from typing import List, Optional

from thsr_ticket.view.web.abstract_show import AbstractShow
from thsr_ticket.configs.web.param_schema import Train


class ShowAvailTrains(AbstractShow):
    def show(self, trains: List[Train], select: bool = True, default_value: int = 1) -> Optional[int]:
        """顯示可用班次列表

        Args:
            trains: 班次列表
            select: 是否要求使用者選擇
            default_value: 預設選擇的班次序號

        Returns:
            使用者選擇的班次序號（1-based），若 select=False 則回傳 None
        """
        if len(trains) == 0:
            print("沒有可用的班次！")
            return None

        for idx, train in enumerate(trains, 1):
            print(
                f'{idx}. {train.id:>4} {train.depart}~{train.arrive} '
                f'({train.travel_time}) {train.discount_str}'
            )

        if select:
            return int(input(f'輸入選擇（預設：{default_value}）：') or default_value)
        return None

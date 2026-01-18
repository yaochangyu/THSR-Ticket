from typing import List, Mapping, Optional
from bs4.element import Tag

from thsr_ticket.view_model.abstract_view_model import AbstractViewModel
from thsr_ticket.configs.web.parse_avail_train import ParseAvailTrain
from thsr_ticket.configs.web.param_schema import Train


def _parse_travel_time_minutes(travel_time: str) -> int:
    """將旅程時間字串轉換為分鐘數

    Args:
        travel_time: 旅程時間字串（如 "01:30" 或 "00:45"）

    Returns:
        int: 總分鐘數
    """
    parts = travel_time.split(":")
    if len(parts) == 2:
        hours = int(parts[0])
        minutes = int(parts[1])
        return hours * 60 + minutes
    return 9999  # 無法解析時回傳大數值



class AvailTrains(AbstractViewModel):
    def __init__(self) -> None:
        super(AvailTrains, self).__init__()
        self.avail_trains: List[Train] = []
        self.cond = ParseAvailTrain()

    def parse(self, html: bytes) -> List[Train]:
        page = self._parser(html)
        avail = page.find_all('label', **self.cond.from_html)
        return self._parse_train(avail)

    def _parse_train(self, avail: List[Tag]) -> List[Train]:
        for item in avail:
            train_id = int(item.find(**self.cond.train_id).text)
            depart_time = item.find(**self.cond.depart).text
            arrival_time = item.find(**self.cond.arrival).text
            travel_time = item.find(**self.cond.duration).find_next(
                'span', {'class': 'material-icons'}
            ).fetchNextSiblings()[0].text
            discount_str = self._parse_discount(item)
            form_value = item.find(**self.cond.form_value).attrs['value']
            self.avail_trains.append(
                Train(
                    id=train_id,
                    depart=depart_time,
                    arrive=arrival_time,
                    travel_time=travel_time,
                    discount_str=discount_str,
                    form_value=form_value,
                )
            )
        return self.avail_trains

    def _parse_discount(self, item: Tag) -> str:
        discounts = []
        if tag := item.find(**self.cond.early_bird_discount):
            discounts.append(tag.find_next().text)
        if tag := item.find(**self.cond.college_student_discount):
            discounts.append(tag.find_next().text)
        if discounts:
            joined_str = ', '.join(discounts)
            return f'({joined_str})'
        return ''

    def select_shortest_travel_time(self) -> Optional[Train]:
        """選擇乘車時間最短的班次

        Returns:
            Train: 乘車時間最短的班次，若無可用班次則回傳 None
        """
        if not self.avail_trains:
            return None

        return min(
            self.avail_trains,
            key=lambda t: _parse_travel_time_minutes(t.travel_time)
        )

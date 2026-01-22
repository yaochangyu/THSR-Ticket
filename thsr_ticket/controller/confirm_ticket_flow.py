import json
from typing import Tuple

from bs4 import BeautifulSoup
from requests.models import Response
from thsr_ticket.configs.web.param_schema import ConfirmTicketModel

from thsr_ticket.model.db import Record
from thsr_ticket.remote.http_request import HTTPRequest
from thsr_ticket.controller.auto_booking_flow import _parse_passenger_id_fields


def _validate_id_format(id_number: str) -> bool:
    """驗證身分證字號格式
    
    Args:
        id_number: 身分證字號
        
    Returns:
        是否為有效格式
    """
    if not id_number:
        return False
    if len(id_number) != 10:
        return False
    return True


def _prompt_passenger_ids(passenger_info_list: list, predefined_ids: list = None) -> dict:
    """詢問每位乘客的身分證字號
    
    Args:
        passenger_info_list: 乘客資訊列表，每個元素包含 field_name, passenger_number, ticket_type
        predefined_ids: 預先設定的身分證字號列表（可選）
        
    Returns:
        {欄位名稱: 身分證字號} 的字典
    """
    if not passenger_info_list:
        return {}
    
    print(f"\n偵測到 {len(passenger_info_list)} 位乘客需要填寫身分證")
    print("=" * 50)
    
    passenger_id_map = {}
    predefined_ids = predefined_ids or []
    
    for idx, passenger_info in enumerate(passenger_info_list):
        passenger_num = passenger_info['passenger_number']
        ticket_type = passenger_info['ticket_type']
        field_name = passenger_info['field_name']
        
        # 優先使用預先設定的身分證（如果有）
        if idx < len(predefined_ids) and predefined_ids[idx]:
            id_number = predefined_ids[idx]
            print(f"乘客 {passenger_num} ({ticket_type}) 身分證字號：{id_number} [使用預設值]")
        else:
            # 詢問用戶輸入
            while True:
                id_number = input(f"乘客 {passenger_num} ({ticket_type}) 身分證字號：").strip()
                
                if _validate_id_format(id_number):
                    break
                else:
                    print("  ⚠️  身分證格式錯誤（應為 10 碼），請重新輸入")
        
        passenger_id_map[field_name] = id_number
    
    print("=" * 50)
    return passenger_id_map


def _check_duplicate_ids(passenger_id_map: dict, passenger_info_list: list) -> None:
    """檢查身分證字號是否重複（僅警告，不阻止）
    
    Args:
        passenger_id_map: {欄位名稱: 身分證字號} 的字典
        passenger_info_list: 乘客資訊列表
    """
    # 建立 {身分證: [(乘客編號, 票種)]} 的映射
    id_usage = {}
    field_to_info = {info['field_name']: info for info in passenger_info_list}
    
    for field_name, id_number in passenger_id_map.items():
        if id_number not in id_usage:
            id_usage[id_number] = []
        
        passenger_info = field_to_info.get(field_name, {})
        id_usage[id_number].append({
            'passenger_number': passenger_info.get('passenger_number', '?'),
            'ticket_type': passenger_info.get('ticket_type', '未知')
        })
    
    # 檢查重複使用的身分證
    has_warning = False
    for id_number, usages in id_usage.items():
        if len(usages) > 1:
            has_warning = True
            print(f"\n⚠️  警告：身分證字號 {id_number} 被多位乘客使用：")
            for usage in usages:
                print(f"   - 乘客 {usage['passenger_number']} ({usage['ticket_type']})")
            
            # 檢查是否違反規則
            ticket_types = [u['ticket_type'] for u in usages]
            if '敬老票' in ticket_types:
                elder_count = ticket_types.count('敬老票')
                if elder_count > 1:
                    print("   ❌ 錯誤：同一身分證號僅能用於 1 位乘客之敬老票")
                if any(t in ['愛心票'] for t in ticket_types):
                    print("   ❌ 錯誤：同一身分證號不能同時用於購買敬老票及愛心票")
    
    if has_warning:
        print("\n注意：以上警告可能導致訂票失敗，請確認是否繼續")
        confirm = input("是否繼續提交？(y/n)：").strip().lower()
        if confirm != 'y':
            print("已取消訂票")
            exit(0)


class ConfirmTicketFlow:
    def __init__(self, client: HTTPRequest, train_resp: Response, record: Record = None):
        self.client = client
        self.train_resp = train_resp
        self.record = record

    def run(self) -> Tuple[Response]:
        page = BeautifulSoup(self.train_resp.content, features='html.parser')
        personal_id = self.set_personal_id()
        ticket_model = ConfirmTicketModel(
            personal_id=personal_id,
            phone_num=self.set_phone_num(),
            member_radio=_parse_member_radio(page),
        )

        json_params = ticket_model.json(by_alias=True)
        dict_params = json.loads(json_params)

        # 解析並填入乘客身分證欄位（愛心票、敬老票等優惠票種）
        passenger_info_list = _parse_passenger_id_fields(page)
        if passenger_info_list:
            # 從 record 中取得預設的乘客身分證列表（如果有）
            predefined_ids = []
            if self.record and hasattr(self.record, 'passenger_ids'):
                predefined_ids = self.record.passenger_ids or []
            
            # 詢問用戶輸入每位乘客的身分證
            passenger_id_map = _prompt_passenger_ids(passenger_info_list, predefined_ids)
            
            # 檢查身分證重複（步驟 5）
            _check_duplicate_ids(passenger_id_map, passenger_info_list)
            
            # 填入參數
            for field_name, id_number in passenger_id_map.items():
                dict_params[field_name] = id_number

        resp = self.client.submit_ticket(dict_params)
        return resp, ticket_model

    def set_personal_id(self) -> str:
        if self.record and (personal_id := self.record.personal_id):
            return personal_id

        return input(f'輸入身分證字號：\n')

    def set_phone_num(self) -> str:
        if self.record and (phone_num := self.record.phone):
            return phone_num

        if phone_num := input('輸入手機號碼（預設：""）：\n'):
            return phone_num
        return ''


def _parse_member_radio(page: BeautifulSoup) -> str:
    candidates = page.find_all(
        'input',
        attrs={
            'name': 'TicketMemberSystemInputPanel:TakerMemberSystemDataView:memberSystemRadioGroup'
        },
    )
    tag = next((cand for cand in candidates if 'checked' in cand.attrs))
    return tag.attrs['value']

import re

def validate_schedule_message(message: str) -> bool:
    """
    檢查訊息是否包含足夠的行程資訊（日期或時間關鍵字）。
    避免將無意義的閒聊發送給 AI。
    
    Args:
        message: 用戶輸入的訊息
        
    Returns:
        bool: True 表示訊息包含行程關鍵字，False 表示資訊不足
    """
    if not message:
        return False
        
    # 關鍵字清單
    keywords = [
        # 相對日期
        r"今天", r"明天", r"後天", r"大後天", r"下週", r"下禮拜",
        
        # 絕對日期
        r"\d{1,2}月", r"\d{1,2}號", r"\d{1,2}日", r"\d{4}年",
        
        # 時間
        r"\d{1,2}點", r"\d{1,2}時", r"\d{1,2}分", 
        r"早上", r"上午", r"中午", r"下午", r"晚上", r"半",
        r"am", r"pm", r"AM", r"PM",
        
        # 模糊時間
        r"待會", r"等下", r"之後",
        
        # 行程動作（輔助判斷）
        r"去", r"開會", r"吃飯", r"聚餐", r"預約", r"提醒", r"行程"
    ]
    
    # 組合正則表達式
    pattern = "|".join(keywords)
    
    # 搜尋是否有匹配
    if re.search(pattern, message, re.IGNORECASE):
        return True
        
    return False

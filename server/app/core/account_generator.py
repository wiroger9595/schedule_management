import random
import string
from sqlmodel import Session, select
from ..models.user import User

def generate_account_number(session: Session) -> str:
    """
    生成唯一帳號：2英文 + 10數字
    例如：AB1234567890
    """
    while True:
        # 前2碼：大寫英文
        letters = ''.join(random.choices(string.ascii_uppercase, k=2))
        # 後10碼：數字
        numbers = ''.join(random.choices(string.digits, k=10))
        account_number = letters + numbers
        
        # 檢查唯一性
        existing = session.exec(
            select(User).where(User.account_number == account_number)
        ).first()
        
        if not existing:
            return account_number

def generate_user_id() -> str:
    """生成 12 位包含英文與數字的隨機字串"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(12))
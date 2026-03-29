import requests
import json

BASE_URL = "http://localhost:7800"

def test_create_schedule():
    print("--- 測試新增行程 ---")
    payload = {
        "title": "測試會議",
        "description": "測試 OSMnx 預估功能",
        "startTime": "2026-02-02T10:00:00",
        "location": "台北 101",
        "latitude": 25.0339,
        "longitude": 121.5644,
        "transportMode": "motorcycle"
    }
    res = requests.post(f"{BASE_URL}/api/schedules", json=payload)
    print(f"狀態碼: {res.status_code}")
    print(res.json())

def test_travel_estimate():
    print("\n--- 測試行程時間預估 (機車模式) ---")
    # 從 台北車站 (25.0478, 121.5170) 到 台北 101 (25.0339, 121.5644)
    params = {
        "lat1": 25.0478,
        "lon1": 121.5170,
        "lat2": 25.0339,
        "lon2": 121.5644,
        "mode": "motorcycle"
    }
    res = requests.get(f"{BASE_URL}/api/estimate", params=params)
    print(f"狀態碼: {res.status_code}")
    print(f"預估結果: {json.dumps(res.json(), indent=2)}")

if __name__ == "__main__":
    try:
        test_create_schedule()
        test_travel_estimate()
    except Exception as e:
        print(f"測試失敗 (請確保 server 已啟動): {e}")

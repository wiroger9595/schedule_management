import requests
import json
import uuid

base_url = "https://schedule-backend-200440251043.asia-east1.run.app/api"

# 1. Register a test user
email = f"test_{uuid.uuid4()}@example.com"
password = "password123"
requests.post(f"{base_url}/auth/register", json={
    "email": email, "password": password, "full_name": "Test User"
})

# 2. Login
login_resp = requests.post(f"{base_url}/auth/login", json={
    "email": email, "password": password
})
token = login_resp.json().get("access_token")

# 3. Create Contact
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
payload = {
    "nick_name": "My New Contact",
    "phone": "",
    "email": "",
    "line_id": ""
}
contact_resp = requests.post(f"{base_url}/contacts/", headers=headers, json=payload)

print("Status Code:", contact_resp.status_code)
print("Response:", contact_resp.text)

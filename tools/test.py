import httpx

url = "https://devapi.qweather.com/v2/city/lookup"
params = {
    "location": "北京",
    "key": "7966b75c76d34fff9de08a7f94b460ef"
}

with httpx.Client(timeout=10) as client:
    r = client.get(url, params=params)
    print("status:", r.status_code)
    print("headers:", r.headers)
    print("raw:", r.text[:500])
import requests

url = "https://query1.finance.yahoo.com/v8/finance/chart/AAPL?range=1y&interval=1d"
response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})

print(response)
print(response.status_code)

data = response.json() 
print(data["chart"]["result"][0].keys())  
price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
print(price)
print(closes[-5:])

from sma import sma, pct_distance

average = sma(closes, 150)
distance = pct_distance(price, average)
print(average)
print(distance)


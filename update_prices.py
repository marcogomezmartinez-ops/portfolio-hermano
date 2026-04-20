import requests, json, os, time
from datetime import datetime

prices = {}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.morningstar.es/es/funds/',
    'Accept': 'application/json',
}

def morningstar(isin, name):
    url = (f'https://tools.morningstar.es/api/rest.svc/timeseries_price/'
           f'2nhcdckzon?id={isin}&idtype=Isin&frequency=daily&outputType=JSON')
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            print(f"  ❌ {name}: HTTP {r.status_code}")
            return None
        data = r.json()
        if isinstance(data, list):
            ts = data[0].get('TimeSeries', {})
        elif isinstance(data, dict):
            ts = data.get('TimeSeries', {})
        else:
            return None
        securities = ts.get('Security', [])
        if not securities: return None
        hist = securities[0].get('HistoryDetail', [])
        if not hist: return None
        last = hist[-1]
        price = float(last.get('Value') or last.get('Close') or 0)
        if 0 < price < 10000:
            print(f"  ✅ {name}: €{price}")
            return round(price, 5)
        return None
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        return None

def yahoo(ticker, name):
    try:
        r = requests.get(f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d',
                         headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        price = r.json()['chart']['result'][0]['meta']['regularMarketPrice']
        print(f"  ✅ {name}: €{round(price, 5)}")
        return round(price, 5)
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        return None

print("🔄 Actualizando precios Tato...\n")

all_funds = [
    ('IE000QAZP7L2', 'iShares Emerging Markets'),
    ('IE000ZYRH0Q7', 'iShares Developed World'),
    ('LU0034353002', 'DWS Floating Rate Notes'),
    ('IE00BFZMJT78', 'Neuberger Berman Short Duration'),
    ('LU1694789451', 'DNCA Alpha Bonds'),
    ('ES0140794001', 'Gamma Global FI'),
    ('ES0175902008', 'Sigma Internacional FI'),
    ('ES0112231016', 'Avantage Fund B'),
]
for isin, name in all_funds:
    p = morningstar(isin, name)
    if p: prices[isin] = p
    time.sleep(1.5)

# iShares Physical Gold via Yahoo Finance (IGLN.L en GBp → EUR)
try:
    r_gold = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/IGLN.L?interval=1d&range=1d',
                     headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    r_fx = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/EURGBP=X?interval=1d&range=1d',
                      headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    price_gbp = r_gold.json()['chart']['result'][0]['meta']['regularMarketPrice']  # ya en GBP
    eurgbp = r_fx.json()['chart']['result'][0]['meta']['regularMarketPrice']
    price_eur = round(price_gbp / eurgbp, 5)  # GBP a EUR
    prices['IE00B4ND3602'] = price_eur
    print(f"  ✅ iShares Physical Gold: €{price_eur}")
except Exception as e:
    print(f"  ❌ iShares Physical Gold: {e}")

portfolio = [
    {'isin': 'IE000QAZP7L2', 'qty': 66.86},
    {'isin': 'IE000ZYRH0Q7', 'qty': 316.66},
    {'isin': 'LU0034353002', 'qty': 21.7847},
    {'isin': 'IE00BFZMJT78', 'qty': 17.729},
    {'isin': 'LU1694789451', 'qty': 15.5658},
    {'isin': 'ES0140794001', 'qty': 461.690519},
    {'isin': 'ES0175902008', 'qty': 39.667898},
    {'isin': 'ES0112231016', 'qty': 216.608132},
    {'isin': 'IE00B4ND3602', 'qty': 1},
]
fallback = {
    'IE000QAZP7L2': 12.683, 'IE000ZYRH0Q7': 11.06,
    'LU0034353002': 93.40,  'IE00BFZMJT78': 118.36,
    'LU1694789451': 130.47, 'ES0140794001': 13.72501,
    'ES0175902008': 20.28139, 'ES0112231016': 29.571,
    'IE00B4ND3602': 79.17,
}
total = round(sum((prices.get(a['isin']) or fallback[a['isin']]) * a['qty'] for a in portfolio), 2)
today = datetime.now().strftime('%Y-%m-%d')
print(f"\n📊 Total Tato ({today}): €{total:,.2f} ({len(prices)}/9 precios)")

existing = json.load(open('prices.json')) if os.path.exists('prices.json') else {}
history = existing.get('history', [])
entry = next((h for h in history if h['date'] == today), None)
if entry: entry['total'] = total
else: history.append({'date': today, 'total': total})
history.sort(key=lambda x: x['date'])

with open('prices.json', 'w') as f:
    json.dump({'updated': datetime.now().strftime('%Y-%m-%d %H:%M UTC'), 'prices': prices, 'history': history}, f, indent=2)
print(f'✅ prices.json: {len(prices)} precios, {len(history)} puntos')

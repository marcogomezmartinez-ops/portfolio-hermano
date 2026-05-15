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

print("🔄 Actualizando precios Tato v10.2...\n")

# ── FONDOS vía Morningstar ─────────────────────────────────────────────────────
all_funds = [
    ('IE000QAZP7L2', 'iShares Emerging Markets'),
    ('IE000ZYRH0Q7', 'iShares Developed World'),
    ('ES0140794001', 'Gamma Global FI'),
    ('ES0175902008', 'Sigma Internacional FI'),
    ('ES0112231016', 'Avantage Fund B'),
    ('ES0146309002', 'Horos Value Internacional'),
]
for isin, name in all_funds:
    p = morningstar(isin, name)
    if p: prices[isin] = p
    time.sleep(1.5)

# ── iShares Physical Gold vía Yahoo Finance (PPFB.SG — EUR, Stuttgart) ────────
try:
    r_gold = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/PPFB.SG?interval=1d&range=1d',
                     headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    price_eur = r_gold.json()['chart']['result'][0]['meta']['regularMarketPrice']
    prices['IE00B4ND3602'] = round(price_eur, 5)
    print(f"  ✅ iShares Physical Gold: €{round(price_eur, 5)}")
except Exception as e:
    print(f"  ❌ iShares Physical Gold: {e}")

# ── Cálculo total cartera Tato (v10.2) ────────────────────────────────────────
portfolio = [
    {'isin': 'IE000QAZP7L2', 'qty': 68.71},          # iShares Emerging Markets
    {'isin': 'IE000ZYRH0Q7', 'qty': 325.38},          # iShares Developed World
    {'isin': 'ES0140794001', 'qty': 415.209233},       # Gamma Global FI
    {'isin': 'ES0175902008', 'qty': 40.890191},        # Sigma Internacional FI
    {'isin': 'ES0112231016', 'qty': 216.608132},       # Avantage Fund B
    {'isin': 'ES0146309002', 'qty': 3.43176278},       # Horos Value Internacional
    {'isin': 'IE00B4ND3602', 'qty': 2},                # iShares Physical Gold
]

fallback = {
    'IE000QAZP7L2': 13.654,
    'IE000ZYRH0Q7': 11.476,
    'ES0140794001': 13.8278,
    'ES0175902008': 20.48988,
    'ES0112231016': 29.18112,
    'ES0146309002': 216.68459,
    'IE00B4ND3602': 77.50,
}

total = round(sum((prices.get(a['isin']) or fallback.get(a['isin'], 0)) * a['qty'] for a in portfolio), 2)
today = datetime.now().strftime('%Y-%m-%d')
print(f"\n📊 Total Tato ({today}): €{total:,.2f} ({len(prices)}/7 precios)")

existing = json.load(open('prices.json')) if os.path.exists('prices.json') else {}
history = existing.get('history', [])
entry = next((h for h in history if h['date'] == today), None)
if entry: entry['total'] = total
else: history.append({'date': today, 'total': total})
history.sort(key=lambda x: x['date'])

with open('prices.json', 'w') as f:
    json.dump({'updated': datetime.now().strftime('%Y-%m-%d %H:%M UTC'), 'prices': prices, 'history': history}, f, indent=2)
print(f'✅ prices.json: {len(prices)} precios, {len(history)} puntos')

import requests, json, os
from datetime import datetime

prices = {}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
EUR_GBP = 1.17

def yahoo_to_eur(raw, currency, ticker):
    """
    Convert Yahoo Finance price to EUR.
    CRITICAL: iShares ETFs on London Stock Exchange (.L) are ALWAYS quoted
    in GBp (pence), never GBP (pounds), even if Yahoo labels them 'GBP'.
    So for .L tickers: ALWAYS divide by 100 first, then convert to EUR.
    """
    if ticker.endswith('.L'):
        # Always treat .L as GBp (pence) → divide by 100 → convert to EUR
        return (raw / 100) * EUR_GBP
    elif currency == 'USD':
        return raw * 0.92
    return raw


# ── ETFs via Yahoo Finance ────────────────────────────────────────────────
yahoo_map = {
    'IE000QAZP7L2': 'EIMI.L',
    'IE000ZYRH0Q7': 'SWDA.L',
}
for isin, ticker in yahoo_map.items():
    try:
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d'
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        result = data['chart']['result'][0]
        raw = result['meta']['regularMarketPrice']
        curr = result['meta']['currency']
        price = yahoo_to_eur(raw, curr, ticker)
        prices[isin] = round(price, 5)
        print(f"  ✅ {ticker}: raw={raw} ({curr}) → €{prices[isin]}")
    except Exception as e:
        print(f"  ❌ {ticker}: {e}")

# ── Fondos ES/LU/IE via Morningstar ──────────────────────────────────────
ms_headers = {**headers, 'Referer': 'https://www.morningstar.es/'}
fund_isins = [
    ('LU0034353002', 'DWS Floating Rate Notes'),
    ('IE00BFZMJT78', 'Neuberger Berman Short Duration'),
    ('LU1694789451', 'DNCA Alpha Bonds'),
    ('ES0140794001', 'Gamma Global FI'),
    ('ES0175902008', 'Sigma Internacional FI'),
    ('ES0112231016', 'Avantage Fund B'),
]
for isin, name in fund_isins:
    try:
        url = (f'https://tools.morningstar.es/api/rest.svc/timeseries_price/'
               f'2nhcdckzon?id={isin}&idtype=Isin&frequency=daily&outputType=JSON')
        r = requests.get(url, headers=ms_headers, timeout=10)
        data = r.json()
        hist = data[0]['TimeSeries']['Security'][0]['HistoryDetail']
        price = float(hist[-1]['Value'])
        if price > 10000:
            print(f"  ⚠️  {name}: {price} incorrecto, omitiendo")
            continue
        prices[isin] = round(price, 5)
        print(f"  ✅ {name}: €{price}")
    except Exception as e:
        print(f"  ❌ {name}: {e}")

# ── Calcular total cartera Tato ───────────────────────────────────────────
portfolio = [
    {'isin': 'IE000QAZP7L2', 'qty': 66.86},
    {'isin': 'IE000ZYRH0Q7', 'qty': 316.66},
    {'isin': 'LU0034353002', 'qty': 21.7847},
    {'isin': 'IE00BFZMJT78', 'qty': 17.729},
    {'isin': 'LU1694789451', 'qty': 15.5658},
    {'isin': 'ES0140794001', 'qty': 461.690519},
    {'isin': 'ES0175902008', 'qty': 39.667898},
    {'isin': 'ES0112231016', 'qty': 216.608132},
]
fallback = {
    'IE000QAZP7L2': 12.339, 'IE000ZYRH0Q7': 10.947,
    'LU0034353002': 93.35,  'IE00BFZMJT78': 118.21,
    'LU1694789451': 130.17, 'ES0140794001': 13.67134,
    'ES0175902008': 19.81392, 'ES0112231016': 29.32158,
}
total = sum((prices.get(a['isin']) or fallback.get(a['isin'], 0)) * a['qty'] for a in portfolio)
total = round(total, 2)
today = datetime.now().strftime('%Y-%m-%d')
print(f"\n  📊 Total Tato ({today}): €{total:,.2f}")

# ── Actualizar prices.json ────────────────────────────────────────────────
existing = json.load(open('prices.json')) if os.path.exists('prices.json') else {}
history = existing.get('history', [])
entry = next((h for h in history if h['date'] == today), None)
if entry: entry['total'] = total
else: history.append({'date': today, 'total': total})
history.sort(key=lambda x: x['date'])

output = {'updated': datetime.now().strftime('%Y-%m-%d %H:%M UTC'), 'prices': prices, 'history': history}
with open('prices.json', 'w') as f:
    json.dump(output, f, indent=2)
print(f'✅ prices.json: {len(prices)} precios, {len(history)} puntos históricos')

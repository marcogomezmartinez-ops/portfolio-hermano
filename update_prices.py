import requests, json
from datetime import datetime

prices = {}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# ── ETFs via Yahoo Finance ────────────────────────────────────────────────
# IMPORTANT: London ETFs (.L) are priced in GBp (pence), not GBP
# Yahoo Finance returns 'GBp' for pence - must divide by 100 then multiply by EUR rate
yahoo_map = {
    'IE000QAZP7L2': ('EIMI.L',  'GBp'),  # iShares Emerging Markets
    'IE000ZYRH0Q7': ('SWDA.L',  'GBp'),  # iShares Developed World
}

EUR_GBP = 1.17  # approx EUR/GBP rate

for isin, (ticker, expected_currency) in yahoo_map.items():
    try:
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d'
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        result = data['chart']['result'][0]
        raw_price = result['meta']['regularMarketPrice']
        currency = result['meta']['currency']
        print(f"  {ticker}: raw={raw_price} currency={currency}")
        
        if currency == 'GBp':        # pence → EUR
            price = (raw_price / 100) * EUR_GBP
        elif currency == 'GBP':      # pounds → EUR
            price = raw_price * EUR_GBP
        elif currency == 'USD':
            price = raw_price * 0.92
        else:
            price = raw_price

        prices[isin] = round(price, 5)
        print(f"  ✅ {ticker}: €{prices[isin]}")
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
        history = data[0]['TimeSeries']['Security'][0]['HistoryDetail']
        price = float(history[-1]['Value'])
        # Sanity check: fund prices should be reasonable (not thousands)
        if price > 10000:
            print(f"  ⚠️  {name}: price {price} looks wrong, skipping")
            continue
        prices[isin] = round(price, 5)
        print(f"  ✅ {name}: €{price}")
    except Exception as e:
        print(f"  ❌ {name} ({isin}): {e}")

# ── Bitcoin via CoinGecko ─────────────────────────────────────────────────
try:
    r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur', timeout=10)
    btc = r.json()['bitcoin']['eur']
    prices['BTC'] = btc
    print(f"  ✅ Bitcoin: €{btc:,}")
except Exception as e:
    print(f"  ❌ Bitcoin: {e}")

# ── Escribir prices.json ──────────────────────────────────────────────────
output = {'updated': datetime.now().strftime('%Y-%m-%d %H:%M UTC'), 'prices': prices}
with open('prices.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f'\n✅ prices.json actualizado con {len(prices)} precios:')
for k, v in prices.items():
    print(f'   {k}: €{v}')

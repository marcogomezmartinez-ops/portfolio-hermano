import requests
import json
from datetime import datetime

prices = {}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
}

# ── ETFs via Yahoo Finance (servidor: sin CORS) ──────────────────────────
yahoo_map = {
    'IE000QAZP7L2': 'EIMI.L',   # iShares Emerging Markets
    'IE000ZYRH0Q7': 'SWDA.L',   # iShares Developed World
    'IE00BFZMJT78': 'IBGS.L',   # Neuberger Berman (approx via iShares bond ETF)
}

for isin, ticker in yahoo_map.items():
    try:
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d'
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        result = data['chart']['result'][0]
        price = result['meta']['regularMarketPrice']
        currency = result['meta']['currency']
        if currency in ('GBp',):      # pence → libras → euros
            price = price / 100 * 1.17
        elif currency == 'GBP':
            price = price * 1.17
        elif currency == 'USD':
            price = price * 0.92
        prices[isin] = round(price, 5)
        print(f'✅ {ticker}: €{prices[isin]}')
    except Exception as e:
        print(f'❌ {ticker}: {e}')

# ── Fondos ES/LU via Morningstar (servidor: sin CORS) ────────────────────
ms_headers = {**headers, 'Referer': 'https://www.morningstar.es/'}
fund_isins = [
    'LU0034353002',  # DWS Floating Rate Notes
    'LU1694789451',  # DNCA Alpha Bonds
    'ES0140794001',  # Gamma Global FI
    'ES0175902008',  # Sigma Internacional FI
    'ES0112231016',  # Avantage Fund B
]

for isin in fund_isins:
    try:
        url = (f'https://tools.morningstar.es/api/rest.svc/timeseries_price/'
               f'2nhcdckzon?id={isin}&idtype=Isin&frequency=daily&outputType=JSON')
        r = requests.get(url, headers=ms_headers, timeout=10)
        data = r.json()
        history = data[0]['TimeSeries']['Security'][0]['HistoryDetail']
        price = float(history[-1]['Value'])
        prices[isin] = round(price, 5)
        print(f'✅ {isin}: €{price}')
    except Exception as e:
        print(f'❌ {isin}: {e}')

# ── Neuberger Berman via Morningstar también ─────────────────────────────
try:
    isin = 'IE00BFZMJT78'
    url = (f'https://tools.morningstar.es/api/rest.svc/timeseries_price/'
           f'2nhcdckzon?id={isin}&idtype=Isin&frequency=daily&outputType=JSON')
    r = requests.get(url, headers=ms_headers, timeout=10)
    data = r.json()
    history = data[0]['TimeSeries']['Security'][0]['HistoryDetail']
    price = float(history[-1]['Value'])
    prices[isin] = round(price, 5)
    print(f'✅ IE00BFZMJT78 (Neuberger) via Morningstar: €{price}')
except Exception as e:
    print(f'⚠️  Neuberger via Yahoo fallback ya cargado o error: {e}')

# ── Bitcoin via CoinGecko ─────────────────────────────────────────────────
try:
    r = requests.get(
        'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur',
        timeout=10
    )
    btc_price = r.json()['bitcoin']['eur']
    prices['BTC'] = btc_price
    print(f'✅ Bitcoin: €{btc_price}')
except Exception as e:
    print(f'❌ Bitcoin: {e}')

# ── Escribir prices.json ──────────────────────────────────────────────────
output = {
    'updated': datetime.now().strftime('%Y-%m-%d %H:%M UTC'),
    'prices': prices
}

with open('prices.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f'\n✅ prices.json actualizado con {len(prices)} precios')
print(json.dumps(prices, indent=2))

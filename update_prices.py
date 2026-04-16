import requests, json, os, time
from datetime import datetime

prices = {}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}
EUR_GBP = 1.17

# ── SOURCE 1: Yahoo Finance para ETFs con ticker .L (sin CORS en servidor) ─
def yahoo_price(ticker):
    try:
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d'
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        raw = data['chart']['result'][0]['meta']['regularMarketPrice']
        curr = data['chart']['result'][0]['meta']['currency']
        print(f"    Yahoo {ticker}: raw={raw} ({curr})")
        # iShares .L cotizan en GBp (peniques) → ÷100 → ×EUR_GBP
        if ticker.endswith('.L'):
            return round((raw / 100) * EUR_GBP, 5)
        elif curr == 'USD':
            return round(raw * 0.92, 5)
        return round(raw, 5)
    except Exception as e:
        print(f"    ❌ Yahoo {ticker}: {e}")
        return None

# ── SOURCE 2: CNMV API para fondos españoles (ES ISINs) ───────────────────
def cnmv_price(isin, name):
    try:
        # CNMV public API
        url = f'https://www.cnmv.es/portal/HR/API/IIC/Nav?isin={isin}'
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        # CNMV returns list of NAV records, take most recent
        if isinstance(data, list) and len(data) > 0:
            latest = sorted(data, key=lambda x: x.get('fecha', ''), reverse=True)[0]
            price = float(latest.get('vl', 0) or latest.get('nav', 0) or latest.get('valor', 0))
            if price > 0:
                print(f"    ✅ CNMV {name}: €{price}")
                return round(price, 5)
        print(f"    CNMV {name}: sin datos, intentando Morningstar...")
        return None
    except Exception as e:
        print(f"    CNMV {name}: {e}, intentando Morningstar...")
        return None

# ── SOURCE 3: Morningstar con headers completos ────────────────────────────
def morningstar_price(isin, name):
    try:
        ms_headers = {
            **headers,
            'Referer': 'https://www.morningstar.es/es/funds/',
            'Origin': 'https://www.morningstar.es',
        }
        url = (f'https://tools.morningstar.es/api/rest.svc/timeseries_price/'
               f'2nhcdckzon?id={isin}&idtype=Isin&frequency=daily&outputType=JSON')
        r = requests.get(url, headers=ms_headers, timeout=15)
        if r.status_code != 200:
            print(f"    Morningstar {name}: HTTP {r.status_code}")
            return None
        data = r.json()
        if not isinstance(data, list) or len(data) == 0:
            return None
        hist = data[0]['TimeSeries']['Security'][0]['HistoryDetail']
        price = float(hist[-1]['Value'])
        if 0 < price < 10000:
            print(f"    ✅ Morningstar {name}: €{price}")
            return round(price, 5)
        return None
    except Exception as e:
        print(f"    Morningstar {name}: {e}")
        return None

# ── SOURCE 4: justetf.com para ETFs por ISIN ──────────────────────────────
def justetf_price(isin, name):
    try:
        url = f'https://www.justetf.com/api/etfs/{isin}/quote?locale=es'
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        price = data.get('latestQuote', {}).get('price', 0)
        currency = data.get('latestQuote', {}).get('currency', '')
        if price and float(price) > 0:
            p = float(price)
            if currency == 'GBX': p = (p / 100) * EUR_GBP
            elif currency == 'GBP': p = p * EUR_GBP
            elif currency == 'USD': p = p * 0.92
            print(f"    ✅ justetf {name}: €{round(p,5)}")
            return round(p, 5)
        return None
    except Exception as e:
        print(f"    justetf {name}: {e}")
        return None

print("🔄 Actualizando precios fondos de Tato...")
print()

# ── ETFs iShares → Yahoo Finance (.L tickers) ────────────────────────────
print("📊 ETFs via Yahoo Finance:")
etfs = [
    ('IE000QAZP7L2', 'iShares Emerging Markets',  'EIMI.L'),
    ('IE000ZYRH0Q7', 'iShares Developed World',   'SWDA.L'),
]
for isin, name, ticker in etfs:
    p = yahoo_price(ticker)
    if p:
        prices[isin] = p
        print(f"  ✅ {name}: €{p}")
    else:
        print(f"  ❌ {name}: sin precio")
    time.sleep(0.5)

# ── Fondos españoles → CNMV primero, luego Morningstar ───────────────────
print("\n📊 Fondos españoles:")
es_funds = [
    ('ES0140794001', 'Gamma Global FI'),
    ('ES0175902008', 'Sigma Internacional FI'),
    ('ES0112231016', 'Avantage Fund B'),
]
for isin, name in es_funds:
    p = cnmv_price(isin, name)
    if not p:
        p = morningstar_price(isin, name)
    if not p:
        p = justetf_price(isin, name)
    if p:
        prices[isin] = p
        print(f"  ✅ {name}: €{p}")
    else:
        print(f"  ❌ {name}: sin precio de ninguna fuente")
    time.sleep(1)

# ── Fondos LU → Morningstar, luego justetf ───────────────────────────────
print("\n📊 Fondos Luxemburgo:")
lu_funds = [
    ('LU0034353002', 'DWS Floating Rate Notes'),
    ('LU1694789451', 'DNCA Alpha Bonds'),
]
for isin, name in lu_funds:
    p = morningstar_price(isin, name)
    if not p:
        p = justetf_price(isin, name)
    if p:
        prices[isin] = p
        print(f"  ✅ {name}: €{p}")
    else:
        print(f"  ❌ {name}: sin precio de ninguna fuente")
    time.sleep(1)

# ── Neuberger Berman (IE ISIN, no .L ticker claro) → Morningstar ─────────
print("\n📊 Neuberger Berman:")
p = morningstar_price('IE00BFZMJT78', 'Neuberger Berman Short Duration')
if not p:
    p = justetf_price('IE00BFZMJT78', 'Neuberger Berman Short Duration')
if p:
    prices['IE00BFZMJT78'] = p
    print(f"  ✅ Neuberger Berman: €{p}")
else:
    print(f"  ❌ Neuberger Berman: sin precio")

# ── Cartera Tato ──────────────────────────────────────────────────────────
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
total = round(sum((prices.get(a['isin']) or fallback[a['isin']]) * a['qty'] for a in portfolio), 2)
today = datetime.now().strftime('%Y-%m-%d')
print(f"\n📊 Total Tato ({today}): €{total:,.2f}")
print(f"   Precios obtenidos: {len(prices)}/8")

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
print(f'✅ prices.json actualizado: {len(prices)} precios, {len(history)} puntos históricos')

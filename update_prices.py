import requests, json, os, time
from datetime import datetime

prices = {}
EUR_GBP = 1.17
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def yahoo_gbp(ticker, isin, name):
    """ETFs de iShares en Londres: Yahoo devuelve GBp (peniques) → ÷100 → ×EUR_GBP"""
    try:
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d'
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        raw = data['chart']['result'][0]['meta']['regularMarketPrice']
        # SIEMPRE dividir entre 100 para .L (son peniques, no libras)
        eur = round((raw / 100) * EUR_GBP, 5)
        print(f"  ✅ {name}: {raw}GBp → €{eur}")
        return eur
    except Exception as e:
        print(f"  ❌ {name} Yahoo: {e}")
        return None

def cnmv(isin, name):
    """Fondos españoles via CNMV (API pública española)"""
    try:
        url = f'https://www.cnmv.es/portal/HR/API/IIC/Nav?isin={isin}'
        r = requests.get(url, headers=headers, timeout=15)
        print(f"    CNMV {name}: HTTP {r.status_code} | {r.text[:100]}")
        data = r.json()
        if isinstance(data, list) and data:
            item = sorted(data, key=lambda x: x.get('fecha',''), reverse=True)[0]
            for k in ['vl','VL','nav','Nav','valor','Valor','importe']:
                v = item.get(k)
                if v is not None and float(str(v).replace(',','.')) > 0:
                    price = round(float(str(v).replace(',','.')), 5)
                    print(f"  ✅ CNMV {name}: €{price}")
                    return price
        return None
    except Exception as e:
        print(f"  ❌ CNMV {name}: {e}")
        return None

def morningstar(isin, name):
    """Morningstar con múltiples endpoints"""
    endpoints = [
        f'https://tools.morningstar.es/api/rest.svc/timeseries_price/2nhcdckzon?id={isin}&idtype=Isin&frequency=daily&outputType=JSON',
        f'https://lt.morningstar.com/api/rest.svc/klr5zyak8x/security/screener?page=1&pageSize=1&outputType=json&version=1&languageId=es-ES&currencyId=EUR&universeIds=FOESP%24%24ALL&securityDataPoints=secId%2CsecExternalId%2ClegalName%2CdayEndNav&filters=SecId%3AIN%3A{isin}',
    ]
    ms_headers = {**headers, 'Referer': 'https://www.morningstar.es/es/funds/'}
    for url in endpoints:
        try:
            r = requests.get(url, headers=ms_headers, timeout=15)
            print(f"    MS {name}: HTTP {r.status_code} | {r.text[:80]}")
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and data:
                    hist = data[0]['TimeSeries']['Security'][0]['HistoryDetail']
                    price = float(hist[-1]['Value'])
                    if 0 < price < 10000:
                        print(f"  ✅ MS {name}: €{price}")
                        return round(price, 5)
        except Exception as e:
            print(f"    MS {e}")
    return None

print("🔄 Actualizando precios Tato...\n")

# iShares ETFs → Yahoo Finance con corrección GBp (PROBADO QUE FUNCIONA)
print("📊 iShares ETFs (Yahoo Finance GBp):")
etfs = [
    ('EIMI.L', 'IE000QAZP7L2', 'iShares Emerging Markets'),
    ('SWDA.L', 'IE000ZYRH0Q7', 'iShares Developed World'),
]
for ticker, isin, name in etfs:
    p = yahoo_gbp(ticker, isin, name)
    if p: prices[isin] = p
    time.sleep(1)

# Fondos ES → CNMV
print("\n📊 Fondos españoles (CNMV):")
es_funds = [
    ('ES0140794001', 'Gamma Global FI'),
    ('ES0175902008', 'Sigma Internacional FI'),
    ('ES0112231016', 'Avantage Fund B'),
]
for isin, name in es_funds:
    p = cnmv(isin, name)
    if not p: p = morningstar(isin, name)
    if p: prices[isin] = p
    else: print(f"  ❌ {name}: sin precio")
    time.sleep(2)

# Fondos LU/IE → Morningstar con log detallado
print("\n📊 Fondos LU/IE (Morningstar):")
other_funds = [
    ('LU0034353002', 'DWS Floating Rate Notes'),
    ('IE00BFZMJT78', 'Neuberger Berman Short Duration'),
    ('LU1694789451', 'DNCA Alpha Bonds'),
]
for isin, name in other_funds:
    p = morningstar(isin, name)
    if p: prices[isin] = p
    else: print(f"  ❌ {name}: sin precio")
    time.sleep(2)

# Total
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
print(f"\n📊 Total Tato ({today}): €{total:,.2f} ({len(prices)}/8 precios)")

existing = json.load(open('prices.json')) if os.path.exists('prices.json') else {}
history = existing.get('history', [])
entry = next((h for h in history if h['date'] == today), None)
if entry: entry['total'] = total
else: history.append({'date': today, 'total': total})
history.sort(key=lambda x: x['date'])

with open('prices.json', 'w') as f:
    json.dump({'updated': datetime.now().strftime('%Y-%m-%d %H:%M UTC'), 'prices': prices, 'history': history}, f, indent=2)
print(f'✅ prices.json: {len(prices)} precios, {len(history)} puntos')

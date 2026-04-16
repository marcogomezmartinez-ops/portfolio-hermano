import json, os, time
from datetime import datetime

# curl_cffi imita Chrome TLS fingerprint → bypassa bloqueos de Morningstar
try:
    from curl_cffi import requests
    CHROME = {"impersonate": "chrome110"}
    print("✅ curl_cffi disponible (modo Chrome)")
except ImportError:
    import requests
    CHROME = {}
    print("⚠️  curl_cffi no disponible, usando requests normal")

prices = {}

def morningstar_price(isin, name):
    """Precio via Morningstar con Chrome TLS fingerprint."""
    try:
        url = (f'https://tools.morningstar.es/api/rest.svc/timeseries_price/'
               f'2nhcdckzon?id={isin}&idtype=Isin&frequency=daily&outputType=JSON')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es-ES,es;q=0.9',
            'Referer': 'https://www.morningstar.es/es/funds/',
            'Origin': 'https://www.morningstar.es',
        }
        r = requests.get(url, headers=headers, timeout=20, **CHROME)
        if r.status_code != 200:
            print(f"    HTTP {r.status_code} para {name}")
            return None
        data = r.json()
        if not isinstance(data, list) or not data:
            return None
        hist = data[0]['TimeSeries']['Security'][0]['HistoryDetail']
        price = float(hist[-1]['Value'])
        if 0 < price < 10000:
            return round(price, 5)
        return None
    except Exception as e:
        print(f"    Morningstar {name}: {e}")
        return None

def cnmv_price(isin, name):
    """Precio via CNMV para fondos españoles."""
    try:
        from datetime import date
        today = date.today().strftime('%d/%m/%Y')
        url = f'https://www.cnmv.es/portal/HR/API/IIC/Nav?isin={isin}&fecha={today}'
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json',
        }
        r = requests.get(url, headers=headers, timeout=20, **CHROME)
        text = r.text.strip()
        if not text or text.startswith('<'):
            return None
        data = json.loads(text)
        if isinstance(data, list) and data:
            latest = sorted(data, key=lambda x: x.get('fecha',''), reverse=True)[0]
            for key in ['vl','nav','valor','VL','Nav','Valor']:
                v = latest.get(key)
                if v and float(v) > 0:
                    return round(float(v), 5)
        elif isinstance(data, dict):
            for key in ['vl','nav','valor','VL','Nav','Valor']:
                v = data.get(key)
                if v and float(v) > 0:
                    return round(float(v), 5)
        return None
    except Exception as e:
        print(f"    CNMV {name}: {e}")
        return None

print("🔄 Actualizando precios Tato...\n")

# ── Todos los fondos via Morningstar (única fuente correcta para clase S) ──
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
    p = morningstar_price(isin, name)
    # Fallback CNMV para fondos españoles
    if not p and isin.startswith('ES'):
        p = cnmv_price(isin, name)
    if p:
        prices[isin] = p
        print(f"  ✅ {name}: €{p}")
    else:
        print(f"  ❌ {name}: sin precio")
    time.sleep(1)

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

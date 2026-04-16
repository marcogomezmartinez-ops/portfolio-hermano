import requests, json, os
from datetime import datetime

prices = {}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
ms_headers = {**headers, 'Referer': 'https://www.morningstar.es/'}

# ── TODOS los fondos y ETFs via Morningstar (EUR directo, sin conversion) ─
# Incluye iShares ETFs irlandeses - Morningstar devuelve NAV en EUR
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
    try:
        url = (f'https://tools.morningstar.es/api/rest.svc/timeseries_price/'
               f'2nhcdckzon?id={isin}&idtype=Isin&frequency=daily&outputType=JSON')
        r = requests.get(url, headers=ms_headers, timeout=10)
        data = r.json()
        hist = data[0]['TimeSeries']['Security'][0]['HistoryDetail']
        price = float(hist[-1]['Value'])
        if price <= 0 or price > 10000:
            print(f"  ⚠️  {name}: precio {price} sospechoso, omitiendo")
            continue
        prices[isin] = round(price, 5)
        print(f"  ✅ {name}: €{price}")
    except Exception as e:
        print(f"  ❌ {name} ({isin}): {e}")

# ── Cartera de Tato (sin Tesla ni Bitcoin) ────────────────────────────────
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
print(f"\n  📊 Total Tato ({today}): €{total:,.2f}")

# ── Actualizar prices.json con historial ─────────────────────────────────
existing = json.load(open('prices.json')) if os.path.exists('prices.json') else {}
history = existing.get('history', [])
entry = next((h for h in history if h['date'] == today), None)
if entry: entry['total'] = total
else: history.append({'date': today, 'total': total})
history.sort(key=lambda x: x['date'])

output = {'updated': datetime.now().strftime('%Y-%m-%d %H:%M UTC'), 'prices': prices, 'history': history}
with open('prices.json', 'w') as f:
    json.dump(output, f, indent=2)
print(f'✅ prices.json: {len(prices)} precios, {len(history)} puntos historicos')

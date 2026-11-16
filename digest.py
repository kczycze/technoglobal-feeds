# Buduje feeds/digest.json: krotka lista dla researchu (mniej tokenow niz caly latest.json).
# Odsiewa notowania gieldowe, raporty rynkowe, marketing i lokalne drobiazgi; zostawia najswiezsze pozycje na kategorie.
import json, re
NOISE = re.compile(r"\b(stock|stocks|shares|investor|earnings|dividend|price target|market size|market share|"
                   r"forecast to \d{4}|forecast \d{4}|cagr|market report|market research|market analysis|global\b.*\bmarket|business report|outlook report|analysis report|development report|report \d{4}|"
                   r"\bmarket \d{4}|nutritionist|dietitian|webinar|podcast|"
                   r"concert|recipe|horoscope|obituary|lottery|nfl|nba|grand prix|mortgage|coupon|deal of the day|"
                   r"notowania|kurs akcji|dywidend)\b", re.I)
LIMIT = {'news': 15, 'komunikat': 20, 'pl': 15}
d = json.load(open('feeds/latest.json', encoding='utf-8'))
out, per = [], {}
for x in d['items']:
    if NOISE.search(x['title']) or NOISE.search(x.get('source') or ''): continue
    key = (x['cat'], x['kind'].split(':')[0])
    lim = LIMIT.get(key[1], 10)
    if per.get(key, 0) >= lim: continue
    per[key] = per.get(key, 0) + 1
    out.append({'cat': x['cat'], 'kind': x['kind'], 't': x['title'], 's': x['source'], 'at': (x['published'] or '')[:16]})
json.dump({'generated': d['generated'], 'count': len(out), 'from': d['count'], 'items': out},
          open('feeds/digest.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('digest', len(out), 'z', d['count'])

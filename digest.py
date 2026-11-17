# Buduje feeds/digest.json: krotka lista dla researchu (mniej tokenow niz caly latest.json).
# Odsiewa notowania gieldowe, raporty rynkowe, marketing i lokalne drobiazgi; zostawia najswiezsze pozycje na kategorie.
import json, re, datetime
from zoneinfo import ZoneInfo
NOISE = re.compile(r"\b(stock|stocks|shares|investor|earnings|dividend|price target|market size|market share|"
                   r"forecast to \d{4}|forecast \d{4}|cagr|market report|market research|market analysis|global\b.*\bmarket|business report|outlook report|analysis report|development report|report \d{4}|"
                   r"\bmarket \d{4}|nutritionist|dietitian|webinar|podcast|"
                   r"concert|recipe|horoscope|obituary|lottery|nfl|nba|grand prix|mortgage|coupon|deal of the day|"
                   r"notowania|kurs akcji|dywidend)\b", re.I)
LIMIT = {'news': 15, 'komunikat': 20, 'pl': 15}
# Godziny researchu (czas polski). Najpierw idzie to, czego poprzedni research jeszcze nie widzial (n: 1).
RESEARCH = ['07:21', '15:51']
WAW = ZoneInfo('Europe/Warsaw')
d = json.load(open('feeds/latest.json', encoding='utf-8'))
now = datetime.datetime.fromisoformat(d['generated']).astimezone(WAW)
slots = [now.replace(hour=int(h), minute=int(m), second=0, microsecond=0) - datetime.timedelta(days=dd)
         for dd in (0, 1) for h, m in (r.split(':') for r in RESEARCH)]
since = max(s for s in slots if s <= now)
def is_new(x):
    t = x.get('seen') or x.get('published')
    return bool(t) and datetime.datetime.fromisoformat(t) >= since
items = sorted(d['items'], key=lambda x: (not is_new(x), ''), )  # stabilnie: nowe najpierw, w srodku od najnowszych
out, per = [], {}
for x in items:
    if NOISE.search(x['title']) or NOISE.search(x.get('source') or ''): continue
    key = (x['cat'], x['kind'].split(':')[0])
    lim = LIMIT.get(key[1], 10)
    if per.get(key, 0) >= lim: continue
    per[key] = per.get(key, 0) + 1
    out.append({'cat': x['cat'], 'kind': x['kind'], 't': x['title'], 's': x['source'], 'at': (x.get('published') or '')[:16],
                'n': 1 if is_new(x) else 0})
json.dump({'generated': d['generated'], 'since': since.astimezone(datetime.timezone.utc).isoformat()[:16],
           'count': len(out), 'new': sum(o['n'] for o in out), 'from': d['count'], 'items': out},
          open('feeds/digest.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('digest', len(out), 'z', d['count'], '; nowe od', since.isoformat()[:16], ':', sum(o['n'] for o in out))

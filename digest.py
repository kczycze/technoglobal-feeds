# Buduje feeds/digest.json: krotka lista dla researchu (mniej tokenow niz caly latest.json).
# 18.11.2026: kazdy naglowek dostaje ocene wstepna (sc); do listy trafiaja najlepsze w kategorii, nie najnowsze.
import json, re, datetime
from zoneinfo import ZoneInfo
NOISE = re.compile(r"\b(stock|stocks|shares|investor|earnings|dividend|price target|market size|market share|"
                   r"forecast to \d{4}|forecast \d{4}|cagr|market report|market research|market analysis|global\b.*\bmarket|business report|outlook report|analysis report|development report|report \d{4}|"
                   r"\bmarket \d{4}|nutritionist|dietitian|webinar|podcast|appoints|board of directors|"
                   r"concert|recipe|horoscope|obituary|lottery|nfl|nba|grand prix|mortgage|coupon|deal of the day|"
                   r"notowania|kurs akcji|dywidend|wernisaż|horoskop)\b", re.I)
PLUS = re.compile(r"\b(first|record|unveil\w*|breakthrough|world'?s|largest|fastest|smallest|tallest|longest|discover\w*|new type|prototype|"
                  r"maiden|milestone|launch\w*|lands?|landing|images?|reveals?|develop\w*|invent\w*|demonstrat\w*|achiev\w*|"
                  r"pierwsz\w*|rekord\w*|odkry\w*|przełom\w*)", re.I)
MINUS = re.compile(r"\b(killed|dies|died|dead|injur\w*|crash|arrest\w*|police|court|lawsuit|sues|ordinance|zoning|residents|council|"
                   r"protest\w*|strike|attack\w*|war\b|ukraine|russia\w*|gaza|israel|iran|election|trump|senator|lawmakers|tariff\w*|"
                   r"invest\w*|fund\w*|ipo|valuation|revenue|profit|acquir\w*|merger|partnership|agreement|signs|contract|deal\b|"
                   r"bomb\w*|nuclear weapon\w*|moratorium|pause|township|county|sheriff|charged|ghost|holiday|christmas|explainer|commentary|breakingviews|exports?|curbs?|regulations?|pushback|backlash|opinion|review:|how to|best \w+ (for|of)|vs\.?|\?$)", re.I)
WEAK_SRC = re.compile(r"(yahoo|msn|studyfinds|asianet|mashable india|crypto|benzinga|motley fool|zacks|seeking alpha|"
                      r"migflug|ssbcrack|the cool down|bioengineer|newsable|devdiscourse|scienmag)", re.I)
GOOD_SRC = re.compile(r"(reuters|associated press|\bap\b|bbc|guardian|new york times|washington post|financial times|economist|"
                      r"nature|science|nasa|esa|interesting engineering|new atlas|ieee|mit|ars technica|spacenews|space\.com|"
                      r"electrek|electrive|the robot report|new scientist|phys\.org|techxplore|eurekalert|the war zone|breaking defense|"
                      r"defense news|world nuclear news|canary media|power|aviation week|flightglobal|railway gazette)", re.I)
def score(x):
    t, s, k = x['title'], x.get('source') or '', x['kind']
    sc = {'T1': 3, 'T2': 2}.get(x.get('tier'), 0) + (1 if k == 'komunikat' else 0)
    if GOOD_SRC.search(s): sc += 2
    if WEAK_SRC.search(s): sc -= 2
    sc += 2 * min(2, len(PLUS.findall(t)))
    if re.search(r'\d', t): sc += 1
    sc -= 3 * min(2, len(MINUS.findall(t)))
    return sc
LIMIT = {'cat': 18, 'komunikat': 15, 'pl': 12}
RESEARCH = ['07:21', '15:51']  # godziny researchu (czas polski)
WAW = ZoneInfo('Europe/Warsaw')
d = json.load(open('feeds/latest.json', encoding='utf-8'))
now = datetime.datetime.fromisoformat(d['generated']).astimezone(WAW)
slots = [now.replace(hour=int(h), minute=int(m), second=0, microsecond=0) - datetime.timedelta(days=dd)
         for dd in (0, 1) for h, m in (r.split(':') for r in RESEARCH)]
since = max(s for s in slots if s <= now)
def is_new(x):
    t = x.get('seen') or x.get('published')
    return bool(t) and datetime.datetime.fromisoformat(t) >= since
pool = [x for x in d['items'] if not (NOISE.search(x['title']) or NOISE.search(x.get('source') or ''))]
for x in pool: x['_sc'] = score(x); x['_n'] = is_new(x)
STOP = set('that this with from have will into after over about their they been were what when which more than first just could would says said year years new news nasa'.split())
def toks(t): return {w for w in re.findall(r"[a-ząćęłńóśźż0-9']{4,}", t.lower()) if w not in STOP}
# Ten sam news z wielu redakcji -> jedna pozycja (najlepiej oceniona) z liczba redakcji r (sygnal "goracego tematu").
pool.sort(key=lambda x: -x['_sc'])
stories = []
for x in pool:
    tk = toks(x['title'])
    for st in stories:
        inter = len(tk & st['tk'])
        if tk and inter >= 3 and inter / min(len(tk), len(st['tk'])) >= 0.4:
            st['srcs'].add(x.get('source') or ''); st['x']['_n'] = st['x']['_n'] or x['_n']; break
    else:
        stories.append({'x': x, 'tk': tk, 'srcs': {x.get('source') or ''}})
pool = []
for st in stories:
    st['x']['_r'] = len(st['srcs']); st['x']['_sc'] += min(3, st['x']['_r'] - 1) if st['x']['_sc'] >= 2 else 0; pool.append(st['x'])
pool.sort(key=lambda x: (not x['_n'], -x['_sc'], ''))  # nowe najpierw, potem najlepiej ocenione (stabilnie: od najnowszych)
out, per = [], {}
for x in pool:
    k = x['kind'].split(':')[0]
    grp = k if k in ('komunikat', 'pl') else 'cat:' + x['cat']
    if x['_sc'] < 0 and k not in ('pl',): continue  # wyraznie slabe naglowki nie trafiaja do Claude
    if per.get(grp, 0) >= LIMIT.get(grp if grp in LIMIT else 'cat'): continue
    per[grp] = per.get(grp, 0) + 1
    o = {'cat': x['cat'], 'kind': x['kind'], 't': x['title'], 's': x['source'], 'at': (x.get('published') or '')[:16],
         'n': 1 if x['_n'] else 0, 'sc': x['_sc']}
    if x['_r'] > 1: o['r'] = x['_r']
    if x.get('tier'): o['tr'] = x['tier']
    out.append(o)
json.dump({'generated': d['generated'], 'since': since.astimezone(datetime.timezone.utc).isoformat()[:16],
           'count': len(out), 'new': sum(o['n'] for o in out), 'from': d['count'], 'items': out},
          open('feeds/digest.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('digest', len(out), 'z', d['count'], '; nowe od', since.isoformat()[:16], ':', sum(o['n'] for o in out))

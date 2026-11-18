# Pobiera swieze naglowki dla researchu TechnoGLOBAL i zapisuje feeds/latest.json (pula z ostatnich 30 h).
# 18.11.2026 (decyzja Kamila): precyzyjne zapytania z wykluczeniami, zapytania tylko w sprawdzonych redakcjach,
# kanaly RSS zrodel pierwotnych i redakcji z config/sources. Ocena naglowkow robi digest.py.
import json, re, html, time, datetime, urllib.request, urllib.parse, email.utils, os
UA = 'Mozilla/5.0 (TechnoGLOBAL feeds; +https://technoglobal.pl)'
GN = 'https://news.google.com/rss/search?q=%s&hl=%s&gl=%s&ceid=%s'
EN = ('en-US', 'US', 'US:en')
NEG = ' -stocks -shares -investors -earnings'
CATS = {
    'energetyka': '("nuclear reactor" OR fusion OR "energy storage" OR "solid-state battery" OR "green hydrogen" OR "solar farm" OR "offshore wind" OR geothermal OR "power plant") (first OR record OR unveils OR breakthrough OR largest OR "begins operation" OR prototype)' + NEG + ' -treaty -sanctions -weapons',
    'przemysl': '("humanoid robot" OR "industrial robot" OR gigafactory OR "chip plant" OR "3D printing" OR "additive manufacturing" OR "robotic") (unveils OR first OR record OR launches OR breakthrough OR prototype)' + NEG,
    'transport': '("electric aircraft" OR eVTOL OR "high-speed rail" OR maglev OR "hydrogen train" OR "electric ship" OR "autonomous ship" OR "self-driving" OR "flying car") (first OR record OR unveils OR test OR prototype OR launches)' + NEG + ' -killed -crash -injured',
    'kosmos': '(rocket OR spacecraft OR satellite OR telescope OR "space station" OR asteroid OR lunar OR Mars) (launch OR first OR discovers OR images OR landing OR mission)' + NEG + ' -invest -horoscope -astrology',
    'ai-it': '("AI model" OR supercomputer OR "quantum computer" OR "quantum computing" OR "AI chip" OR "brain-computer") (unveils OR breakthrough OR record OR first OR launches)' + NEG + ' -ordinance -zoning -residents -lawsuit -lawmakers',
    'budownictwo': '("longest bridge" OR "tallest building" OR "tunnel boring" OR megaproject OR "3D-printed building" OR "world\'s largest" construction OR "dam construction") (completed OR opens OR record OR construction)' + NEG + ' -climber -arrested',
    'militaria': '(drone OR "fighter jet" OR "missile defense" OR warship OR "laser weapon" OR hypersonic OR "military robot") (unveils OR "first flight" OR prototype OR test OR record OR "new")' + NEG + ' -killed -injured -attack -strike -police -prison -shot',
    'nauka': '("published in Nature" OR "published in Science" OR "scientists discover" OR "researchers develop" OR physicists OR "new material" OR breakthrough)' + NEG + ' -supplement -diet -horoscope',
}
# Google News tylko w sprawdzonych redakcjach (T2 z config/sources + kilka branzowych); kategoria z klasyfikatora.
TRUSTED = [
    ['interestingengineering.com', 'newatlas.com', 'techxplore.com', 'phys.org', 'spectrum.ieee.org', 'technologyreview.com', 'arstechnica.com'],
    ['spacenews.com', 'nasaspaceflight.com', 'space.com', 'electrek.co', 'electrive.com', 'therobotreport.com', 'newscientist.com'],
    ['twz.com', 'breakingdefense.com', 'defensenews.com', 'world-nuclear-news.org', 'canarymedia.com', 'powermag.com', 'newcivilengineer.com', 'globalconstructionreview.com'],
]
WIRES = '(site:businesswire.com OR site:prnewswire.com OR site:globenewswire.com) (reactor OR battery OR aircraft OR rocket OR satellite OR robot OR chip OR bridge OR drone) -"market size" -"market report" -appoints -"board of directors" -acquisition -earnings -dividend -webinar'
PL = '("polscy naukowcy" OR "naukowcy odkryli" OR "polska firma" OR "polski satelita" OR "elektrownia jądrowa" OR robot OR rakieta OR CPK OR "magazyn energii" OR "nowa technologia") -wernisaż -wystawa -koncert -horoskop -promocja -makabryczne -prokuratura -policja -zwłoki'
# Kanaly RSS: (id, tier, kategoria albo '*' = klasyfikator, url)
RSS = [
    ('nasa', 'T1', 'kosmos', 'https://www.nasa.gov/news-release/feed/'),
    ('eso', 'T1', 'kosmos', 'https://www.eso.org/public/news/feed/'),
    ('esa', 'T1', 'kosmos', 'https://www.esa.int/rssfeed/TopNews|https://www.esa.int/rssfeed/Our_Activities/Space_Science|https://www.esa.int/rssfeed/Our_Activities/Space_Engineering_Technology'),
    ('nvidia', 'T1', 'ai-it', 'https://nvidianews.nvidia.com/releases.xml'),
    ('deepmind', 'T1', 'ai-it', 'https://deepmind.google/blog/rss.xml'),
    ('openai', 'T1', 'ai-it', 'https://openai.com/news/rss.xml'),
    ('nature', 'T1', 'nauka', 'https://www.nature.com/nature.rss'),
    ('mit', 'T1', '*', 'https://news.mit.edu/rss/research'),
    ('sciencedaily', 'T2', '*', 'https://www.sciencedaily.com/rss/top/technology.xml'),
    ('phys-org', 'T2', '*', 'https://phys.org/rss-feed/'),
    ('techxplore', 'T2', '*', 'https://techxplore.com/rss-feed/'),
    ('quanta', 'T2', 'nauka', 'https://www.quantamagazine.org/feed/'),
    ('mittr', 'T2', 'ai-it', 'https://www.technologyreview.com/feed/'),
    ('ieee-spectrum', 'T2', '*', 'https://spectrum.ieee.org/feeds/feed.rss'),
    ('ie', 'T2', '*', 'https://interestingengineering.com/feed'),
    ('newatlas', 'T2', '*', 'https://newatlas.com/index.rss'),
    ('robot-report', 'T2', 'przemysl', 'https://www.therobotreport.com/feed/'),
    ('electrive', 'T2', 'transport', 'https://www.electrive.com/feed/'),
    ('spacenews', 'T2', 'kosmos', 'https://spacenews.com/feed/'),
    ('nsf', 'T2', 'kosmos', 'https://www.nasaspaceflight.com/feed/'),
    ('twz', 'T2', 'militaria', 'https://www.twz.com/feed'),
    ('breaking-def', 'T2', 'militaria', 'https://breakingdefense.com/feed/'),
    ('power-mag', 'T2', 'energetyka', 'https://www.powermag.com/feed/'),
    ('wnn', 'T2', 'energetyka', 'https://www.world-nuclear-news.org/rss'),
    ('constr-dive', 'T2', 'budownictwo', 'https://www.constructiondive.com/feeds/news/'),
]
# Klasyfikator kategorii dla pozycji '*' (pierwsze trafienie wygrywa).
CLASS = [
    ('militaria', r'\b(military|defen[cs]e|missile|army|navy|air force|fighter jet|warship|weapon|pentagon|hypersonic|submarine|artillery|anti-drone)'),
    ('kosmos', r'\b(space\b|spacecraft|rocket|satellite|orbit|nasa|esa\b|spacex|telescope|asteroid|lunar|moon\b|mars\b|astronaut|galaxy|planet|star\b|stars\b)'),
    ('ai-it', r'\b(ai\b|artificial intelligence|machine learning|neural|quantum|chip|semiconductor|supercomputer|algorithm|computer|software|llm|humanoid)'),
    ('transport', r'\b(aircraft|plane|aviation|airline|train|rail|ship|vessel|car\b|cars\b|vehicle|ev\b|evs\b|evtol|truck|bus\b|e-bike|robotaxi)'),
    ('energetyka', r'\b(energy|solar|wind|nuclear|reactor|fusion|battery|batteries|grid|hydrogen|power plant|geothermal|photovoltaic)'),
    ('budownictwo', r'\b(bridge|tunnel|building|skyscraper|construction|concrete|cement|dam\b|architecture)'),
    ('przemysl', r'\b(robot|factory|manufactur|industrial|3d print|steel|automation|drone)'),
]
MAX_AGE_H = 30

def classify(title, default):
    if default != '*': return default
    t = title.lower()
    for cat, rx in CLASS:
        if re.search(rx, t): return cat
    return 'nauka'

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'replace')

def parse(xml, cat, kind, tier=None):
    out = []
    blocks = re.findall(r'<item[ >].*?</item>', xml, re.S) or re.findall(r'<entry[ >].*?</entry>', xml, re.S)
    for it in blocks:
        g = lambda tag: (re.search(r'<%s[^>]*>(.*?)</%s>' % (tag, tag), it, re.S) or [None, ''])[1]
        title = html.unescape(re.sub(r'<!\[CDATA\[|\]\]>|<[^>]+>', '', g('title'))).strip()
        if not title: continue
        src = html.unescape(re.sub(r'<!\[CDATA\[|\]\]>', '', g('source'))).strip()
        if src and title.endswith(' - ' + src): title = title[: -len(src) - 3]
        dt = None
        for tag in ('pubDate', 'dc:date', 'published', 'updated'):
            v = re.sub(r'<!\[CDATA\[|\]\]>', '', g(tag)).strip()
            if not v: continue
            try: dt = email.utils.parsedate_to_datetime(v)
            except Exception:
                try: dt = datetime.datetime.fromisoformat(v.replace('Z', '+00:00'))
                except Exception: dt = None
            if dt: break
        if dt and dt.tzinfo is None: dt = dt.replace(tzinfo=datetime.timezone.utc)
        link = html.unescape(re.sub(r'<!\[CDATA\[|\]\]>', '', g('link'))).strip() or (re.search(r'<link[^>]+href="([^"]+)"', it) or [None, ''])[1]
        x = {'cat': classify(title, cat), 'kind': kind, 'title': title, 'source': src or kind.split(':')[-1], 'link': link,
             'published': dt.astimezone(datetime.timezone.utc).isoformat() if dt else None}
        if tier: x['tier'] = tier
        out.append(x)
    return out

def main():
    now = datetime.datetime.now(datetime.timezone.utc); items = []; status = {}
    gq = lambda q, lang=EN: GN % (urllib.parse.quote(q + ' when:1d'), *lang)
    jobs = [(c, 'news', gq(q), None) for c, q in CATS.items()]
    jobs += [('*', 'redakcja', gq(' OR '.join('site:' + s for s in grp)), 'T2') for grp in TRUSTED]
    jobs += [('*', 'komunikat', gq(WIRES), None), ('*', 'pl', gq(PL, ('pl', 'PL', 'PL:pl')), None)]
    jobs += [(c, 'rss:' + i, u, t) for i, t, c, u in RSS]
    for n, (cat, kind, url, tier) in enumerate(jobs):
        key = (cat + '/' if not kind.startswith('rss') else '') + kind + ('#%d' % n if kind == 'redakcja' else '')
        try:
            err = None
            for u in url.split('|'):  # kilka adresow zapasowych kanalu
                try: xml = get(u); err = None; break
                except Exception as e: err = e
            if err: raise err
            got = parse(xml, cat, kind, tier)
            if kind == 'pl':
                for x in got: x['cat'] = '*'
            if kind == 'komunikat':
                for x in got: x['cat'] = classify(x['title'], '*')
            items += got; status[key] = len(got)
        except Exception as e:
            status[key] = 'blad: %s' % str(e)[:80]
        time.sleep(1.5)
    prev = []
    try:
        old = json.load(open('feeds/latest.json', encoding='utf-8'))
        for x in old.get('items', []):
            if old.get('v', 1) < 2 and x.get('kind') == 'news': continue  # jednorazowo: stare, zbyt ogolne zapytania
            if old.get('v', 1) < 3 and x.get('kind') == 'pl': continue  # jednorazowo: stare zapytanie PL
            x.setdefault('seen', old.get('generated')); prev.append(x)
    except Exception:
        pass
    nowiso = now.isoformat()
    key = lambda x: re.sub(r'\W+', ' ', x['title'].lower())[:80]
    pool = {}
    for x in prev: pool.setdefault(key(x), x)
    for x in items:
        k = key(x)
        if k not in pool:
            x['seen'] = nowiso; pool[k] = x
        elif x['kind'].startswith(('rss', 'redakcja')) and not pool[k]['kind'].startswith(('rss', 'redakcja')):
            x['seen'] = pool[k].get('seen', nowiso); pool[k] = x  # lepsze zrodlo tego samego naglowka
    star = {'rss:' + i for i, t, c, u in RSS if c == '*'}
    for x in pool.values():  # klasyfikacja zawsze aktualnymi regulami
        if x['kind'] in star or x['kind'] in ('redakcja', 'komunikat'): x['cat'] = classify(x['title'], '*')
    fresh = []
    for x in pool.values():
        ts = x.get('published') or x.get('seen')
        if ts and (now - datetime.datetime.fromisoformat(ts)).total_seconds() / 3600 > MAX_AGE_H: continue
        fresh.append(x)
    fresh.sort(key=lambda x: x.get('published') or x.get('seen') or '', reverse=True)
    if prev and set(map(key, fresh)) == set(map(key, prev)):
        print(json.dumps({'count': len(fresh), 'zmiany': 0, 'status': status}, ensure_ascii=False)); return
    added = sum(1 for x in fresh if x.get('seen') == nowiso)
    os.makedirs('feeds', exist_ok=True)
    json.dump({'v': 3, 'generated': nowiso, 'max_age_h': MAX_AGE_H, 'status': status, 'count': len(fresh), 'added': added, 'items': fresh},
              open('feeds/latest.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({'count': len(fresh), 'added': added, 'status': status}, ensure_ascii=False))

if __name__ == '__main__':
    main()

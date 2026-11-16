# Pobiera swieze naglowki dla researchu TechnoGLOBAL i zapisuje feeds/latest.json.
# Zrodla: Google News RSS (ostatnie 24 h, po kategoriach), serwisy z komunikatami prasowymi, kanaly instytucji.
import json, re, html, time, datetime, urllib.request, urllib.parse, email.utils, os
UA = 'Mozilla/5.0 (TechnoGLOBAL feeds; +https://technoglobal.pl)'
GN = 'https://news.google.com/rss/search?q=%s&hl=%s&gl=%s&ceid=%s'
EN = ('en-US', 'US', 'US:en')
CATS = {
    'energetyka': 'nuclear OR reactor OR "energy storage" OR "power plant" OR hydrogen OR "solar farm" OR "wind farm" OR grid',
    'przemysl': 'factory OR "humanoid robot" OR manufacturing OR "chip plant" OR steel OR automation',
    'transport': 'aircraft OR "electric plane" OR "high-speed rail" OR train OR ship OR "electric vehicle" OR "EV battery"',
    'kosmos': 'rocket OR spacecraft OR satellite OR NASA OR ESA OR SpaceX OR "space station"',
    'ai-it': '"AI model" OR supercomputer OR "quantum computer" OR "data center" OR semiconductor OR chip',
    'budownictwo': 'bridge OR tunnel OR skyscraper OR dam OR megaproject OR "tallest building"',
    'militaria': 'drone OR "fighter jet" OR "missile defense" OR warship OR "military technology"',
    'nauka': '"scientists discover" OR "researchers develop" OR "study finds" OR breakthrough',
}
WIRES = '(site:businesswire.com OR site:prnewswire.com OR site:globenewswire.com) (reactor OR battery OR aircraft OR rocket OR satellite OR robot OR chip OR bridge OR drone)'
PL = 'technologia OR energetyka OR kosmos OR elektrownia OR robot OR satelita'
RSS = {'nasa': 'https://www.nasa.gov/news-release/feed/'}
MAX_AGE_H = 30

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'replace')

def parse(xml, cat, kind):
    out = []
    for it in re.findall(r'<item[ >].*?</item>', xml, re.S):
        g = lambda tag: (re.search(r'<%s[^>]*>(.*?)</%s>' % (tag, tag), it, re.S) or [None, ''])[1]
        title = html.unescape(re.sub(r'<!\[CDATA\[|\]\]>', '', g('title'))).strip()
        src = html.unescape(g('source')).strip()
        if src and title.endswith(' - ' + src): title = title[: -len(src) - 3]
        try: dt = email.utils.parsedate_to_datetime(g('pubDate'))
        except Exception: dt = None
        out.append({'cat': cat, 'kind': kind, 'title': title, 'source': src, 'link': html.unescape(g('link')).strip(),
                    'published': dt.astimezone(datetime.timezone.utc).isoformat() if dt else None})
    return out

def main():
    now = datetime.datetime.now(datetime.timezone.utc); items = []; status = {}
    jobs = [(c, 'news', GN % (urllib.parse.quote(q + ' when:1d'), *EN)) for c, q in CATS.items()]
    jobs += [('*', 'komunikat', GN % (urllib.parse.quote(WIRES + ' when:1d'), *EN)),
             ('*', 'pl', GN % (urllib.parse.quote(PL + ' when:1d'), 'pl', 'PL', 'PL:pl'))]
    jobs += [('kosmos', 'instytucja:' + k, u) for k, u in RSS.items()]
    for cat, kind, url in jobs:
        key = cat + '/' + kind
        try:
            got = parse(get(url), cat, kind); items += got; status[key] = len(got)
        except Exception as e:
            status[key] = 'blad: %s' % e
        time.sleep(2)
    fresh, seen = [], set()
    for x in items:
        if x['published']:
            age = (now - datetime.datetime.fromisoformat(x['published'])).total_seconds() / 3600
            if age > MAX_AGE_H: continue
        k = re.sub(r'\W+', ' ', x['title'].lower())[:80]
        if k in seen: continue
        seen.add(k); fresh.append(x)
    fresh.sort(key=lambda x: x['published'] or '', reverse=True)
    os.makedirs('feeds', exist_ok=True)
    json.dump({'generated': now.isoformat(), 'max_age_h': MAX_AGE_H, 'status': status, 'count': len(fresh), 'items': fresh},
              open('feeds/latest.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({'count': len(fresh), 'status': status}, ensure_ascii=False))

if __name__ == '__main__':
    main()

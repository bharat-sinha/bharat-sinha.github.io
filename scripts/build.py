#!/usr/bin/env python3
"""Build step for GitHub Pages (SEO).

Reads content.json and writes a fully static copy of the site to _site/ :
  - index.html with all content rendered as static HTML (+ title, meta, JSON-LD, canonical)
  - one case-study page per project: projects/<slug>/index.html
  - sitemap.xml and robots.txt generated from "siteUrl" in content.json
index.html in the repo stays the editable template (it contains <!--@key--> markers).
Stdlib only. Run:  python scripts/build.py
"""
import datetime, html, json, os, re, shutil, sys
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, '_site')
SKIP = {'.git', '.github', 'scripts', '_site', 'node_modules', 'README.md', 'SEO-CHECKLIST.md', '.gitignore'}
ICONS = {'chart', 'db', 'code', 'brief'}
TODAY = datetime.date.today().isoformat()


def esc(v):
    return html.escape('' if v is None else str(v), quote=True)


def safe(u):
    return u if re.match(r'^(https?://|images/|/)', u or '', re.I) else '#'


def indian(n):
    s = str(int(n))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ','.join(parts) + ',' + tail


def ico(name):
    return '<svg class="i" aria-hidden="true"><use href="#ic-%s"/></svg>' % name


def slug(t):
    return re.sub(r'[^a-z0-9]+', '-', str(t or '').lower()).strip('-')[:60].rstrip('-') or 'project'


def slugs(projects):
    used, out = set(), []
    for p in projects:
        s = n = slug(p.get('title'))
        i = 2
        while n in used:
            n = '%s-%d' % (s, i)
            i += 1
        used.add(n)
        out.append(n)
    return out


def trim(text, n=158):
    text = ' '.join(str(text).split())
    if len(text) <= n:
        return text
    return text[:n].rsplit(' ', 1)[0].rstrip(',;:') + '...'


def article(word):
    return 'an' if word[:1].lower() in 'aeiou' else 'a'


def block(s, key, inner):
    pat = re.compile(r'(<!--@%s-->)(.*?)(<!--/@%s-->)' % (key, key), re.S)
    if not pat.search(s):
        sys.exit('Template marker missing: ' + key)
    return pat.sub(lambda m: m.group(1) + inner + m.group(3), s, count=1)


def meta(s, attr, name, value):
    pat = re.compile(r'(<meta %s="%s" content=")[^"]*(")' % (attr, re.escape(name)))
    return pat.sub(lambda m: m.group(1) + esc(value) + m.group(2), s, count=1)


def img_markup(p, sizes, base='', cls=''):
    """<img> for a project screenshot: WebP/JPEG srcset (960w + 1600w), descriptive alt, full-size for the lightbox."""
    full, small = safe(p['image']), safe(p['imageSmall']) if p.get('imageSmall') else ''
    if base:
        full = full if full.startswith('http') else base + full.lstrip('/')
        small = small if (not small or small.startswith('http')) else base + small.lstrip('/')
    use_small = bool(small) and small != '#'
    alt = p.get('imageAlt') or '%s dashboard screenshot' % p.get('title', '')
    return '<img%s src="%s"%s data-full="%s" alt="%s" loading="lazy" decoding="async" onerror="this.remove()">' % (
        cls, esc(small if use_small else full),
        (' srcset="%s 960w, %s 1600w" sizes="%s"' % (esc(small), esc(full), sizes)) if use_small else '', esc(full), esc(alt))


def project(p, sl):
    tags = ''.join('<span>%s</span>' % esc(t) for t in p.get('tags', []))
    btn = '<a class="pill d" href="projects/%s/">Case study</a>' % esc(sl) if p.get('title') else ''
    if p.get('repo'):
        btn += '<a class="pill" href="%s" target="_blank" rel="noopener">%s GitHub</a>' % (esc(safe(p['repo'])), ico('github'))
    if p.get('live'):
        btn += '<a class="pill" href="%s" target="_blank" rel="noopener">Live demo &#8599;</a>' % esc(safe(p['live']))
    media = ''
    if p.get('image'):
        media = ('<a class="shl" href="projects/%s/" style="view-transition-name:pimg-%s" aria-label="Open case study: %s">%s</a>'
                 '<button class="zm" type="button" aria-label="View screenshot full size: %s">%s</button>') % (
            esc(sl), esc(sl), esc(p.get('title')), img_markup(p, '(max-width:900px) 84vw, 520px'), esc(p.get('title')), ico('expand'))
    sub = esc(p.get('subtitle', '')) + (' (%s)' % esc(p['year']) if p.get('year') else '')
    return ('<article class="pc"><div class="sh"><span>Project preview</span>%s</div><div class="pb"><div class="tg">%s</div>'
            '<h3>%s</h3><p class="st">%s</p><dl><div><dt>Problem</dt><dd>%s</dd></div><div><dt>Approach</dt><dd>%s</dd></div>'
            '<div><dt>Impact</dt><dd>%s</dd></div></dl><div class="bt">%s</div></div></article>') % (
        media, tags, esc(p.get('title')), sub, esc(p.get('problem')), esc(p.get('approach')), esc(p.get('impact')), btn)


def hall_html(C):
    return ''.join('<li class="hi"><b>%s</b><span>%s</span><small>%s</small></li>' % (esc(x.get('big')), esc(x.get('label')), esc(x.get('sub')))
                   for x in C.get('hallway', []) if x.get('big'))


def workindex_html(projects, sl):
    out = []
    for i, (p, s) in enumerate(zip(projects, sl)):
        im = p.get('imageSmall') or p.get('image')
        ok = bool(im) and safe(im) != '#'
        out.append('<li><a class="wr" href="projects/%s/"%s><span class="n">%02d</span><span class="t">%s</span><span class="g">%s</span><span class="y">%s</span>%s</a></li>' % (
            esc(s), (' data-prev="%s"' % esc(safe(im))) if ok else '', i + 1, esc(p.get('title')), esc(' \u00b7 '.join(p.get('tags', []))), esc(p.get('year') or ''),
            ('<span class="wpw"><img class="wp" src="%s" alt="" loading="lazy" decoding="async" onerror="this.remove()"></span>' % esc(safe(im))) if ok else ''))
    return ''.join(out)


def counter(prefix, value, suffix, label):
    n = int(value or 0)
    attrs = 'data-n="%d"' % n
    if prefix:
        attrs += ' data-p="%s"' % esc(prefix)
    if suffix:
        attrs += ' data-s="%s"' % esc(suffix)
    return '<b %s>%s%s%s</b><small>%s</small>' % (attrs, esc(prefix), indian(n), esc(suffix), esc(label))


def contact_links(inner, email, social):
    def fix(m):
        a = m.group(0)
        label = re.search(r'<span>(Email|LinkedIn|GitHub|LeetCode)<small>', a)
        if not label:
            return a
        k = label.group(1)
        if k == 'Email':
            href, text = 'mailto:' + email, email
        else:
            url = social.get(k.lower(), '')
            if not url:
                return a
            href, text = safe(url), re.sub(r'^https?://(www\.)?', '', url).rstrip('/')
            if 'rel="me' not in a:
                a = a.replace('rel="noopener"', 'rel="me noopener"', 1)
        a = re.sub(r'href="[^"]*"', lambda _: 'href="%s"' % esc(href), a, count=1)
        return re.sub(r'<small>.*?</small>', lambda _: '<small>%s</small>' % esc(text), a, count=1, flags=re.S)
    return re.sub(r'<a href=.*?</a>', fix, inner, flags=re.S)


def ldjson(data):
    return json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


CASE_CSS = (':root{--am:#ffb347;--mu:#a49f94;--ln:rgba(255,255,255,.12);--e1:cubic-bezier(.76,0,.24,1);--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}'
 '@view-transition{navigation:auto}::view-transition-group(*){animation-duration:.8s;animation-timing-function:var(--e1)}::view-transition-old(root){animation:o .4s ease both}::view-transition-new(root){animation:n .6s ease .1s both}@keyframes o{to{opacity:0}}@keyframes n{from{opacity:0}}'
 '*{box-sizing:border-box;margin:0}html{background:#000;color-scheme:dark}body{font-family:"DM Sans",system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;background:#000;color:#f4efe6;line-height:1.7;-webkit-font-smoothing:antialiased;padding-bottom:130px;overflow-x:clip}'
 'a{color:inherit;text-decoration:none}body::before{content:"";position:fixed;left:50%;top:-18%;width:1000px;height:640px;transform:translate3d(-50%,0,0);background:radial-gradient(closest-side,rgba(255,179,71,.18),transparent);pointer-events:none}'
 '.bars i{position:fixed;left:0;right:0;height:12px;background:#000;z-index:320;pointer-events:none}.bars i:first-child{top:0}.bars i:last-child{bottom:0}'
 '#grain{position:fixed;inset:-50%;z-index:330;pointer-events:none;opacity:.075;background:url("data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'220\' height=\'220\'><filter id=\'n\'><feTurbulence type=\'fractalNoise\' baseFrequency=\'.85\' numOctaves=\'2\' stitchTiles=\'stitch\'/><feColorMatrix type=\'saturate\' values=\'0\'/></filter><rect width=\'100%25\' height=\'100%25\' filter=\'url(%23n)\'/></svg>");animation:g .9s steps(6) infinite;will-change:transform}'
 '@keyframes g{0%{transform:translate3d(0,0,0)}33%{transform:translate3d(2%,-4%,0)}67%{transform:translate3d(4%,1%,0)}100%{transform:translate3d(0,0,0)}}'
 '.lg{position:fixed;top:20px;left:24px;z-index:350;font-weight:700;text-shadow:0 0 18px #000}.i{width:1em;height:1em;flex:none;fill:currentColor}'
 '.cp{position:relative;max-width:980px;margin:0 auto;padding:110px 24px 0}.eb{font:600 .72rem var(--mono);letter-spacing:.24em;text-transform:uppercase;color:var(--am)}'
 'h1{font-family:"Cormorant Garamond",Georgia,"Times New Roman",serif;font-weight:500;line-height:1.02;font-size:clamp(2.4rem,7vw,4.6rem);text-transform:uppercase;margin:10px 0 12px;text-shadow:0 0 70px rgba(255,179,71,.25)}'
 'h2{font:600 .72rem var(--mono);letter-spacing:.22em;text-transform:uppercase;color:var(--am);margin:0 0 12px}.st{color:var(--mu);font-size:1.15rem}'
 '.tg{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}.tg span{border:1px solid rgba(255,179,71,.45);color:var(--am);border-radius:99px;padding:2px 12px;font-size:.78rem;font-weight:600}'
 '.shotl{display:block;margin:26px 0 8px;border-radius:26px;overflow:hidden;border:1px solid var(--ln);box-shadow:0 40px 90px rgba(0,0,0,.7),0 0 70px rgba(255,179,71,.08)}.shot{display:block;width:100%;aspect-ratio:37/20;object-fit:cover;background:#050505}.cap{font-size:.8rem;color:var(--mu);margin:8px 0 26px}'
 '.bento{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:18px 0}.bn{background:linear-gradient(180deg,#0e0e10,#060607);border:1px solid var(--ln);border-radius:24px;padding:24px}.bn p{color:#cfc9bc}.wide{grid-column:1/-1}'
 '.kn{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:0}.kn li{border:1px solid rgba(255,179,71,.3);border-radius:18px;padding:16px 18px;font-weight:600;background:rgba(255,179,71,.05)}'
 '.bt{display:flex;flex-wrap:wrap;gap:12px;margin:26px 0}.pill{display:inline-flex;gap:8px;align-items:center;border:1px solid rgba(255,255,255,.28);border-radius:99px;padding:12px 24px;font-size:.76rem;font-weight:600;letter-spacing:.09em;text-transform:uppercase;background:rgba(255,255,255,.04)}.pill.d{background:var(--am);color:#000;border-color:var(--am)}'
 'ul.rl{list-style:none;padding:0}ul.rl a{display:block;padding:14px 0;border-bottom:1px solid var(--ln);font-family:"Cormorant Garamond",Georgia,serif;font-size:1.5rem}ul.rl a:hover{color:var(--am)}'
 'aside{margin:30px 0}aside a{color:var(--am)}footer{padding:30px 24px;text-align:center;color:var(--mu);font-size:.85rem}'
 '.dock{position:fixed;left:50%;bottom:calc(16px + env(safe-area-inset-bottom));transform:translate3d(-50%,0,0);z-index:400;display:flex;gap:2px;padding:7px;border-radius:999px;background:rgba(12,12,13,.72);-webkit-backdrop-filter:blur(18px);backdrop-filter:blur(18px);border:1px solid rgba(255,255,255,.14);box-shadow:0 20px 60px rgba(0,0,0,.65),0 0 44px rgba(255,179,71,.09)}'
 '.dk{display:flex;align-items:center;height:44px;min-width:44px;padding:0 14px;border-radius:999px;color:var(--mu);white-space:nowrap}.dk span{font-size:.82rem;font-weight:600;margin-left:8px}.dk:hover,.dk:focus-visible{background:var(--am);color:#000}'
 ':focus-visible{outline:2px solid var(--am);outline-offset:3px}@media(max-width:760px){.bento{grid-template-columns:1fr}.dk span{display:none}.dk{padding:0 13px}}'
 '@media(prefers-reduced-motion:reduce){#grain{animation:none}@view-transition{navigation:none}}')


def case_page(C, p, sl, slist, plist, url, sprite='', cv='Bharat%20Sinha%20CV.pdf'):
    P, S = C.get('profile', {}), C.get('social', {})
    name, role, loc = P.get('name', ''), P.get('role', ''), P.get('location', '')
    title = p.get('title', '')
    page_url = '%sprojects/%s/' % (url, sl)
    page_title = '%s | %s' % (title, name)
    if len(page_title) > 66:
        page_title = title
    desc = trim('%s %s %s' % (title + ':', p.get('problem', ''), p.get('impact', '')))
    img = ''
    img_abs = ''
    if p.get('image'):
        img_abs = p['image'] if p['image'].startswith('http') else url + p['image'].lstrip('/')
        rel_full = p['image'] if p['image'].startswith('http') else '../../' + p['image'].lstrip('/')  # relative: works on any host or preview
        img = ('<a class="shotl" href="%s" target="_blank" rel="noopener" style="view-transition-name:pimg-%s">%s</a>'
               '<p class="cap">Dashboard screenshot. Click the image to open it full size.</p>') % (
            esc(rel_full), esc(sl), img_markup(p, '(max-width:860px) 92vw, 940px', base='../../', cls=' class="shot"'))
    og_src = p.get('imageOg') or (p['image'] if re.search(r'\.(jpe?g|png)$', p.get('image') or '', re.I) else '')
    og_abs = (og_src if og_src.startswith('http') else url + og_src.lstrip('/')) if og_src else ''
    tags = ''.join('<span>%s</span>' % esc(t) for t in p.get('tags', []))
    btns = '<a class="pill d" href="%s#projects">All projects</a>' % esc(url)
    if p.get('repo'):
        btns += '<a class="pill" href="%s" target="_blank" rel="noopener">View code on GitHub</a>' % esc(safe(p['repo']))
    if p.get('live'):
        btns += '<a class="pill" href="%s" target="_blank" rel="noopener">Live demo</a>' % esc(safe(p['live']))
    related = ''.join('<li><a href="%sprojects/%s/">%s</a></li>' % (esc(url), esc(sl2), esc(p2.get('title')))
                      for sl2, p2 in zip(slist, plist) if sl2 != sl and p2.get('title'))
    year = str(p.get('year') or '')
    graph = [
        {'@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': url},
            {'@type': 'ListItem', 'position': 2, 'name': 'Projects', 'item': url + '#projects'},
            {'@type': 'ListItem', 'position': 3, 'name': title}]},
        {'@type': 'Article', 'headline': title[:110], 'description': desc, 'inLanguage': 'en-IN',
         'author': {'@type': 'Person', '@id': url + '#person', 'name': name, 'url': url},
         'datePublished': year if re.fullmatch(r'\d{4}', year) else TODAY, 'dateModified': TODAY,
         'mainEntityOfPage': page_url, 'keywords': ', '.join(p.get('tags', []))}]
    if img_abs:
        graph[1]['image'] = [img_abs]
    hl = [h for h in (p.get('highlights') or []) if h]
    key = ('<div class="bn wide"><h2>Key numbers</h2><ul class="kn">%s</ul></div>' % ''.join('<li>%s</li>' % esc(h) for h in hl)) if hl else ''
    tl = [x for x in p.get('tags', []) if x]
    tools = ('<div class="bn wide"><h2>Tools used</h2><p>This %s project was built with %s.</p></div>' % (
        esc(role.lower()), esc(', '.join(tl[:-1]) + ' and ' + tl[-1] if len(tl) > 1 else ''.join(tl)))) if tl else ''
    ic = lambda n: '<svg class="i" aria-hidden="true"><use href="#ic-%s"/></svg>' % n
    t = '''<!DOCTYPE html>
<html lang="en-IN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>@@TITLE@@</title><meta name="description" content="@@DESC@@"><meta name="theme-color" content="#000000">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
<link rel="canonical" href="@@URL@@"><meta name="author" content="@@NAME@@">
<meta property="og:type" content="article"><meta property="og:site_name" content="@@NAME@@ Portfolio"><meta property="og:locale" content="en_IN">
<meta property="og:title" content="@@TITLE@@"><meta property="og:description" content="@@DESC@@"><meta property="og:url" content="@@URL@@">
<meta property="og:image" content="@@OG@@"><meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="@@TITLE@@"><meta name="twitter:description" content="@@DESC@@"><meta name="twitter:image" content="@@OG@@">
<link rel="manifest" href="@@SITE@@manifest.webmanifest"><link rel="icon" href="@@SITE@@favicon.ico" sizes="48x48"><link rel="icon" type="image/png" href="@@SITE@@favicon-192.png" sizes="192x192"><link rel="apple-touch-icon" href="@@SITE@@apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<script type="application/ld+json">@@LD@@</script><style>@@CSS@@</style></head>
<body>@@SPRITE@@<div class="bars" aria-hidden="true"><i></i><i></i></div><div id="grain" aria-hidden="true"></div>
<a class="lg" href="@@SITE@@">@@NAME@@</a>
<main class="cp"><article><p class="eb">Data analytics case study@@YEAR@@</p><h1>@@H1@@</h1><p class="st">@@SUB@@</p><div class="tg">@@TAGS@@</div>@@IMG@@
<div class="bento"><div class="bn"><h2>The problem</h2><p>@@PROB@@</p></div><div class="bn"><h2>My approach</h2><p>@@APPR@@</p></div><div class="bn"><h2>The impact</h2><p>@@IMP@@</p></div>@@KEY@@@@TOOLS@@</div>
<div class="bt">@@BTNS@@</div>@@REL@@
<aside class="bn"><h2>About the analyst</h2><p>@@NAME@@ is @@ART@@ @@ROLE@@ based in @@LOC@@. @@SUBLINE@@ <a href="@@SITE@@">See the full portfolio</a> or <a href="@@SITE@@#contact">get in touch</a>.</p></aside>
</article></main><footer>&copy; @@Y@@ @@NAME@@ | <a href="@@LI@@" rel="me">LinkedIn</a> | <a href="@@GH@@" rel="me">GitHub</a></footer>
<nav class="dock" aria-label="Main"><a class="dk" href="@@SITE@@">@@I_HOME@@<span>Home</span></a><a class="dk" href="@@SITE@@#projects">@@I_LAYERS@@<span>Work</span></a><a class="dk" href="@@SITE@@#contact">@@I_MAIL@@<span>Contact</span></a><a class="dk" href="@@SITE@@@@CV@@" download aria-label="Download CV (PDF)">@@I_DL@@<span>CV</span></a></nav>
</body></html>'''
    rep = {'TITLE': esc(page_title), 'DESC': esc(desc), 'URL': esc(page_url), 'NAME': esc(name), 'OG': esc(og_abs or url + 'og-image.png'), 'SITE': esc(url),
           'LD': ldjson({'@context': 'https://schema.org', '@graph': graph}), 'CSS': CASE_CSS, 'SPRITE': sprite, 'YEAR': (' | ' + esc(year)) if year else '',
           'H1': esc(title), 'SUB': esc(p.get('subtitle')), 'TAGS': tags, 'IMG': img, 'PROB': esc(p.get('problem')), 'APPR': esc(p.get('approach')),
           'IMP': esc(p.get('impact')), 'BTNS': btns, 'KEY': key, 'TOOLS': tools,
           'REL': ('<div class="bn wide"><h2>More data analytics projects</h2><ul class="rl">%s</ul></div>' % related) if related else '',
           'ART': article(role), 'ROLE': esc(role), 'LOC': esc(loc), 'SUBLINE': esc(P.get('sub')), 'Y': TODAY[:4], 'CV': cv,
           'LI': esc(safe(S.get('linkedin', '#'))), 'GH': esc(safe(S.get('github', '#'))),
           'I_HOME': ic('home'), 'I_LAYERS': ic('layers'), 'I_MAIL': ic('mail'), 'I_DL': ic('dl')}
    for k, v in rep.items():
        t = t.replace('@@%s@@' % k, v)
    return t


def resolve_site(C):
    """Pick the public site URL: CNAME (custom domain) > detected GitHub Pages URL > content.json siteUrl."""
    cn = os.path.join(ROOT, 'CNAME')
    if os.path.exists(cn):
        words = open(cn, encoding='utf-8').read().split()
        if words:
            return 'https://%s/' % words[0], 'CNAME file'
    configured = (C.get('siteUrl') or '').strip()
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    if '/' in repo and (not configured or re.match(r'https?://[^/]*\.github\.io', configured)):
        owner, name = repo.split('/', 1)
        owner = owner.lower()
        det = 'https://%s.github.io/' % owner if name.lower() == owner + '.github.io' else 'https://%s.github.io/%s/' % (owner, name)
        return det, 'detected from GITHUB_REPOSITORY'
    if configured:
        return configured if configured.endswith('/') else configured + '/', 'content.json siteUrl'
    return 'https://example.github.io/', 'fallback (set siteUrl in content.json)'


LEVELS = {'learning': 40, 'working knowledge': 60, 'proficient': 75, 'strong': 85, 'expert': 95}


def levels_html(C):
    out = []
    for i, x in enumerate([x for x in C.get('skillLevels', []) if x.get('name')]):
        lv = str(x.get('level') or '')
        v = LEVELS.get(lv.lower(), 60)
        out.append('<div class="lc rv" style="--d:%ss;--v:%d%%;--s:%s"><div class="lt"><b>%s</b><span class="lvl">%s</span></div>'
                   '<div class="bar" aria-hidden="true"><i style="--i:%d"></i></div><p>%s</p></div>' % (
                       round(i * 0.08, 2), v, round(v / 100, 2), esc(x['name']), esc(lv), i, esc(x.get('note', ''))))
    return ''.join(out)


def top_skills(C, n=4):
    flat = [x for g in C.get('skills', []) for x in g.get('items', [])]
    pri = [x for x in ('Advanced Excel', 'Excel', 'SQL', 'Power BI', 'Python', 'Tableau', 'Power Query') if x in flat]
    out = pri[:n]
    for x in flat:
        if len(out) >= n:
            break
        if x not in out:
            out.append(x)
    return out


def verify_tags(C):
    g, m = re.sub(r'[^A-Za-z0-9_-]', '', C.get('googleVerification', '') or ''), re.sub(r'[^A-Za-z0-9_-]', '', C.get('bingVerification', '') or '')
    return ('<meta name="google-site-verification" content="%s">' % g if g else '') + ('<meta name="msvalidate.01" content="%s">' % m if m else '')


def build():
    C = json.load(open(os.path.join(ROOT, 'content.json'), encoding='utf-8'))
    P, S, M = C.get('profile', {}), C.get('social', {}), C.get('metrics', {})
    url, url_src = resolve_site(C)
    print('Site URL:', url, '(%s)' % url_src)
    projects = [p for p in C.get('projects', []) if p.get('title')]
    sl = slugs(projects)
    s = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    name, role, loc, email = P.get('name', ''), P.get('role', ''), P.get('location', ''), P.get('email', '')

    cv_href = quote(C.get('cvFile') or 'Bharat Sinha CV.pdf')
    s = s.replace('Bharat%20Sinha%20CV.pdf', cv_href)
    s = block(s, 'verify', verify_tags(C))
    s = block(s, 'levels', levels_html(C))
    s = block(s, 'hall', hall_html(C))
    s = block(s, 'workindex', workindex_html(projects, sl))
    s = block(s, 'logo', esc(name))
    s = block(s, 'loader', esc('%s | %s' % (name, role)))
    s = block(s, 'eyebrow', esc(P.get('eyebrow')))
    s = block(s, 'headline', esc(P.get('headline')))
    s = block(s, 'sub', esc(P.get('sub')))
    s = block(s, 'statement', esc(P.get('statement')))
    s = block(s, 'summary', esc(P.get('summary')))
    s = block(s, 'footername', esc(name))
    s = block(s, 'abouth', esc('About %s, %s' % (name, role)))
    s = block(s, 'hire', esc('Hire %s %s' % (article(role), role.lower())))
    s = block(s, 'ticket', counter(M.get('ticketPrefix'), M.get('ticketValue'), M.get('ticketSuffix'), M.get('ticketLabel')))
    s = block(s, 'circle', counter(M.get('circlePrefix'), M.get('circleValue'), M.get('circleSuffix'), M.get('circleLabel')))
    s = block(s, 'projects', '\n  '.join(project(p, x) for p, x in zip(projects, sl)))
    s = block(s, 'faq', ''.join('<details class="rv"><summary>%s</summary><p>%s</p></details>' % (esc(x.get('q')), esc(x.get('a'))) for x in C.get('faq', [])))
    s = block(s, 'skills', ''.join(
        '<div class="sk rv" style="--d:%ss"><h3>%s%s</h3><div class="ch">%s</div></div>' % (
            round(i * 0.08, 2), ico(g.get('icon') if g.get('icon') in ICONS else 'chart'), esc(g.get('title')),
            ''.join('<span>%s</span>' % esc(x) for x in g.get('items', [])))
        for i, g in enumerate(C.get('skills', []))))
    s = block(s, 'experience', ''.join(
        '<div class="it rv"><b>%s</b><small>%s%s</small>%s</div>' % (
            esc(x.get('role')), esc(x.get('org')), (' | ' + esc(x['period'])) if x.get('period') else '',
            ('<ul>%s</ul>' % ''.join('<li>%s</li>' % esc(b) for b in x['bullets'])) if x.get('bullets') else '')
        for x in C.get('experience', [])))
    s = block(s, 'education', ''.join(
        '<div class="it rv"><b>%s</b><small>%s</small></div>' % (esc(x.get('title')), esc(x.get('sub', ''))) for x in C.get('education', []))
        + ('<p class="rv">Languages: %s</p>' % esc(C['languages']) if C.get('languages') else ''))
    gh = S.get('github')
    if gh:
        s = re.sub(r'(<!--@endlink--><a [^>]*?href=")[^"]*(")', lambda m: m.group(1) + esc(safe(gh)) + m.group(2), s, count=1)
    m = re.search(r'<!--@contactlinks-->(.*?)<!--/@contactlinks-->', s, re.S)
    s = block(s, 'contactlinks', contact_links(m.group(1), email, S))
    s = re.sub(r'(<p class="lead rv">)[^<]*(</p>)', lambda mm: mm.group(1) + esc(P.get('contactLead')) + mm.group(2), s, count=1)

    # head: title, description, canonical, social cards
    title = '%s in %s | %s Portfolio' % (role, loc, name)
    sk = top_skills(C)
    desc = trim('%s is %s %s in %s skilled in %s. Explore data analytics case studies, projects and experience.' % (
        name, article(role), role, loc, ', '.join(sk[:-1]) + ' and ' + sk[-1] if len(sk) > 1 else ''.join(sk)))
    s = re.sub(r'<title>.*?</title>', lambda _: '<title>%s</title>' % esc(title), s, count=1, flags=re.S)
    s = meta(s, 'name', 'description', desc)
    s = meta(s, 'property', 'og:title', '%s | %s' % (name, role))
    s = meta(s, 'property', 'og:description', desc)
    s = meta(s, 'property', 'og:url', url)
    s = meta(s, 'property', 'og:image', url + 'og-image.png')
    s = meta(s, 'property', 'og:image:alt', '%s, %s' % (name, role))
    s = meta(s, 'name', 'twitter:title', '%s | %s' % (name, role))
    s = meta(s, 'name', 'twitter:description', desc)
    s = meta(s, 'name', 'twitter:image', url + 'og-image.png')
    s = meta(s, 'name', 'author', name)
    s = re.sub(r'(<link rel="canonical" href=")[^"]*(")', lambda mm: mm.group(1) + esc(url) + mm.group(2), s, count=1)

    # JSON-LD (rebuilt from scratch from content.json)
    skills = []
    for g in C.get('skills', []):
        for x in g.get('items', []):
            if x not in skills:
                skills.append(x)
    person = {'@type': 'Person', '@id': url + '#person', 'name': name, 'url': url, 'jobTitle': role,
              'description': trim(P.get('summary', ''), 300), 'email': email,
              'address': {'@type': 'PostalAddress', 'addressLocality': loc, 'addressCountry': 'IN'},
              'hasOccupation': {'@type': 'Occupation', 'name': role, 'occupationLocation': {'@type': 'AdministrativeArea', 'name': loc},
                                'skills': ', '.join(skills[:10])},
              'knowsAbout': skills[:14],
              'sameAs': [u for u in (S.get('linkedin'), S.get('github'), S.get('leetcode')) if u]}
    graph = [{'@type': 'WebSite', '@id': url + '#website', 'url': url, 'name': '%s Portfolio' % name, 'inLanguage': 'en-IN', 'publisher': {'@id': url + '#person'}},
             person,
             {'@type': 'ProfilePage', '@id': url + '#profile', 'url': url, 'name': title, 'inLanguage': 'en-IN', 'dateModified': TODAY,
              'isPartOf': {'@id': url + '#website'}, 'mainEntity': {'@id': url + '#person'}}]
    ld = re.search(r'(<script type="application/ld\+json">\s*)(.*?)(\s*</script>)', s, re.S)
    s = s[:ld.start(2)] + ldjson({'@context': 'https://schema.org', '@graph': graph}) + s[ld.end(2):]

    sm_ = re.search(r'<svg width="0" height="0".*?</svg>', s, re.S)
    sprite = sm_.group(0) if sm_ else ''
    # write _site
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(ROOT, OUT, ignore=lambda d, names: [n for n in names if n in SKIP] if d == ROOT else [])
    open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(s)
    for p, x in zip(projects, sl):
        d = os.path.join(OUT, 'projects', x)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(case_page(C, p, x, sl, projects, url, sprite, cv_href))
    nf = os.path.join(OUT, '404.html')
    if os.path.exists(nf):
        t = open(nf, encoding='utf-8').read().replace('{{SITE}}', url)
        open(nf, 'w', encoding='utf-8').write(t)
    urls = [(url, '1.0')] + [(url + 'projects/%s/' % x, '0.8') for x in sl]
    open(os.path.join(OUT, 'sitemap.xml'), 'w', encoding='utf-8').write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        ''.join('  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>%s</priority>\n  </url>\n' % (esc(u), TODAY, pr) for u, pr in urls) +
        '</urlset>\n')
    open(os.path.join(OUT, 'robots.txt'), 'w', encoding='utf-8').write('User-agent: *\nAllow: /\n\nSitemap: %ssitemap.xml\n' % url)
    print('Built _site/: home + %d case-study pages, %d skill groups, %d FAQs' % (len(sl), len(C.get('skills', [])), len(C.get('faq', []))))


if __name__ == '__main__':
    build()

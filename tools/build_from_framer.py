#!/usr/bin/env python3
"""
Turn a raw export of the Ceacio Framer site into a clean, self-hosted static site.

The raw export is the folder layout produced when the live site was captured:

    raw/
      pages/index.html, about.html, services.html, 404.html   (Framer's server-rendered HTML)
      framerusercontent/images/...                             (images)
      framerusercontent/assets/...                             (fonts, favicon, social image)
      framerusercontent/third-party-assets/fontshare/...       (Fontshare fonts)
      framerusercontent/sites/<siteId>/*.mjs                   (Framer runtime + page code)

What the build does:
  * copies every image, font and script under /assets/framer/ so nothing loads from Framer's CDN
  * rewrites every https://framerusercontent.com/... reference in HTML and JS to those local paths
  * keeps Framer's runtime so animations, the mobile menu and page transitions behave like the original
  * removes Framer analytics, the "Made in Framer" badge and the Framer editor bar
  * points canonical / Open Graph URLs at SITE_URL instead of the *.framer.website domain
  * patches three spots in the runtime that parse image URLs, so root-relative paths work

Usage:
    python3 tools/build_from_framer.py <raw-export-dir> <output-dir> [--site-url https://ceacio.com]
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

FRAMER_CDN = "https://framerusercontent.com/"
LOCAL_PREFIX = "/assets/framer/"
# Folders on Framer's CDN that we host ourselves. /modules/ and /cms/ are deliberately left
# alone: the runtime only uses them to build CMS query URLs, which normal browsing never fetches,
# and `new URL(relative, base)` needs an absolute base there.
LOCAL_DIRS = ("images", "assets", "third-party-assets", "sites")
# CMS data files: copied locally, but their URLs are built at runtime (see patch_cms_loader).
COPY_DIRS = LOCAL_DIRS + ("cms",)
FRAMER_DOMAIN = "https://ceacio.framer.website"

# Bugs carried over from the Framer project, fixed in HTML and JS alike.
# "(" and ")" make the section anchor an invalid CSS selector, so the footer link never scrolls to it.
FIXES = {
    "lubricant-diesel-(ago)-supply": "lubricant-diesel-ago-supply",
}

PAGES = {
    "index.html": "/",
    "about.html": "/about",
    "services.html": "/services",
    "404.html": None,
}


def rewrite_cdn_urls(text: str) -> str:
    pattern = re.compile(r"https://framerusercontent\.com/(" + "|".join(LOCAL_DIRS) + r")/")
    text = pattern.sub(lambda m: LOCAL_PREFIX + m.group(1) + "/", text)
    for old, new in FIXES.items():
        text = text.replace(old, new)
    return text


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        sys.exit(f"[patch failed] {label}: expected 1 match, found {count}. "
                 "Framer may have changed its runtime; review the patch list.")
    return text.replace(old, new)


def regex_once(text: str, pattern: str, new: str, label: str, flags=0) -> str:
    matches = re.findall(pattern, text, flags)
    if len(matches) != 1:
        sys.exit(f"[patch failed] {label}: expected 1 match, found {len(matches)}.")
    return re.sub(pattern, lambda _: new, text, count=1, flags=flags)


def remove_element_by_id(html: str, tag: str, element_id: str) -> str:
    """Remove <tag id="element_id">...</tag>, honouring nested tags of the same name."""
    start = html.find(f'<{tag} id="{element_id}"')
    if start == -1:
        return html
    depth = 0
    for m in re.compile(rf"<{tag}\b|</{tag}>").finditer(html, start):
        depth += -1 if m.group(0).startswith("</") else 1
        if depth == 0:
            return html[:start] + html[m.end():]
    sys.exit(f"[html] could not find the end of #{element_id}")


def clean_html(html: str, site_url: str) -> str:
    # Framer editor bar preload (only fires for logged-in Framer users)
    html = regex_once(
        html,
        r'<script>try\{if\(localStorage\.getItem\("__framer_force_showing_editorbar_since"\)\).*?</script>',
        "", "editor bar preload", re.S)
    # Framer analytics
    html = regex_once(html, r'<script[^>]*src="https://events\.framer\.com/[^"]*"[^>]*>\s*</script>',
                      "", "framer analytics")
    # "Made in Framer" badge
    html = remove_element_by_id(html, "div", "__framer-badge-container")
    html = re.sub(r"@supports \(z-index:calc\(infinity\)\)\{#__framer-badge-container\{[^}]*\}\}", "", html)
    html = re.sub(r"#__framer-badge-container\{[^}]*\}", "", html)
    # Generator meta and Framer comments
    html = re.sub(r'<meta name="generator" content="Framer[^"]*">\s*', "", html)
    html = re.sub(r"<!-- Made in Framer[^>]*-->\s*", "", html)
    html = re.sub(r"<!-- Published [^>]*-->\s*", "", html)

    # Canonical, og:url and the 404 link fixer: point at the real domain
    html = html.replace(FRAMER_DOMAIN, site_url)

    # Local assets
    html = rewrite_cdn_urls(html)

    # Social previews need absolute image URLs
    html = re.sub(r'(<meta (?:property|name)="(?:og:image|twitter:image)" content=")(/assets/framer/)',
                  lambda m: m.group(1) + site_url + m.group(2), html)
    return html


def patch_runtime(js_dir: Path, site_url: str) -> None:
    main = next(js_dir.glob("script_main.*.mjs"))
    t = main.read_text(encoding="utf-8")
    # Never load the Framer editor bar from framer.com
    t = regex_once(t, r"EditorBar:E===void 0\?void 0:\(\(\)=>\{.*?return\{default:e\(\)\}\}\)\}\)\(\)",
                   "EditorBar:void 0", "editor bar", re.S)
    # Don't mount the "Made in Framer" badge (its container is removed from the HTML)
    t = regex_once(t, r"\(function\(\)\{\w+&&\w+\(\(\)=>\{\w+\(document\.getElementById\(`__framer-badge-container`\).*?\}\)\}\)\(\)",
                   "", "badge mount", re.S)
    t = replace_once(t, f"siteCanonicalURL:`{FRAMER_DOMAIN}`", f"siteCanonicalURL:`{site_url}`",
                     "canonical URL")
    main.write_text(t, encoding="utf-8")

    # The image helpers call `new URL(src)` without a base, which throws on root-relative paths.
    framer = next(js_dir.glob("framer.*.mjs"))
    t = framer.read_text(encoding="utf-8")
    patches = [
        (r"(if\(!e\|\|!t\?\.src\)return t;let n=new URL\(t\.src)\)", r"\1,document.baseURI)", "srcset helper"),
        (r"(\{try\{let n=new URL\(e)\);return t\?n\.searchParams\.set\(`scale-down-to`",
         r"\1,document.baseURI);return t?n.searchParams.set(`scale-down-to`", "scale-down helper"),
        (r"(return new Promise\(\(t,n\)=>\{try\{new URL\(e)\);let r=new Image",
         r"\1,document.baseURI);let r=new Image", "image preloader"),
    ]
    for pattern, repl, label in patches:
        if len(re.findall(pattern, t)) != 1:
            sys.exit(f"[patch failed] {label}")
        t = re.sub(pattern, repl, t, count=1)
    framer.write_text(t, encoding="utf-8")

    patch_cms_loader(js_dir)


def patch_cms_loader(js_dir: Path) -> None:
    """Make Framer's CMS client read the local .framercms files.

    * The CMS file URLs are built as new URL(`./x.framercms`, `<module url>`).replace('/modules/', '/cms/'),
      so the module base must stay absolute: use the page's own origin.
    * Framer's CDN serves byte ranges from a `?range=a-b,c-d` query parameter. Static hosts ignore query
      strings and return the whole file, so fetch the file once and cut the ranges out locally.
    * Image URLs stored inside CMS records are rewritten to the local copies as they are decoded.
    """
    for f in js_dir.glob("*.mjs"):
        t = f.read_text(encoding="utf-8")
        if "framercms" not in t:
            continue
        n_mod = t.count("`https://framerusercontent.com/modules/")
        t = t.replace("`https://framerusercontent.com/modules/", "`${location.origin}" + LOCAL_PREFIX + "modules/")

        range_fetch = (r"let a=new URL\(e\),o=r\.join\(`,`\);a\.searchParams\.set\(`range`,o\);let s=await (\w+)\(a\);"
                       r"if\(s\.status!==200\)throw Error\(`Request failed: \$\{s\.status\} \$\{s\.statusText\}`\);"
                       r"let c=await s\.arrayBuffer\(\),l=new Uint8Array\(c\);")
        local_slice = (r"let s=await \1(new URL(e,document.baseURI));"
                       r"if(s.status!==200)throw Error(`Request failed: ${s.status} ${s.statusText}`);"
                       r"let __f=new Uint8Array(await s.arrayBuffer()),l=new Uint8Array(i),__p=0;"
                       r"for(let __r of n){l.set(__f.subarray(__r.from,__r.to),__p);__p+=__r.to-__r.from}")
        n_range = len(re.findall(range_fetch, t))
        t = re.sub(range_fetch, local_slice, t)

        json_read = "readJson(){let e=this.readString();return JSON.parse(e)}"
        n_json = t.count(json_read)
        t = t.replace(json_read,
                      "readJson(){let e=this.readString();return JSON.parse(e.replace("
                      r"/https:\/\/framerusercontent\.com\/(images|assets|third-party-assets)\//g,"
                      f'"{LOCAL_PREFIX}$1/"))}}')
        if not (n_mod and n_range and n_json):
            sys.exit(f"[patch failed] CMS loader in {f.name}: modules={n_mod} range={n_range} json={n_json}")
        f.write_text(t, encoding="utf-8")
        print(f"CMS loader patched in {f.name}: {n_mod} file URLs, {n_range} range readers, {n_json} JSON readers")


def build(raw: Path, out: Path, site_url: str) -> None:
    cdn = raw / "framerusercontent"
    assets_out = out / "assets" / "framer"
    if assets_out.exists():
        shutil.rmtree(assets_out)
    for d in COPY_DIRS:
        if (cdn / d).exists():
            shutil.copytree(cdn / d, assets_out / d)

    # Rewrite CDN URLs inside scripts and JSON
    for f in assets_out.rglob("*"):
        if f.suffix in (".mjs", ".js", ".json"):
            f.write_text(rewrite_cdn_urls(f.read_text(encoding="utf-8")), encoding="utf-8")

    site_dirs = list((assets_out / "sites").iterdir())
    if len(site_dirs) != 1:
        sys.exit("expected exactly one Framer site folder")
    patch_runtime(site_dirs[0], site_url)

    for name in PAGES:
        html = (raw / "pages" / name).read_text(encoding="utf-8")
        (out / name).write_text(clean_html(html, site_url), encoding="utf-8")

    # Sitemap + robots for the real domain
    urls = "".join(f"  <url><loc>{site_url}{p if p != '/' else '/'}</loc></url>\n"
                   for p in PAGES.values() if p)
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n",
        encoding="utf-8")
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {site_url}/sitemap.xml\n",
                                    encoding="utf-8")

    # Final check: nothing should still load from Framer's CDN, analytics or editor
    leftovers = []
    for f in list(out.glob("*.html")) + list(assets_out.rglob("*.mjs")):
        text = f.read_text(encoding="utf-8")
        for bad in ("events.framer.com", "framer.com/edit/init.mjs", "__framer-badge-container",
                    FRAMER_DOMAIN):
            if bad in text:
                leftovers.append(f"{f.relative_to(out)}: {bad}")
        for m in re.finditer(r"https://framerusercontent\.com/[\w-]+/", text):
            leftovers.append(f"{f.relative_to(out)}: {m.group(0)}")
    if leftovers:
        sys.exit("Leftover Framer references:\n  " + "\n  ".join(sorted(set(leftovers))))
    print(f"Built {len(PAGES)} pages into {out} (site URL {site_url})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("raw", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--site-url", default="https://ceacio.com")
    a = ap.parse_args()
    build(a.raw, a.out, a.site_url.rstrip("/"))

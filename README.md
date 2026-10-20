# Ceacio website

Static, self-hosted copy of the Ceacio Alliance site originally built in Framer
(`ceacio.framer.website`). It is Framer's own server-rendered HTML plus Framer's runtime, with
every image, font, script and CMS file served from this repo. Animations, the mobile menu, the
FAQ accordion, the sticky "Why choose us" section and page transitions work as they do on Framer.

## What's here

| Path | What it is |
| --- | --- |
| `index.html`, `about.html`, `services.html` | The three pages |
| `404.html` | Not-found page (served automatically by Vercel, Netlify and GitHub Pages) |
| `assets/framer/images/` | Images |
| `assets/framer/assets/`, `assets/framer/third-party-assets/` | Fonts, favicons, social preview image |
| `assets/framer/sites/<id>/` | Framer runtime and page code (`.mjs`) |
| `assets/framer/cms/` | Framer CMS data (the services list) |
| `assets/ceacio.css` | Our own styles: the "What we do at a glance" section and layout fixes on top of Framer's CSS |
| `vercel.json` | Clean URLs (`/about` instead of `/about.html`) and long-lived caching for assets |
| `sitemap.xml`, `robots.txt` | For search engines, pointing at `https://ceacio.com` |
| `tools/build_from_framer.py` | The script that produced all of the above from a raw Framer capture |

## Removed from the Framer version

- Framer analytics (`events.framer.com`)
- The "Made in Framer" badge
- The Framer on-page editor bar (`framer.com/edit`)
- The HTTrack project-index files that were previously in this repo

## Deploying

It's plain static files with no build step. On Vercel, import the repo with framework preset
"Other" and leave the build command empty. Netlify and Cloudflare Pages work the same way. The site
must be served from the root of a domain (not a sub-folder such as `user.github.io/repo/`), because
asset paths start with `/assets/`.

To preview locally, run any static server from the repo root, for example `npx serve .`
(opening `index.html` directly from disk won't work, as browsers block ES modules on `file://`).

## Editing the site

This repo is now the source of truth; the Framer project is no longer in sync with it. Text lives in
two places that must stay identical: the page HTML (what loads first) and the page's Framer module in
`assets/framer/sites/<id>/` (what React renders when it takes over). Change a sentence in only one of
them and React will swap it back or log a hydration error. Search both for the exact sentence and edit
both. New sections can be added the way "What we do at a glance" was: an element rendered with
`dangerouslySetInnerHTML` in the page module, the same markup in the HTML, styles in `assets/ceacio.css`.

## Things to know

- **Domain.** The site's main address is `https://www.ceacio.com` (Vercel redirects `ceacio.com` to it).
  Canonical links, Open Graph tags, structured data, the sitemap, `robots.txt`, `llms.txt` and
  `siteCanonicalURL` in `assets/framer/sites/*/script_main.*.mjs` all use it.
- **SEO.** Each page has its own title, description and 1200×630 header screenshot (`assets/seo/`),
  set in the page HTML and in that page's Framer metadata module (the `description:`/`socialImage:`/`title:`
  fields). JSON-LD in each page's `<head>` (`data-cx-seo`) describes the company, the page, breadcrumbs,
  the FAQ (Home) and the services (Services). `sitemap.xml` lists page images; `llms.txt` summarises the
  business for AI assistants. Image alt text is set in the HTML and modules, and a small `data-cx-alt`
  script fills it in for CMS images. If you change page copy, FAQ answers or services, update these too.
- **Script caching.** Files under `/assets/framer/` are cached by browsers for a year. Never edit a `.mjs`
  file in place: save the change under a new file name and update everything that references it (other
  modules and the HTML pages), or returning visitors keep the old version.
- **Contact form.** Submissions go to augustine.chukwudozie@gmail.com through
  [FormSubmit](https://formsubmit.co) (no backend needed). The first submission from the live domain
  sends an "Activate Form" email to that address; messages are delivered once it's clicked. After
  activation FormSubmit offers a random alias; swap it for the email in the home page module
  (`formsubmit.co/ajax/...`) to keep the address out of the page source. The recipient is set in
  `assets/framer/sites/*/u60X*.mjs`; the request is built by `__cxFormSubmit` in `framer.*.mjs`.
- **Footer social links** were removed until real profiles exist.
- **One fix applied:** the "Lubricant & Diesel (AGO) Supply" anchor contained parentheses, which
  broke the footer link to that section on Framer. It is now `#lubricant-diesel-ago-supply`.

## Re-importing from Framer (overwrites the edits above)

Only if the site is rebuilt in Framer: publish, capture the site again (the four pages' HTML plus
everything they load from `framerusercontent.com`, in the same layout as before), then run:

```bash
python3 tools/build_from_framer.py path/to/raw-capture . --site-url https://ceacio.com
```

The script stops with a clear message if a newer Framer runtime no longer matches one of its patches.

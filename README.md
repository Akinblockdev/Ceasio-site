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

## Things to know

- **Domain.** Canonical links, Open Graph tags, the sitemap and `robots.txt` assume
  `https://ceacio.com`. If the site will live elsewhere, find-and-replace `https://ceacio.com` across
  the HTML, `sitemap.xml`, `robots.txt` and `assets/framer/sites/*/script_main.*.mjs`.
- **Contact form.** The form still posts to Framer's form endpoint. Framer may not accept
  submissions from a non-Framer domain, so test it after deploying and switch it to a form backend
  (Formspree, Basin, a small API route) if submissions don't arrive.
- **Footer social links** were placeholders in the Framer project: "Linkedin" goes to
  `tiktok.com`, "Twitter" to `x.com` and "Instagram" to `instagram.com`. Update them with the real
  profile URLs.
- **One fix applied:** the "Lubricant & Diesel (AGO) Supply" anchor contained parentheses, which
  broke the footer link to that section on Framer. It is now `#lubricant-diesel-ago-supply`.

## Updating from Framer

Edit in Framer, publish, capture the site again (the four pages' HTML plus everything they load from
`framerusercontent.com`, in the same layout as before), then run:

```bash
python3 tools/build_from_framer.py path/to/raw-capture . --site-url https://ceacio.com
```

The script stops with a clear message if a newer Framer runtime no longer matches one of its patches.

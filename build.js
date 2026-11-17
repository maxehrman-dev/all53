// THE 53 build: node build.js [https://your-site.example/]
//  dist/index.html            full page for any static host (loads rosters-current.js, then rosters-alltime.js on demand)
//  dist/the53-single.html     everything inlined, opens from a file or a single-file host like Muse
//  artifact/index.html        the same app as a page fragment for claude.ai artifacts
const fs = require('fs'), path = require('path');
const here = __dirname, dist = path.join(here, 'dist'), art = path.join(here, 'artifact');
const site = (process.argv[2] || '').replace(/\/?$/, process.argv[2] ? '/' : '');
let app = fs.readFileSync(path.join(here, 'src', 'app.html'), 'utf8');
if (site) app = app.replace('var SITE_URL = "";', 'var SITE_URL = ' + JSON.stringify(site) + ';');
const cur = fs.readFileSync(path.join(dist, 'rosters-current.js'), 'utf8');
const all = fs.readFileSync(path.join(dist, 'rosters-alltime.js'), 'utf8');

const desc = 'One NFL team, one clock. Name as many players as you can. Deep cuts buy time. Can you name all 53?';
const img = (site || '') + 'og.png';
const head = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="${desc}">
<meta name="theme-color" content="#07090F">
<meta property="og:type" content="website">
<meta property="og:title" content="THE 53">
<meta property="og:description" content="${desc}">
<meta property="og:image" content="${img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
${site ? `<meta property="og:url" content="${site}">\n<link rel="canonical" href="${site}">` : ''}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="THE 53">
<meta name="twitter:description" content="${desc}">
<meta name="twitter:image" content="${img}">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}</style>
`;
const wrap = body => head + body.replace('<title>THE 53</title>', '<title>THE 53</title>').replace(/\n<div class="sky"/, '\n</head>\n<body>\n<div class="sky"') + '\n</body>\n</html>\n';

fs.writeFileSync(path.join(dist, 'index.html'), wrap(app));
const single = app
  .replace('<script src="rosters-current.js"></script>', '<script>\n' + cur + '</script>\n<script>\n' + all + '</script>')
  .replace('<link rel="icon" href="favicon.svg" type="image/svg+xml">', '');
fs.writeFileSync(path.join(dist, 'the53-single.html'), wrap(single).replace('<link rel="icon" href="favicon.svg" type="image/svg+xml">\n', ''));
fs.mkdirSync(art, { recursive: true });
fs.writeFileSync(path.join(art, 'index.html'), process.env.ARTIFACT_URL && !site ? app.replace('var SITE_URL = "";', 'var SITE_URL = ' + JSON.stringify(process.env.ARTIFACT_URL) + ';') : app);
fs.copyFileSync(path.join(dist, 'rosters-current.js'), path.join(art, 'rosters-current.js'));
fs.copyFileSync(path.join(dist, 'rosters-alltime.js'), path.join(art, 'rosters-alltime.js'));
fs.rmSync(path.join(art, 'img'), { recursive: true, force: true }); fs.rmSync(path.join(art, 'faces'), { recursive: true, force: true });
fs.cpSync(path.join(dist, 'img'), path.join(art, 'img'), { recursive: true });
fs.cpSync(path.join(dist, 'faces'), path.join(art, 'faces'), { recursive: true, filter: f => !/[\\/]faces[\\/]p([\\/]|$)/.test(f) });   /* the preview takes per-team files only */
fs.writeFileSync(path.join(dist, 'favicon.svg'),
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#07090F"/>' +
  '<text x="32" y="45" text-anchor="middle" font-family="Arial Black,Arial,sans-serif" font-weight="900" font-size="34" fill="#E1B04B">53</text></svg>');
fs.writeFileSync(path.join(dist, 'robots.txt'), 'User-agent: *\nAllow: /\n');
for (const f of ['index.html', 'the53-single.html', 'rosters-current.js', 'rosters-alltime.js'])
  console.log(f, fs.statSync(path.join(dist, f)).size);

// Worker del tauler veïnal: router, validación, D1, Turnstile, CORS y cron.
import { MAIL, CATS, LANGS, SLUGS, CAT_NAMES, t, esc, fmtDate, page } from './i18n.js';
import { sendMail } from './mail.js';
import { isBlocked, hasIban, hasCard } from './filter.js';

const DAY = 86400;
const HOUR = 3600;
const LIFETIME = 45 * DAY; // vida de un anuncio
const MAX_RENEWALS = 3;
const MAX_LIVE = 500; // tope de anuncios vivos
const MAIL_PER_DAY = 300; // tope global de correos/día
const REPORTS_TO_HIDE = 3;
const ID_RE = /^[a-z2-7]{12}$/;
const TOKEN_RE = /^[A-Za-z0-9_-]{32,64}$/;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

// ---------- utilidades ----------

const now = () => Math.floor(Date.now() / 1000);

function json(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', ...headers },
  });
}

const fail = (error, status, extra = {}, headers = {}) => json({ error, ...extra }, status, headers);

function html(body, status = 200) {
  return new Response(body, {
    status,
    headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer' },
  });
}

async function sha256hex(s) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

// Comparación en tiempo constante de dos cadenas de la misma longitud.
function timingEqual(a, b) {
  a = String(a);
  b = String(b);
  let diff = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  }
  return diff === 0;
}

// Compara contra un secreto tras hashear ambos (misma longitud, sin fugas por tamaño).
async function secretEqual(given, secret) {
  if (!secret) return false;
  return timingEqual(await sha256hex(String(given ?? '')), await sha256hex(secret));
}

const B32 = 'abcdefghijklmnopqrstuvwxyz234567';
function randomId() {
  const bytes = crypto.getRandomValues(new Uint8Array(8));
  let bits = 0, value = 0, out = '';
  for (const b of bytes) {
    value = (value << 8) | b;
    bits += 8;
    while (bits >= 5) {
      out += B32[(value >>> (bits - 5)) & 31];
      bits -= 5;
    }
  }
  return out.slice(0, 12);
}

function randomToken() {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  let s = '';
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function yyyymmdd(ts = now()) {
  return new Date(ts * 1000).toISOString().slice(0, 10).replace(/-/g, '');
}

async function ipHashes(env, req) {
  const ip = req.headers.get('CF-Connecting-IP') || '0.0.0.0';
  const salt = env.IP_SALT || '';
  const day = (await sha256hex(`${salt}:${ip}:${yyyymmdd()}`)).slice(0, 32);
  const fixed = (await sha256hex(`${salt}:${ip}`)).slice(0, 32);
  return { ip, day, fixed };
}

const emailHash = (env, email) => sha256hex(`${env.IP_SALT || ''}:${email}`);

// Cubo de límite en la tabla `rate`: ventanas fijas (día u hora). true si se permite.
async function rateHit(env, key, limit, window = DAY) {
  const ts = now();
  const reset = (Math.floor(ts / window) + 1) * window;
  const row = await env.DB.prepare(
    `INSERT INTO rate (key, n, reset) VALUES (?1, 1, ?2)
     ON CONFLICT(key) DO UPDATE SET
       n = CASE WHEN reset <= ?3 THEN 1 ELSE n + 1 END,
       reset = CASE WHEN reset <= ?3 THEN ?2 ELSE reset END
     RETURNING n`,
  )
    .bind(key, reset, ts)
    .first();
  return (row?.n ?? 1) <= limit;
}

// Reserva `n` correos del cupo global diario. false si se supera.
async function takeMail(env, n = 1) {
  const key = `mail:global:${yyyymmdd()}`;
  const ts = now();
  const reset = (Math.floor(ts / DAY) + 1) * DAY;
  const row = await env.DB.prepare(
    `INSERT INTO rate (key, n, reset) VALUES (?1, ?4, ?2)
     ON CONFLICT(key) DO UPDATE SET
       n = CASE WHEN reset <= ?3 THEN ?4 ELSE n + ?4 END,
       reset = CASE WHEN reset <= ?3 THEN ?2 ELSE reset END
     RETURNING n`,
  )
    .bind(key, reset, ts, n)
    .first();
  return (row?.n ?? n) <= MAIL_PER_DAY;
}

async function verifyTurnstile(env, token, ip) {
  if (!token || typeof token !== 'string' || token.length > 2048) return false;
  try {
    const r = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ secret: env.TURNSTILE_SECRET, response: token, remoteip: ip }),
    });
    const j = await r.json();
    return j.success === true;
  } catch {
    return false;
  }
}

// ---------- CORS ----------

function allowedOrigins(env) {
  return (env.ALLOWED_ORIGINS || '').split(',').map((s) => s.trim()).filter(Boolean);
}

function corsFor(req, env, pub) {
  const origin = req.headers.get('Origin');
  if (pub) return { ok: true, headers: { 'Access-Control-Allow-Origin': '*' } };
  if (!origin || !allowedOrigins(env).includes(origin)) return { ok: false, headers: {} };
  return { ok: true, headers: { 'Access-Control-Allow-Origin': origin, Vary: 'Origin' } };
}

function preflight(req, env, path) {
  const origin = req.headers.get('Origin');
  const headers = {
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
  };
  if (origin && allowedOrigins(env).includes(origin)) {
    headers['Access-Control-Allow-Origin'] = origin;
    headers.Vary = 'Origin';
  } else if (path === '/posts') {
    headers['Access-Control-Allow-Origin'] = '*';
  }
  return new Response(null, { status: 204, headers });
}

// ---------- caché de GET /posts ----------

function postsCacheKey(url) {
  return new Request(new URL('/posts', url).toString(), { method: 'GET' });
}

async function purgePosts(url) {
  try {
    await caches.default.delete(postsCacheKey(url));
  } catch {
    /* sin caché en local */
  }
}

// ---------- validación ----------

// Limpieza común: NFC, sin caracteres de control, espacios colapsados, recortado.
function clean(s, { multiline = false } = {}) {
  if (typeof s !== 'string') return null;
  let v = s.normalize('NFC').replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f\u200b-\u200f\u2028\u2029\ufeff]/g, '');
  if (multiline) {
    v = v.replace(/\r\n?/g, '\n').replace(/[ \t ]+/g, ' ').replace(/ ?\n ?/g, '\n').replace(/\n{3,}/g, '\n\n');
  } else {
    v = v.replace(/\s+/g, ' ');
  }
  return v.trim();
}

// Comprobaciones de contenido libre: HTML, exceso de URL, IBAN, tarjeta.
function textOk(v) {
  if (/<[a-zA-Z/]/.test(v)) return false;
  if ((v.match(/https?:\/\//gi) || []).length > 2) return false;
  if (hasIban(v) || hasCard(v)) return false;
  return true;
}

// Valida un campo de texto; devuelve el valor limpio o null si no es válido.
function field(raw, min, max, { multiline = false, optional = false, content = true } = {}) {
  if (raw === undefined || raw === null || raw === '') return optional ? '' : null;
  const v = clean(raw, { multiline });
  if (v === null) return null;
  if (v === '' && optional) return '';
  if (v.length < min || v.length > max) return null;
  if (content && !textOk(v)) return null;
  return v;
}

function cleanEmail(raw) {
  if (typeof raw !== 'string') return null;
  const v = raw.trim().toLowerCase();
  if (v.length > 254 || !EMAIL_RE.test(v)) return null;
  return v;
}

// Valida `body` según `spec` = {campo: [min, max, opciones]}; devuelve {data} o {field}.
function validate(body, spec) {
  if (!body || typeof body !== 'object') return { field: 'body' };
  const data = {};
  for (const [name, def] of Object.entries(spec)) {
    const raw = body[name];
    let v;
    if (def.type === 'enum') v = def.values.includes(raw) ? raw : null;
    else if (def.type === 'email') v = cleanEmail(raw);
    else if (def.type === 'id') v = typeof raw === 'string' && ID_RE.test(raw) ? raw : null;
    else if (def.type === 'bool') v = raw === true ? true : null;
    else v = field(raw, def.min ?? 0, def.max, def);
    if (v === null) return { field: name };
    data[name] = v;
  }
  return { data };
}

async function readJson(req) {
  try {
    if (!(req.headers.get('Content-Type') || '').includes('application/json')) return null;
    const txt = await req.text();
    if (txt.length > 16384) return null;
    return JSON.parse(txt);
  } catch {
    return null;
  }
}

async function readForm(req) {
  try {
    const txt = await req.text();
    if (txt.length > 4096) return {};
    return Object.fromEntries(new URLSearchParams(txt));
  } catch {
    return {};
  }
}

// ---------- D1 ----------

const PUBLIC_COLS = 'id, cat, lang, title, body, name, contact, price, created, expires';

const getPost = (env, id) => env.DB.prepare('SELECT * FROM posts WHERE id = ?1').bind(id).first();

// Marca borrado y fija `expires` en el pasado para poder purgarlo a los 7 días.
const markDeleted = (env, id) =>
  env.DB.prepare("UPDATE posts SET status = 'deleted', expires = MIN(COALESCE(expires, ?2), ?2) WHERE id = ?1").bind(id, now()).run();

// Token de gestión derivado del secreto IP_SALT: permite enviar enlaces «manage»
// en correos posteriores (aviso de caducidad, respuestas) sin guardar el token original.
const derivedToken = async (env, id) => (await sha256hex(`${env.IP_SALT || ''}:manage:${id}`)).slice(0, 43);

// Carga el post y comprueba el token de autor o el derivado (siempre en tiempo constante).
async function authPost(env, id, token) {
  if (!ID_RE.test(id || '') || !TOKEN_RE.test(token || '')) return null;
  const post = await getPost(env, id);
  if (!post) return null;
  const okOwn = timingEqual(await sha256hex(token), post.token_hash);
  const okDerived = timingEqual(token, await derivedToken(env, post.id));
  return okOwn || okDerived ? post : null;
}

function links(env, post, token) {
  const base = (env.SITE_URL || '').replace(/\/$/, '');
  const api = env.API_URL; // origen de la petición en fetch(); variable API_URL en el cron
  return {
    confirm: `${api}/confirm?id=${post.id}&t=${token}`,
    manage: `${api}/manage?id=${post.id}&t=${token}`,
    board: `${base}/${post.lang}/${SLUGS[post.lang] || SLUGS.ca}/#p-${post.id}`,
  };
}

const manageLink = async (env, post) => links(env, post, await derivedToken(env, post.id)).manage;

// ---------- endpoints ----------

async function listPosts(req, env, ctx, url) {
  const cache = caches.default;
  const key = postsCacheKey(url);
  const hit = await cache.match(key).catch(() => null);
  if (hit) return hit;
  const ts = now();
  const { results } = await env.DB.prepare(
    `SELECT ${PUBLIC_COLS} FROM posts WHERE status = 'live' AND expires > ?1 ORDER BY created DESC LIMIT 200`,
  )
    .bind(ts)
    .all();
  const res = json(
    { posts: results, generated: new Date(ts * 1000).toISOString() },
    200,
    // El navegador guarda 1 min; la caché del worker (s-maxage) 5 min y se purga al cambiar algo.
    { 'Cache-Control': 'public, max-age=60, s-maxage=300', 'Access-Control-Allow-Origin': '*' },
  );
  ctx.waitUntil(cache.put(key, res.clone()).catch(() => {}));
  return res;
}

async function createPost(req, env, ctx, url, cors) {
  const body = await readJson(req);
  const v = validate(body, {
    cat: { type: 'enum', values: CATS },
    lang: { type: 'enum', values: LANGS },
    title: { min: 5, max: 80 },
    body: { min: 20, max: 1000, multiline: true },
    name: { min: 2, max: 40 },
    email: { type: 'email' },
    contact: { min: 0, max: 60, optional: true },
    price: { min: 0, max: 20, optional: true },
    consent: { type: 'bool' },
  });
  if (v.field) return fail('invalid', 400, { field: v.field }, cors);
  const d = v.data;
  if (isBlocked(`${d.title}\n${d.body}\n${d.name}\n${d.contact}\n${d.price}`)) return fail('filtered', 400, {}, cors);

  const ip = await ipHashes(env, req);
  const ehash = await emailHash(env, d.email);
  if (!(await rateHit(env, `create:ip:${ip.day}`, 3)) || !(await rateHit(env, `create:email:${ehash.slice(0, 32)}`, 2))) {
    return fail('rate', 429, {}, cors);
  }
  if (!(await verifyTurnstile(env, body.turnstile, ip.ip))) return fail('turnstile', 403, {}, cors);

  const banned = await env.DB.prepare(
    "SELECT 1 AS b FROM bans WHERE (kind = 'ip' AND value = ?1) OR (kind = 'email' AND value = ?2) LIMIT 1",
  )
    .bind(ip.fixed, ehash)
    .first();
  if (banned) return fail('rate', 429, {}, cors);

  const live = await env.DB.prepare("SELECT COUNT(*) AS n FROM posts WHERE status = 'live' AND expires > ?1").bind(now()).first();
  if ((live?.n ?? 0) >= MAX_LIVE) return fail('full', 503, {}, cors);
  if (!(await takeMail(env, 1))) return fail('mail_quota', 503, {}, cors);

  const id = randomId();
  const token = randomToken();
  const ts = now();
  const post = {
    id, cat: d.cat, lang: d.lang, title: d.title, body: d.body, name: d.name,
    contact: d.contact || null, price: d.cat === 'deal' && d.price ? d.price : null, email: d.email,
  };
  await env.DB.prepare(
    `INSERT INTO posts (id, cat, lang, title, body, name, contact, price, email, token_hash, status, created, expires, ip_day, ip_fixed)
     VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, 'pending', ?11, ?12, ?13, ?14)`,
  )
    .bind(id, post.cat, post.lang, post.title, post.body, post.name, post.contact, post.price, post.email,
      await sha256hex(token), ts, ts + LIFETIME, ip.day, ip.fixed)
    .run();

  const l = links(env, post, token);
  const vars = { name: post.name, title: post.title, site: env.FROM_NAME, confirm: l.confirm, manage: l.manage, expires: fmtDate(ts + LIFETIME, post.lang) };
  try {
    await sendMail(env, { to: post.email, subject: t(post.lang, 'confirm_subject', vars), text: t(post.lang, 'confirm_body', vars) });
  } catch (e) {
    console.error('mail', e.message);
    await env.DB.prepare('DELETE FROM posts WHERE id = ?1').bind(id).run();
    return fail('mail', 502, {}, cors);
  }
  return json({ ok: true }, 201, cors);
}

async function confirmPost(req, env, ctx, url) {
  const id = url.searchParams.get('id') || '';
  const token = url.searchParams.get('t') || '';
  const ip = await ipHashes(env, req);
  if (!(await rateHit(env, `manage:ip:${ip.day}`, 30, HOUR))) return html(page('ca', 'Error', `<p>${esc(t('ca', 'page_rate'))}</p>`), 429);
  const post = await authPost(env, id, token);
  if (!post || post.status === 'deleted') return html(page('ca', 'Error', `<p>${esc(t('ca', 'page_gone'))}</p>`), 404);
  const lang = post.lang;
  if (post.status === 'pending') {
    const ts = now();
    await env.DB.prepare("UPDATE posts SET status = 'live', confirmed = ?2, expires = ?3 WHERE id = ?1 AND status = 'pending'")
      .bind(post.id, ts, ts + LIFETIME)
      .run();
    ctx.waitUntil(purgePosts(url));
  }
  const l = links(env, post, token);
  const inner = `<p>${esc(t(lang, 'page_confirm_ok', { title: post.title }))}</p><p><a href="${esc(l.board)}">${esc(t(lang, 'page_go_board'))}</a></p>`;
  return html(page(lang, t(lang, 'page_confirm_title'), inner, { refresh: l.board }));
}

function manageForms(lang, post, token, url) {
  const hidden = `<input type="hidden" name="id" value="${esc(post.id)}"><input type="hidden" name="t" value="${esc(token)}">`;
  const canRenew = post.status === 'live' && post.renewals < MAX_RENEWALS;
  return (
    (canRenew ? `<form method="post" action="${esc(new URL('/renew', url).pathname)}">${hidden}<button>${esc(t(lang, 'page_renew'))}</button></form>` : '') +
    `<form method="post" action="${esc(new URL('/delete', url).pathname)}">${hidden}<button class="danger">${esc(t(lang, 'page_delete'))}</button></form>`
  );
}

async function managePage(req, env, ctx, url, params, notice) {
  const ip = await ipHashes(env, req);
  if (!(await rateHit(env, `manage:ip:${ip.day}`, 30, HOUR))) return html(page('ca', 'Error', `<p>${esc(t('ca', 'page_rate'))}</p>`), 429);
  const post = await authPost(env, params.id || '', params.t || '');
  if (!post || post.status === 'deleted') return html(page('ca', 'Error', `<p>${esc(t('ca', 'page_gone'))}</p>`), 404);
  const lang = post.lang;
  const intro = t(lang, 'page_manage_intro', {
    title: post.title, status: t(lang, 'status_' + post.status), expires: fmtDate(post.expires, lang), renewals: post.renewals, max: MAX_RENEWALS,
  });
  const inner = (notice ? `<p><strong>${esc(notice)}</strong></p>` : '') + `<p>${esc(intro)}</p>` + manageForms(lang, post, params.t, url);
  return html(page(lang, t(lang, 'page_manage_title'), inner));
}

async function renewPost(req, env, ctx, url) {
  const params = await readForm(req);
  const post = await authPost(env, params.id || '', params.t || '');
  if (!post || post.status === 'deleted') return managePage(req, env, ctx, url, params);
  const lang = post.lang;
  if (post.status !== 'live') return managePage(req, env, ctx, url, params, t(lang, 'page_renew_no'));
  if (post.renewals >= MAX_RENEWALS) return managePage(req, env, ctx, url, params, t(lang, 'page_renew_max'));
  const exp = now() + LIFETIME;
  await env.DB.prepare('UPDATE posts SET expires = ?2, renewals = renewals + 1, warned = 0 WHERE id = ?1').bind(post.id, exp).run();
  ctx.waitUntil(purgePosts(url));
  return managePage(req, env, ctx, url, params, t(lang, 'page_renew_ok', { expires: fmtDate(exp, lang) }));
}

async function deletePost(req, env, ctx, url) {
  const params = await readForm(req);
  const ip = await ipHashes(env, req);
  if (!(await rateHit(env, `manage:ip:${ip.day}`, 30, HOUR))) return html(page('ca', 'Error', `<p>${esc(t('ca', 'page_rate'))}</p>`), 429);
  const post = await authPost(env, params.id || '', params.t || '');
  if (!post) return html(page('ca', 'Error', `<p>${esc(t('ca', 'page_gone'))}</p>`), 404);
  if (post.status !== 'deleted') {
    await markDeleted(env, post.id);
    ctx.waitUntil(purgePosts(url));
  }
  return html(page(post.lang, t(post.lang, 'page_manage_title'), `<p>${esc(t(post.lang, 'page_delete_ok'))}</p>`));
}

async function replyPost(req, env, ctx, url, cors) {
  const body = await readJson(req);
  const v = validate(body, {
    id: { type: 'id' },
    email: { type: 'email' },
    message: { min: 20, max: 2000, multiline: true },
  });
  if (v.field) return fail('invalid', 400, { field: v.field }, cors);
  const d = v.data;
  if (isBlocked(d.message)) return fail('filtered', 400, {}, cors);
  const ip = await ipHashes(env, req);
  if (!(await rateHit(env, `reply:ip:${ip.day}`, 5)) || !(await rateHit(env, `reply:post:${d.id}`, 10))) {
    return fail('rate', 429, {}, cors);
  }
  if (!(await verifyTurnstile(env, body.turnstile, ip.ip))) return fail('turnstile', 403, {}, cors);
  const post = await getPost(env, d.id);
  if (!post || post.status !== 'live' || post.expires <= now()) return fail('notfound', 404, {}, cors);
  if (!(await takeMail(env, 1))) return fail('mail_quota', 503, {}, cors);
  // El correo del lector solo viaja en Reply-To; no se guarda en D1.
  const vars = { name: post.name, title: post.title, site: env.FROM_NAME, message: d.message, manage: await manageLink(env, post) };
  try {
    await sendMail(env, {
      to: post.email,
      replyTo: d.email,
      subject: t(post.lang, 'reply_subject', vars),
      text: t(post.lang, 'reply_body', vars),
    });
  } catch (e) {
    console.error('mail', e.message);
    return fail('mail', 502, {}, cors);
  }
  return json({ ok: true }, 200, cors);
}

async function reportPost(req, env, ctx, url, cors) {
  const body = await readJson(req);
  const v = validate(body, {
    id: { type: 'id' },
    reason: { min: 0, max: 200, optional: true, content: false },
  });
  if (v.field) return fail('invalid', 400, { field: v.field }, cors);
  const d = v.data;
  const ip = await ipHashes(env, req);
  if (!(await rateHit(env, `report:ip:${ip.day}`, 10))) return fail('rate', 429, {}, cors);
  if (!(await verifyTurnstile(env, body.turnstile, ip.ip))) return fail('turnstile', 403, {}, cors);
  const post = await getPost(env, d.id);
  if (!post || post.status !== 'live') return fail('notfound', 404, {}, cors);
  await env.DB.prepare('INSERT OR IGNORE INTO reports (post_id, ip_day, created, reason) VALUES (?1, ?2, ?3, ?4)')
    .bind(post.id, ip.day, now(), d.reason || null)
    .run();
  const { results } = await env.DB.prepare('SELECT reason FROM reports WHERE post_id = ?1').bind(post.id).all();
  if (results.length >= REPORTS_TO_HIDE) {
    const r = await env.DB.prepare("UPDATE posts SET status = 'hidden', flagged = 1 WHERE id = ?1 AND status = 'live'").bind(post.id).run();
    if (r.meta?.changes) {
      ctx.waitUntil(purgePosts(url));
      ctx.waitUntil(notifyHidden(env, url, post, results.map((x) => x.reason || '-')));
    }
  }
  return json({ ok: true }, 200, cors);
}

async function notifyHidden(env, url, post, reasons) {
  if (!(await takeMail(env, 2))) return;
  const admin = `${env.API_URL}/admin?key=${encodeURIComponent(env.ADMIN_KEY || '')}`;
  const common = { name: post.name, title: post.title, id: post.id, cat: CAT_NAMES.es[post.cat], site: env.FROM_NAME };
  try {
    if (env.ADMIN_EMAIL) {
      await sendMail(env, {
        to: env.ADMIN_EMAIL,
        subject: t('es', 'report_admin_subject', common),
        text: t('es', 'report_admin_body', { ...common, reasons: reasons.map((r) => '- ' + r).join('\n'), admin }),
      });
    }
    await sendMail(env, {
      to: post.email,
      subject: t(post.lang, 'hidden_author_subject', common),
      text: t(post.lang, 'hidden_author_body', { ...common, manage: await manageLink(env, post) }),
    });
  } catch (e) {
    console.error('mail', e.message);
  }
}

// ---------- admin ----------

function adminRow(p, url) {
  const btn = (action, label, cls = '') =>
    `<form method="post" action="/admin" style="display:inline"><input type="hidden" name="key" value="${esc(url.searchParams.get('key') || '')}">` +
    `<input type="hidden" name="action" value="${action}"><input type="hidden" name="id" value="${esc(p.id)}"><button class="${cls}">${label}</button></form>`;
  return (
    `<tr><td><code>${esc(p.id)}</code><br>${esc(p.status)}${p.flagged ? ' ⚑' : ''}<br>${esc(CAT_NAMES.es[p.cat])} · ${esc(p.lang)}</td>` +
    `<td><strong>${esc(p.title)}</strong><br>${esc(p.body).replace(/\n/g, '<br>')}<br><small>${esc(p.name)} · ${esc(p.contact || '')} · ${esc(p.price || '')}</small>` +
    (p.reports ? `<br><small>Denuncias: ${esc(p.reports)}</small>` : '') +
    `<br><small>creado ${fmtDate(p.created, 'es')} · caduca ${p.expires ? fmtDate(p.expires, 'es') : '-'}</small></td>` +
    `<td>${p.status !== 'deleted' ? btn('delete', 'Borrar', 'danger') : ''} ${p.status === 'hidden' ? btn('restore', 'Restaurar') : ''} ` +
    `${btn('ban_ip', 'Banear IP')} ${btn('ban_email', 'Banear email')}</td></tr>`
  );
}

async function adminPage(req, env, url, notice) {
  const hidden = await env.DB.prepare(
    `SELECT p.*, (SELECT group_concat(reason, ' | ') FROM reports r WHERE r.post_id = p.id) AS reports
     FROM posts p WHERE p.status = 'hidden' OR p.flagged = 1 ORDER BY p.created DESC LIMIT 100`,
  ).all();
  const live = await env.DB.prepare("SELECT * FROM posts WHERE status = 'live' ORDER BY created DESC LIMIT 50").all();
  const table = (rows) =>
    rows.length ? `<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">${rows.map((p) => adminRow(p, url)).join('')}</table>` : '<p>Nada.</p>';
  const inner =
    (notice ? `<p><strong>${esc(notice)}</strong></p>` : '') +
    `<h2>Ocultos o denunciados (${hidden.results.length})</h2>${table(hidden.results)}` +
    `<h2>Últimos 50 vivos</h2>${table(live.results)}`;
  const body = page('es', 'Moderación del tablón', inner).replace('max-width:40rem', 'max-width:70rem');
  return html(body);
}

async function admin(req, env, ctx, url) {
  const ip = await ipHashes(env, req);
  if (!(await rateHit(env, `admin:ip:${ip.day}`, 5, HOUR))) return html(page('es', 'Error', `<p>${esc(t('es', 'page_rate'))}</p>`), 429);
  if (req.method === 'GET') {
    if (!(await secretEqual(url.searchParams.get('key'), env.ADMIN_KEY))) return html(page('es', 'Error', '<p>Clave incorrecta.</p>'), 403);
    return adminPage(req, env, url);
  }
  const f = await readForm(req);
  if (!(await secretEqual(f.key, env.ADMIN_KEY))) return html(page('es', 'Error', '<p>Clave incorrecta.</p>'), 403);
  url.searchParams.set('key', f.key);
  const post = ID_RE.test(f.id || '') ? await getPost(env, f.id) : null;
  if (!post) return adminPage(req, env, url, 'Anuncio no encontrado.');
  let notice = 'Hecho.';
  if (f.action === 'delete') {
    await markDeleted(env, post.id);
  } else if (f.action === 'restore') {
    await env.DB.prepare("UPDATE posts SET status = 'live', flagged = 0 WHERE id = ?1").bind(post.id).run();
    await env.DB.prepare('DELETE FROM reports WHERE post_id = ?1').bind(post.id).run();
  } else if (f.action === 'ban_ip') {
    if (post.ip_fixed) {
      await env.DB.prepare("INSERT OR IGNORE INTO bans (kind, value, note, created) VALUES ('ip', ?1, ?2, ?3)").bind(post.ip_fixed, post.id, now()).run();
    }
    await markDeleted(env, post.id);
  } else if (f.action === 'ban_email') {
    await env.DB.prepare("INSERT OR IGNORE INTO bans (kind, value, note, created) VALUES ('email', ?1, ?2, ?3)")
      .bind(await emailHash(env, post.email), post.id, now())
      .run();
    await markDeleted(env, post.id);
  } else {
    notice = 'Acción desconocida.';
  }
  ctx.waitUntil(purgePosts(url));
  return adminPage(req, env, url, notice);
}

// ---------- cron ----------

async function runScheduled(env) {
  const ts = now();
  const db = env.DB;
  await db.batch([
    db.prepare("UPDATE posts SET status = 'deleted' WHERE status = 'live' AND expires < ?1").bind(ts),
    db.prepare("DELETE FROM posts WHERE status = 'pending' AND created < ?1").bind(ts - 2 * DAY),
    // Al borrar (manual o por caducidad) `expires` queda en el pasado: sirve como fecha de borrado.
    db.prepare("DELETE FROM posts WHERE status = 'deleted' AND COALESCE(expires, created) < ?1").bind(ts - 7 * DAY),
    db.prepare('DELETE FROM rate WHERE reset < ?1').bind(ts),
    db.prepare('DELETE FROM reports WHERE created < ?1').bind(ts - 60 * DAY),
  ]);
  // Aviso de caducidad (≤ 5 días) una sola vez por anuncio.
  const { results } = await db
    .prepare("SELECT id, lang, name, title, email, expires FROM posts WHERE status = 'live' AND warned = 0 AND expires > ?1 AND expires <= ?2 LIMIT 100")
    .bind(ts, ts + 5 * DAY)
    .all();
  for (const p of results) {
    if (!(await takeMail(env, 1))) break;
    const vars = { name: p.name, title: p.title, expires: fmtDate(p.expires, p.lang), site: env.FROM_NAME, manage: await manageLink(env, p) };
    try {
      await sendMail(env, { to: p.email, subject: t(p.lang, 'expiring_subject', vars), text: t(p.lang, 'expiring_body', vars) });
      await db.prepare('UPDATE posts SET warned = 1 WHERE id = ?1').bind(p.id).run();
    } catch (e) {
      console.error('mail', e.message);
    }
  }
}

// ---------- router ----------

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    const path = url.pathname.replace(/\/+$/, '') || '/';
    env = { ...env, API_URL: url.origin }; // enlaces absolutos a este worker (el cron usa la variable API_URL)
    try {
      if (req.method === 'OPTIONS') return preflight(req, env, path);
      if (req.method === 'GET') {
        if (path === '/health') return json({ ok: true });
        if (path === '/posts') return listPosts(req, env, ctx, url);
        if (path === '/confirm') return confirmPost(req, env, ctx, url);
        if (path === '/manage') return managePage(req, env, ctx, url, { id: url.searchParams.get('id'), t: url.searchParams.get('t') });
        if (path === '/admin') return admin(req, env, ctx, url);
        return fail('notfound', 404);
      }
      if (req.method === 'POST') {
        if (path === '/renew') return renewPost(req, env, ctx, url);
        if (path === '/delete') return deletePost(req, env, ctx, url);
        if (path === '/admin') return admin(req, env, ctx, url);
        const cors = corsFor(req, env, false);
        if (!cors.ok) return fail('invalid', 403, { field: 'origin' });
        if (path === '/posts') return createPost(req, env, ctx, url, cors.headers);
        if (path === '/reply') return replyPost(req, env, ctx, url, cors.headers);
        if (path === '/report') return reportPost(req, env, ctx, url, cors.headers);
        return fail('notfound', 404, {}, cors.headers);
      }
      return fail('notfound', 404);
    } catch (e) {
      console.error(e);
      return fail('server', 500);
    }
  },

  async scheduled(event, env, ctx) {
    if (!env.API_URL) console.warn('Falta la variable API_URL en wrangler.toml: los enlaces de los correos del cron saldrán incompletos');
    ctx.waitUntil(runScheduled(env));
  },
};

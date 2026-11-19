// Contador de visitas anónimo de las webs (sin cookies, sin IP: solo un número por web y día).

export const SITES = {
  hv: 'https://horaverda.es',
  cer: 'https://cerdanyola.horaverda.es',
  sc: 'https://santcugat.horaverda.es',
  osm: 'https://onestudioman.horaverda.es',
};

// Día natural en Europe/Madrid, AAAA-MM-DD.
export function madridDay(d = new Date()) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Madrid', year: 'numeric', month: '2-digit', day: '2-digit' }).format(d);
}

// Solo suma la visita si viene del navegador de esa web (o de localhost con VISITS_DEV=1 en `wrangler dev`).
export function countable(site, origin, env = {}) {
  if (!origin) return false;
  if (origin === SITES[site]) return true;
  return env.VISITS_DEV === '1' && /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin);
}

export async function visits(req, env, site) {
  const headers = { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'Access-Control-Allow-Origin': '*' };
  if (!Object.hasOwn(SITES, site || '')) return new Response('{"error":"invalid"}', { status: 400, headers });
  const day = madridDay();
  if (req.method === 'POST' && countable(site, req.headers.get('Origin'), env)) {
    await env.DB.prepare('INSERT INTO visits (site, day, n) VALUES (?1, ?2, 1) ON CONFLICT (site, day) DO UPDATE SET n = n + 1')
      .bind(site, day)
      .run();
  }
  const row = await env.DB.prepare(
    'SELECT COALESCE(SUM(n), 0) AS total, COALESCE(SUM(CASE WHEN day = ?2 THEN n END), 0) AS today FROM visits WHERE site = ?1',
  )
    .bind(site, day)
    .first();
  return new Response(JSON.stringify({ today: row?.today || 0, total: row?.total || 0 }), { status: 200, headers });
}

// Envío de correo por la API de Gmail con OAuth2 (refresh token en secreto del worker).

let cached = { token: null, exp: 0 }; // caché del access token a nivel de módulo

export async function getAccessToken(env) {
  const now = Date.now();
  if (cached.token && cached.exp > now + 30_000) return cached.token;
  const body = new URLSearchParams({
    client_id: env.GMAIL_CLIENT_ID,
    client_secret: env.GMAIL_CLIENT_SECRET,
    refresh_token: env.GMAIL_REFRESH_TOKEN,
    grant_type: 'refresh_token',
  });
  const r = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  if (!r.ok) throw new Error('oauth ' + r.status + ' ' + (await r.text()).slice(0, 200));
  const j = await r.json();
  cached = { token: j.access_token, exp: now + (j.expires_in || 3600) * 1000 };
  return cached.token;
}

function b64(bytes) {
  let s = '';
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s);
}

function b64url(bytes) {
  return b64(bytes).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

// Cabecera con UTF-8 codificada según RFC 2047.
function encHeader(s) {
  return /^[\x20-\x7e]*$/.test(s) ? s : '=?UTF-8?B?' + b64(new TextEncoder().encode(s)) + '?=';
}

// Solo direcciones simples; evita inyección de cabeceras.
function cleanAddr(a) {
  return String(a).replace(/[\r\n<>"]/g, '').trim();
}

// Construye el mensaje RFC 822 en texto plano.
export function buildRaw({ from, fromName, to, subject, text, replyTo }) {
  const name = fromName.replace(/["\r\n]/g, '');
  const lines = [
    `From: ${/^[\x20-\x7e]*$/.test(name) ? '"' + name + '"' : encHeader(name)} <${cleanAddr(from)}>`,
    `To: <${cleanAddr(to)}>`,
  ];
  if (replyTo) lines.push(`Reply-To: <${cleanAddr(replyTo)}>`);
  lines.push(
    `Subject: ${encHeader(subject.replace(/[\r\n]+/g, ' '))}`,
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=utf-8',
    'Content-Transfer-Encoding: base64',
    '',
    b64(new TextEncoder().encode(text)).replace(/(.{76})/g, '$1\r\n'),
  );
  return lines.join('\r\n');
}

export async function sendMail(env, { to, subject, text, replyTo }) {
  const raw = buildRaw({
    from: env.GMAIL_FROM,
    fromName: env.FROM_NAME || 'Tauler veïnal',
    to,
    subject,
    text,
    replyTo,
  });
  if (env.MAIL_DRY_RUN === '1' && !env.GMAIL_REFRESH_TOKEN) {
    // Solo en local (.dev.vars): imprime el correo en vez de enviarlo.
    console.log('[correo no enviado: MAIL_DRY_RUN]\n' + raw);
    return true;
  }
  const token = await getAccessToken(env);
  const r = await fetch('https://gmail.googleapis.com/gmail/v1/users/me/messages/send', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' },
    body: JSON.stringify({ raw: b64url(new TextEncoder().encode(raw)) }),
  });
  if (!r.ok) throw new Error('gmail ' + r.status + ' ' + (await r.text()).slice(0, 200));
  return true;
}

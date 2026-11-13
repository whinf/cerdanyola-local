// node --test worker/test
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { MAIL, LANGS, fmt, t, esc, page } from '../src/i18n.js';
import { isBlocked, hasIban, hasCard, checkText, fold } from '../src/filter.js';
import { buildRaw } from '../src/mail.js';

const placeholders = (s) => [...String(s).matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

test('i18n: mismas claves y mismos placeholders en ca/es/en', () => {
  const keys = Object.keys(MAIL.ca).sort();
  assert.ok(keys.length > 10);
  for (const lang of LANGS) {
    assert.deepEqual(Object.keys(MAIL[lang]).sort(), keys, `claves de ${lang}`);
    for (const k of keys) {
      assert.deepEqual(placeholders(MAIL[lang][k]), placeholders(MAIL.ca[k]), `placeholders de ${lang}.${k}`);
    }
  }
});

test('i18n: fmt, t, esc y page', () => {
  assert.equal(fmt('Hola {name} {x}', { name: 'Ana' }), 'Hola Ana ');
  assert.ok(t('es', 'confirm_subject', { title: 'Sofá' }).includes('Sofá'));
  assert.ok(t('en', 'reply_body', {}).includes('never send money'));
  assert.equal(esc('<a href="x">&\'</a>'), '&lt;a href=&quot;x&quot;&gt;&amp;&#39;&lt;/a&gt;');
  const html = page('en', 'T<', '<p>x</p>', { refresh: 'https://e.x/?a=1&b=2' });
  assert.ok(html.includes('<html lang="en">') && html.includes('T&lt;') && html.includes('a=1&amp;b=2'));
});

test('filter: rechaza IBAN y tarjetas', () => {
  assert.ok(hasIban('Haz el ingreso en ES76 2100 0418 4502 0005 1332 gracias'));
  assert.ok(hasIban('iban GB29NWBK60161331926819'));
  assert.ok(hasCard('tarjeta 4111 1111 1111 1111'));
  assert.ok(hasCard('4111111111111111'));
  assert.equal(checkText('Pago a ES7621000418450200051332'), 'iban');
  assert.equal(checkText('Mi tarjeta 4111-1111-1111-1111'), 'card');
});

test('filter: acepta texto normal', () => {
  const ok = [
    'Regalo un sofá de tres plazas en buen estado, recoger en el centro. Teléfono 600 123 456.',
    'Busco ajuda per muntar un armari dissabte al matí, al barri de Montflorit.',
    'iPhone 12 Pro Max 256GB, battery at 88%, used for two years. Ref: XPS13.',
    'Dell XPS 13 i7 16GB 512GB SSD, molt bon estat, amb funda.',
    'Clases de refuerzo de matemáticas, 10 €/h. Disputa amistosa sobre quién es mejor en computación.',
  ];
  for (const s of ok) {
    assert.equal(checkText(s), null, s);
  }
});

test('filter: bloquea insultos y patrones de estafa con acentos plegados', () => {
  assert.ok(isBlocked('Eres un GILIPOLLAS'));
  assert.ok(isBlocked('ets un fill de puta'));
  assert.ok(isBlocked('Envía el Bizum por adelantado y te lo mando'));
  assert.ok(isBlocked('Inversión garantizada en cripto, ganancias del 20%'));
  assert.ok(isBlocked('Pago solo por Western Únion'));
  assert.ok(!isBlocked('Pago por Bizum al recoger'));
  assert.ok(!isBlocked('Hablamos de cripto en el taller del sábado'));
  assert.equal(fold('Càmera Ñandú'), 'camera nandu');
});

test('mail: construye RFC 822 con cabeceras codificadas', () => {
  const raw = buildRaw({ from: 'a@b.c', fromName: 'Tauler veïnal', to: 'x@y.z', replyTo: 'r@s.t\r\nBcc: evil', subject: 'Hola món', text: 'Cos del missatge' });
  assert.ok(raw.startsWith('From: =?UTF-8?B?'));
  assert.ok(raw.includes('\r\nTo: <x@y.z>\r\n'));
  assert.ok(raw.includes('\r\nReply-To: <r@s.tBcc: evil>\r\n'));
  assert.ok(raw.includes('Subject: =?UTF-8?B?'));
  assert.ok(raw.includes('Content-Transfer-Encoding: base64\r\n\r\n'));
  assert.equal(Buffer.from(raw.split('\r\n\r\n')[1].replace(/\r\n/g, ''), 'base64').toString(), 'Cos del missatge');
});

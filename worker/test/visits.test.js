import { test } from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';
import { visits, countable, madridDay } from '../src/visits.js';

// Imita la API de D1 sobre SQLite en memoria con el esquema real.
function fakeD1() {
  const db = new DatabaseSync(':memory:');
  db.exec(readFileSync(new URL('../schema.sql', import.meta.url), 'utf8'));
  return {
    prepare(sql) {
      const st = db.prepare(sql);
      let args = [];
      return {
        bind(...a) { args = a; return this; },
        async run() { return st.run(...args); },
        async first() { return st.get(...args); },
      };
    },
  };
}

const hit = (env, site, origin, method = 'POST') =>
  // Request de Node descarta la cabecera Origin (prohibida en fetch): objeto mínimo.
  visits({ method, headers: new Headers(origin ? { Origin: origin } : {}) }, env, site).then(async (r) => [r.status, await r.json()]);

test('visits: suma solo desde el origen de cada web', async () => {
  const env = { DB: fakeD1() };
  assert.deepEqual(await hit(env, 'hv', 'https://horaverda.es'), [200, { today: 1, total: 1 }]);
  assert.deepEqual(await hit(env, 'hv', 'https://horaverda.es'), [200, { today: 2, total: 2 }]);
  assert.deepEqual(await hit(env, 'hv', 'https://evil.example'), [200, { today: 2, total: 2 }]);
  assert.deepEqual(await hit(env, 'hv', null), [200, { today: 2, total: 2 }]);
  assert.deepEqual(await hit(env, 'hv', 'https://horaverda.es', 'GET'), [200, { today: 2, total: 2 }]);
  assert.deepEqual(await hit(env, 'cer', 'https://horaverda.es'), [200, { today: 0, total: 0 }]);
  assert.equal((await hit(env, 'nope', 'https://horaverda.es'))[0], 400);
});

test('visits: localhost solo con VISITS_DEV y día de Madrid', () => {
  assert.ok(!countable('cer', 'http://localhost:8001', {}));
  assert.ok(countable('cer', 'http://localhost:8001', { VISITS_DEV: '1' }));
  assert.ok(!countable('cer', 'http://localhost.evil.x', { VISITS_DEV: '1' }));
  assert.equal(madridDay(new Date('2026-03-01T23:30:00Z')), '2026-03-02');
});

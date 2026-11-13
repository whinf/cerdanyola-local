// Filtro de contenido: palabras bloqueadas, patrones de estafa, IBAN y tarjetas.
// Todo se compara con acentos plegados y en minúsculas (fold()).

export function fold(s) {
  return String(s).normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
}

// Palabras y frases (ca/es/en). Se comparan como palabra completa.
export const BLOCKLIST = [
  // insultos y slurs ca/es
  'hijo de puta', 'hija de puta', 'hijos de puta', 'fill de puta', 'filla de puta', 'fills de puta',
  'gilipollas', 'subnormal', 'subnormals', 'retrasado', 'retrasada', 'retrasados', 'mongolo', 'mongola',
  'maricon', 'maricones', 'marica', 'maricas', 'bollera', 'bolleras', 'travelo', 'travelos',
  'sudaca', 'sudacas', 'negrata', 'negratas', 'panchito', 'panchitos', 'charnego', 'xarnego',
  'moro de mierda', 'moros de mierda', 'negro de mierda', 'puta de mierda', 'puto de mierda',
  'cabron', 'cabrona', 'cabrones', 'capullo', 'capullos', 'imbecil', 'imbeciles', 'malparido', 'malparit',
  'hostia puta', 'me cago en', 'em cago en', 'heil hitler', 'sieg heil',
  // en
  'fuck', 'fucking', 'fucker', 'motherfucker', 'bitch', 'bitches', 'asshole', 'cunt', 'dickhead',
  'nigger', 'nigga', 'faggot', 'fag', 'retard', 'retards', 'spic', 'chink', 'kike', 'wetback', 'tranny',
  // spam habitual
  'viagra', 'cialis', 'casino online', 'apuestas deportivas', 'onlyfans', 'escort', 'escorts',
];

// Patrones de estafa: fragmentos que deben aparecer todos a la vez, en cualquier orden.
export const SCAM_PATTERNS = [
  ['bizum', 'adelant'], // «bizum» + «adelantado / per adelantat»
  ['bizum', 'advance'],
  ['pago', 'adelantado'],
  ['pagament', 'avancat'],
  ['western union'],
  ['moneygram'],
  ['inversion garantizada'], ['inversio garantida'], ['guaranteed return'], ['guaranteed profit'],
  ['cripto', 'ganancia'], ['crypto', 'ganancia'], ['cripto', 'guany'], ['crypto', 'guany'],
  ['crypto', 'profit'], ['crypto', 'earning'], ['bitcoin', 'ganancia'], ['bitcoin', 'profit'],
  ['dinero facil'], ['diners facils'], ['easy money'],
  ['tarjeta regalo', 'codigo'], ['gift card', 'code'],
];

function escapeRe(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

const WORD_RE = new RegExp(
  '(?<![a-z0-9])(?:' +
    BLOCKLIST.map((w) => fold(w).trim().split(/\s+/).map(escapeRe).join('\\s+')).join('|') +
    ')(?![a-z0-9])',
  'i',
);

const SCAM_RES = SCAM_PATTERNS.map(
  (parts) => new RegExp(parts.map((p) => '(?=[\\s\\S]*' + escapeRe(fold(p)) + ')').join(''), 'i'),
);

// true si el texto contiene una palabra bloqueada o un patrón de estafa.
export function isBlocked(text) {
  const t = fold(text);
  if (WORD_RE.test(t)) return true;
  return SCAM_RES.some((re) => re.test(t));
}

// IBAN: dos letras, dos dígitos y 10–30 alfanuméricos, con o sin espacios/guiones entre grupos
// (ES76 2100 0418 4502 0005 1332, ES7621000418450200051332, GB29NWBK60161331926819…).
const IBAN_RE = /(?<![A-Z0-9])[A-Z]{2}\d{2}(?:[ -]?[A-Z0-9]){10,30}(?![A-Z0-9])/g;
export function hasIban(text) {
  const t = String(text).toUpperCase();
  for (const m of t.matchAll(IBAN_RE)) {
    // Para reducir falsos positivos (modelos de productos) se exige mayoría de dígitos.
    const digits = (m[0].match(/\d/g) || []).length;
    if (digits >= 10) return true;
  }
  return false;
}

// Número de tarjeta: 13–19 dígitos seguidos o separados por espacios/guiones.
const CARD_RE = /(?<![\d-])\d(?:[ -]?\d){12,18}(?![\d-])/;
export function hasCard(text) {
  return CARD_RE.test(String(text));
}

// Comprobación completa: null si pasa, o el motivo ('filtered' | 'iban' | 'card').
export function checkText(text) {
  if (hasIban(text)) return 'iban';
  if (hasCard(text)) return 'card';
  if (isBlocked(text)) return 'filtered';
  return null;
}

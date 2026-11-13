// Plantillas de correo y textos de las páginas HTML mínimas, en ca/es/en.
// Los placeholders {x} se sustituyen con fmt().

export const LANGS = ['ca', 'es', 'en'];
export const CATS = ['help', 'give', 'deal'];

// Slug de la página del tablón en el sitio estático, por idioma.
export const SLUGS = { ca: 'tauler', es: 'tablon', en: 'board' };

export const CAT_NAMES = {
  ca: { help: "Ajuda'm", give: 'Ho regalo', deal: 'Ganga' },
  es: { help: 'Ayúdame', give: 'Lo regalo', deal: 'Chollo' },
  en: { help: 'Help me', give: 'Giving away', deal: 'Deal' },
};

const WARN = {
  ca: 'Consell de seguretat: no enviïs mai diners per avançat ni comparteixis dades bancàries. Queda en un lloc públic.',
  es: 'Consejo de seguridad: nunca envíes dinero por adelantado ni compartas datos bancarios. Queda en un lugar público.',
  en: 'Safety tip: never send money in advance or share bank details. Meet in a public place.',
};

export const MAIL = {
  ca: {
    confirm_subject: 'Confirma el teu anunci: {title}',
    confirm_body:
      'Hola {name},\n\n' +
      'Has publicat «{title}» al {site}. Per fer-lo visible, confirma el teu correu obrint aquest enllaç:\n\n' +
      '{confirm}\n\n' +
      "L'anunci caducarà el {expires}. Des d'aquest altre enllaç el podràs renovar o esborrar quan vulguis (guarda\'l):\n\n" +
      '{manage}\n\n' +
      "Si no has estat tu, ignora aquest correu i l'anunci s'esborrarà sol en 48 hores.\n\n" +
      '{warn}',
    reply_subject: 'Resposta al teu anunci «{title}»',
    reply_body:
      'Hola {name},\n\n' +
      'Algú ha respost al teu anunci «{title}» des del {site}:\n\n' +
      '----------------------------------------\n{message}\n----------------------------------------\n\n' +
      'Respon a aquest correu per contestar-li. El teu correu només el veurà si li contestes.\n\n' +
      '{warn}\n\n' +
      "Gestiona l'anunci (renovar o esborrar): {manage}",
    report_admin_subject: '[Tauler] Anunci ocultat per denúncies: {id}',
    report_admin_body:
      "L'anunci «{title}» ({cat}, {id}) ha rebut 3 denúncies de persones diferents i s'ha ocultat.\n\n" +
      'Motius:\n{reasons}\n\n' +
      'Revisa-ho a: {admin}',
    hidden_author_subject: "El teu anunci «{title}» s'ha ocultat",
    hidden_author_body:
      'Hola {name},\n\n' +
      "El teu anunci «{title}» ha rebut diverses denúncies de veïns i s'ha ocultat temporalment mentre el revisem. " +
      'Si tot és correcte el tornarem a publicar; si no, quedarà esborrat.\n\n' +
      'Si vols esborrar-lo tu mateix: {manage}',
    expiring_subject: 'El teu anunci «{title}» caduca aviat',
    expiring_body:
      'Hola {name},\n\n' +
      "El teu anunci «{title}» caduca el {expires}. Si encara és vigent, renova'l des d'aquí (45 dies més):\n\n" +
      '{manage}\n\n' +
      "Si ja no cal, no has de fer res: s'esborrarà sol.",
    page_confirm_title: 'Anunci confirmat',
    page_confirm_ok: 'El teu anunci «{title}» ja és públic. Et portem al tauler en uns segons…',
    page_go_board: 'Anar al tauler',
    page_manage_title: 'Gestiona el teu anunci',
    page_manage_intro: '«{title}» · estat: {status} · caduca el {expires} · renovacions: {renewals} de {max}.',
    page_renew: 'Renovar 45 dies més',
    page_delete: 'Esborrar l\'anunci',
    page_renew_ok: 'Anunci renovat. Ara caduca el {expires}.',
    page_renew_max: "Aquest anunci ja ha arribat al màxim de renovacions. Pots publicar-ne un de nou al tauler.",
    page_renew_no: 'Aquest anunci no es pot renovar en el seu estat actual.',
    page_delete_ok: "L'anunci s'ha esborrat. Gràcies per mantenir el tauler al dia.",
    page_gone: 'Aquest anunci ja no existeix o l\'enllaç no és vàlid.',
    page_rate: 'Massa peticions. Torna-ho a provar d\'aquí una estona.',
    page_error: 'Hi ha hagut un error. Torna-ho a provar més tard.',
    status_pending: 'pendent de confirmar',
    status_live: 'publicat',
    status_hidden: 'ocultat (en revisió)',
    status_deleted: 'esborrat',
  },
  es: {
    confirm_subject: 'Confirma tu anuncio: {title}',
    confirm_body:
      'Hola {name},\n\n' +
      'Has publicado «{title}» en {site}. Para hacerlo visible, confirma tu correo abriendo este enlace:\n\n' +
      '{confirm}\n\n' +
      'El anuncio caducará el {expires}. Desde este otro enlace podrás renovarlo o borrarlo cuando quieras (guárdalo):\n\n' +
      '{manage}\n\n' +
      'Si no has sido tú, ignora este correo y el anuncio se borrará solo en 48 horas.\n\n' +
      '{warn}',
    reply_subject: 'Respuesta a tu anuncio «{title}»',
    reply_body:
      'Hola {name},\n\n' +
      'Alguien ha respondido a tu anuncio «{title}» desde {site}:\n\n' +
      '----------------------------------------\n{message}\n----------------------------------------\n\n' +
      'Responde a este correo para contestarle. Tu correo solo lo verá si le contestas.\n\n' +
      '{warn}\n\n' +
      'Gestiona el anuncio (renovar o borrar): {manage}',
    report_admin_subject: '[Tablón] Anuncio ocultado por denuncias: {id}',
    report_admin_body:
      'El anuncio «{title}» ({cat}, {id}) ha recibido 3 denuncias de personas distintas y se ha ocultado.\n\n' +
      'Motivos:\n{reasons}\n\n' +
      'Revísalo en: {admin}',
    hidden_author_subject: 'Tu anuncio «{title}» se ha ocultado',
    hidden_author_body:
      'Hola {name},\n\n' +
      'Tu anuncio «{title}» ha recibido varias denuncias de vecinos y se ha ocultado temporalmente mientras lo revisamos. ' +
      'Si todo es correcto lo volveremos a publicar; si no, quedará borrado.\n\n' +
      'Si quieres borrarlo tú mismo: {manage}',
    expiring_subject: 'Tu anuncio «{title}» caduca pronto',
    expiring_body:
      'Hola {name},\n\n' +
      'Tu anuncio «{title}» caduca el {expires}. Si sigue vigente, renuévalo desde aquí (45 días más):\n\n' +
      '{manage}\n\n' +
      'Si ya no hace falta, no tienes que hacer nada: se borrará solo.',
    page_confirm_title: 'Anuncio confirmado',
    page_confirm_ok: 'Tu anuncio «{title}» ya es público. Te llevamos al tablón en unos segundos…',
    page_go_board: 'Ir al tablón',
    page_manage_title: 'Gestiona tu anuncio',
    page_manage_intro: '«{title}» · estado: {status} · caduca el {expires} · renovaciones: {renewals} de {max}.',
    page_renew: 'Renovar 45 días más',
    page_delete: 'Borrar el anuncio',
    page_renew_ok: 'Anuncio renovado. Ahora caduca el {expires}.',
    page_renew_max: 'Este anuncio ya ha llegado al máximo de renovaciones. Puedes publicar uno nuevo en el tablón.',
    page_renew_no: 'Este anuncio no se puede renovar en su estado actual.',
    page_delete_ok: 'El anuncio se ha borrado. Gracias por mantener el tablón al día.',
    page_gone: 'Este anuncio ya no existe o el enlace no es válido.',
    page_rate: 'Demasiadas peticiones. Vuelve a intentarlo dentro de un rato.',
    page_error: 'Ha habido un error. Vuelve a intentarlo más tarde.',
    status_pending: 'pendiente de confirmar',
    status_live: 'publicado',
    status_hidden: 'ocultado (en revisión)',
    status_deleted: 'borrado',
  },
  en: {
    confirm_subject: 'Confirm your post: {title}',
    confirm_body:
      'Hi {name},\n\n' +
      'You posted "{title}" on {site}. To make it visible, confirm your email by opening this link:\n\n' +
      '{confirm}\n\n' +
      'The post expires on {expires}. Use this other link to renew or delete it whenever you like (keep it):\n\n' +
      '{manage}\n\n' +
      "If this wasn't you, ignore this email and the post will be deleted automatically in 48 hours.\n\n" +
      '{warn}',
    reply_subject: 'Reply to your post "{title}"',
    reply_body:
      'Hi {name},\n\n' +
      'Someone replied to your post "{title}" from {site}:\n\n' +
      '----------------------------------------\n{message}\n----------------------------------------\n\n' +
      'Reply to this email to answer them. They will only see your email if you reply.\n\n' +
      '{warn}\n\n' +
      'Manage your post (renew or delete): {manage}',
    report_admin_subject: '[Board] Post hidden after reports: {id}',
    report_admin_body:
      'The post "{title}" ({cat}, {id}) received 3 reports from different people and has been hidden.\n\n' +
      'Reasons:\n{reasons}\n\n' +
      'Review it at: {admin}',
    hidden_author_subject: 'Your post "{title}" has been hidden',
    hidden_author_body:
      'Hi {name},\n\n' +
      'Your post "{title}" received several reports from neighbours and has been hidden temporarily while we review it. ' +
      'If everything is fine we will publish it again; otherwise it will be deleted.\n\n' +
      'To delete it yourself: {manage}',
    expiring_subject: 'Your post "{title}" expires soon',
    expiring_body:
      'Hi {name},\n\n' +
      'Your post "{title}" expires on {expires}. If it is still current, renew it here (45 more days):\n\n' +
      '{manage}\n\n' +
      "If it's no longer needed, do nothing: it will be deleted automatically.",
    page_confirm_title: 'Post confirmed',
    page_confirm_ok: 'Your post "{title}" is now public. Taking you to the board in a few seconds…',
    page_go_board: 'Go to the board',
    page_manage_title: 'Manage your post',
    page_manage_intro: '"{title}" · status: {status} · expires on {expires} · renewals: {renewals} of {max}.',
    page_renew: 'Renew for 45 more days',
    page_delete: 'Delete the post',
    page_renew_ok: 'Post renewed. It now expires on {expires}.',
    page_renew_max: 'This post has reached the maximum number of renewals. You can publish a new one on the board.',
    page_renew_no: 'This post cannot be renewed in its current state.',
    page_delete_ok: 'The post has been deleted. Thanks for keeping the board up to date.',
    page_gone: 'This post no longer exists or the link is not valid.',
    page_rate: 'Too many requests. Please try again in a while.',
    page_error: 'Something went wrong. Please try again later.',
    status_pending: 'pending confirmation',
    status_live: 'published',
    status_hidden: 'hidden (under review)',
    status_deleted: 'deleted',
  },
};

// Sustituye {x} por vars.x (vacío si no existe). {warn} se rellena solo según idioma.
export function fmt(tpl, vars = {}, lang = 'ca') {
  const all = { warn: WARN[lang] || WARN.ca, ...vars };
  return String(tpl).replace(/\{(\w+)\}/g, (_, k) => (all[k] === undefined || all[k] === null ? '' : String(all[k])));
}

// Texto de la plantilla `key` en `lang` (con fallback a catalán) ya formateado.
export function t(lang, key, vars) {
  const l = MAIL[lang] ? lang : 'ca';
  return fmt(MAIL[l][key] ?? MAIL.ca[key] ?? key, vars, l);
}

export function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// Fecha dd/mm/aaaa en hora de Madrid (fallback ISO en UTC).
export function fmtDate(ts, lang = 'ca') {
  const d = new Date(ts * 1000);
  try {
    const locale = { ca: 'ca-ES', es: 'es-ES', en: 'en-GB' }[lang] || 'ca-ES';
    return new Intl.DateTimeFormat(locale, { timeZone: 'Europe/Madrid', day: '2-digit', month: '2-digit', year: 'numeric' }).format(d);
  } catch {
    return d.toISOString().slice(0, 10);
  }
}

// Página HTML mínima; `inner` ya debe venir escapado. `refresh` = URL para meta refresh a los 3 s.
export function page(lang, title, inner, { refresh } = {}) {
  const l = MAIL[lang] ? lang : 'ca';
  return (
    `<!doctype html><html lang="${l}"><head><meta charset="utf-8">` +
    '<meta name="viewport" content="width=device-width,initial-scale=1">' +
    (refresh ? `<meta http-equiv="refresh" content="3;url=${esc(refresh)}">` : '') +
    `<title>${esc(title)}</title>` +
    '<style>body{font:16px/1.5 system-ui,sans-serif;max-width:40rem;margin:3rem auto;padding:0 1rem;color:#222}' +
    'form{display:inline-block;margin:.5rem 1rem .5rem 0}button{font:inherit;padding:.5rem 1rem;cursor:pointer}' +
    '.danger{color:#a00}</style></head><body>' +
    `<h1>${esc(title)}</h1>${inner}</body></html>`
  );
}

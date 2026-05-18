/* HACCP Monitor — Origine pays (helpers partagés)
   Charger ce script AVANT le module de page qui appelle PAYS_UE / origineCode().
*/

const PAYS_UE = [
  'France', 'Allemagne', 'Autriche', 'Belgique', 'Bulgarie',
  'Chypre', 'Croatie', 'Danemark', 'Espagne', 'Estonie',
  'Finlande', 'Grèce', 'Hongrie', 'Irlande', 'Italie',
  'Lettonie', 'Lituanie', 'Luxembourg', 'Malte', 'Pays-Bas',
  'Pologne', 'Portugal', 'République tchèque', 'Roumanie',
  'Slovaquie', 'Slovénie', 'Suède',
];

const PAYS_CODES = {
  'france': 'FR', 'allemagne': 'DE', 'autriche': 'AT', 'belgique': 'BE',
  'bulgarie': 'BG', 'chypre': 'CY', 'croatie': 'HR', 'danemark': 'DK',
  'espagne': 'ES', 'estonie': 'EE', 'finlande': 'FI',
  'grece': 'GR', 'grèce': 'GR',
  'hongrie': 'HU', 'irlande': 'IE', 'italie': 'IT',
  'lettonie': 'LV', 'lituanie': 'LT', 'luxembourg': 'LU', 'malte': 'MT',
  'pays-bas': 'NL', 'paysbas': 'NL', 'hollande': 'NL',
  'pologne': 'PL', 'portugal': 'PT',
  'republique tcheque': 'CZ', 'république tchèque': 'CZ',
  'tchequie': 'CZ', 'tchéquie': 'CZ',
  'roumanie': 'RO', 'slovaquie': 'SK',
  'slovenie': 'SI', 'slovénie': 'SI',
  'suede': 'SE', 'suède': 'SE',
  'royaume-uni': 'UK', 'royaume uni': 'UK', 'angleterre': 'UK',
  'grande-bretagne': 'UK', 'uk': 'UK',
  'suisse': 'CH', 'norvege': 'NO', 'norvège': 'NO', 'islande': 'IS',
  'etats-unis': 'US', 'états-unis': 'US', 'usa': 'US',
  'canada': 'CA', 'argentine': 'AR',
  'bresil': 'BR', 'brésil': 'BR',
  'australie': 'AU',
  'nouvelle-zelande': 'NZ', 'nouvelle-zélande': 'NZ',
  'japon': 'JP', 'chine': 'CN',
  'maroc': 'MA', 'algerie': 'DZ', 'algérie': 'DZ', 'tunisie': 'TN',
};

function origineCode(nom) {
  if (!nom) return '';
  const norm = String(nom).trim().toLowerCase()
    .normalize('NFD').replace(/[̀-ͯ]/g, '');
  if (!norm) return '';
  if (PAYS_CODES[norm]) return PAYS_CODES[norm];
  const sans = norm.replace(/\s+/g, '');
  if (PAYS_CODES[sans]) return PAYS_CODES[sans];
  // Si la saisie est déjà un code court (2-3 lettres), on l'utilise
  const up = String(nom).trim().toUpperCase();
  if (/^[A-Z]{2,3}$/.test(up)) return up;
  // Fallback : 2 premières lettres alpha en majuscule
  const lettres = String(nom).replace(/[^A-Za-zÀ-ÿ]/g, '').slice(0, 2).toUpperCase();
  return lettres || '?';
}

function origineLabel(nom) {
  const code = origineCode(nom);
  return code ? `Origine : ${code}` : '';
}

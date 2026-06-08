/* familles.js — Référentiel famille / sous-famille partagé entre catalogue achats et vente */

const FAMILLES = {
  'Viande':               ['Boeuf', 'Veau', 'Agneau', 'Porc', 'Volaille', 'Cheval'],
  'Charcuterie':          ['Jambon', 'Pâté, Terrine et Rillette', 'Salaison et Pièce séchée',
                           'Saucisse à cuire et Saucisson cuit', 'Spécialité charcutière'],
  'Traiteur':             ['Crudité', 'Fromage', 'Plat préparé', 'Accompagnement', 'Pané', 'Dessert'],
  'Aide culinaire':       ['Épices et Aromates', 'Boyaux et Ficellerie', 'Marinades, Sauces et huile',
                           'Bases et Liants', 'Fruits secs et Inclusions', 'Alcools de cuisson'],
  'Hygiène et emballage': ['Hygiène', 'Emballage'],
};

/**
 * Remplit un <select> famille et, si fourni, remet à zéro le <select> sous-famille.
 * @param {HTMLSelectElement} selFamille
 * @param {HTMLSelectElement|null} selSousFamille
 * @param {string} valeurActuelle  — valeur à présélectionner
 */
function peuplerSelectFamille(selFamille, selSousFamille, valeurActuelle = '') {
  selFamille.innerHTML = '<option value="">— Famille —</option>';
  for (const fam of Object.keys(FAMILLES)) {
    const opt = document.createElement('option');
    opt.value = fam;
    opt.textContent = fam;
    if (fam === valeurActuelle) opt.selected = true;
    selFamille.appendChild(opt);
  }
  if (selSousFamille) {
    majSousFamille(selFamille.value, selSousFamille, '');
  }
}

/**
 * Recharge le <select> sous-famille en fonction de la famille choisie.
 * @param {string} famille
 * @param {HTMLSelectElement} selSousFamille
 * @param {string} valeurActuelle  — valeur à présélectionner
 */
function majSousFamille(famille, selSousFamille, valeurActuelle = '') {
  const sousFamilles = FAMILLES[famille] || [];
  selSousFamille.innerHTML = '<option value="">— Sous-famille —</option>';
  for (const sf of sousFamilles) {
    const opt = document.createElement('option');
    opt.value = sf;
    opt.textContent = sf;
    if (sf === valeurActuelle) opt.selected = true;
    selSousFamille.appendChild(opt);
  }
  selSousFamille.disabled = sousFamilles.length === 0;
}

/* mentions-etiquette.js — Bloc « Étiquette prix » d'un formulaire de produit de vente :
   case « Fait maison » + mentions (AOP, IGP, Label Rouge…), 2 au maximum.

   Utilisé par les fenêtres « Créer le produit de vente » (catalogue achats et popup de
   la réception). Liste des mentions = miroir de brother_ql_prix.MENTIONS_ORDRE.

     const bloc = MentionsEtiquette.monter(conteneur);
     bloc.ecrire({ fait_maison: false, mentions: [] });   // remise à zéro
     bloc.lire();   // → { fait_maison: true, mentions: ['label_rouge', 'local'] }
   Article d'ACHAT : MentionsEtiquette.monter(conteneur, { faitMaison: false }) — un produit
   acheté n'est pas « fait maison » ; ses mentions sont reprises par le produit de vente.
*/
window.MentionsEtiquette = (function () {
  const MENTIONS = [
    { cle: 'aop',          libelle: 'AOP' },
    { cle: 'igp',          libelle: 'IGP' },
    { cle: 'label_rouge',  libelle: 'Label Rouge' },
    { cle: 'artisanal',    libelle: 'Artisanal' },
    { cle: 'sans_nitrite', libelle: 'Sans nitrite ajouté' },
    { cle: 'local',        libelle: 'Local' },
    { cle: 'race_viande',  libelle: 'Race à viande' },
  ];
  const MAX = 2;
  const CASE = 'width:18px;height:18px;accent-color:var(--color-accent);';

  function monter(conteneur, { faitMaison = true } = {}) {
    conteneur.innerHTML = `
      <label style="display:${faitMaison ? 'flex' : 'none'};align-items:center;gap:8px;margin:var(--space-2, 8px) 0 6px;font-weight:400;">
        <input type="checkbox" class="me-fait-maison" style="${CASE}">
        🏠 Fait maison (logo sur ses étiquettes prix)
      </label>
      <div style="font-weight:600;${faitMaison ? '' : 'margin-top:var(--space-2, 8px);'}">${faitMaison
        ? 'Mentions sur l\'étiquette prix' : 'Mentions (labels)'}
        <span style="font-weight:400;color:#6b7280;">(2 au maximum — AOP, IGP, Label Rouge
          seulement si le produit est certifié)</span></div>
      <div style="display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:4px;">
        ${MENTIONS.map(m => `
          <label style="display:flex;align-items:center;gap:6px;margin:0;font-weight:400;">
            <input type="checkbox" class="me-mention" value="${m.cle}" style="${CASE}"> ${m.libelle}
          </label>`).join('')}
      </div>`;
    const cases = () => [...conteneur.querySelectorAll('.me-mention')];
    // 2 mentions au maximum : les autres cases se grisent dès que 2 sont cochées.
    const majMax = () => {
      const pleines = cases().filter(c => c.checked).length >= MAX;
      cases().forEach(c => { c.disabled = pleines && !c.checked; });
    };
    conteneur.addEventListener('change', majMax);
    return {
      lire() {
        const mentions = cases().filter(c => c.checked).map(c => c.value);
        return faitMaison
          ? { fait_maison: conteneur.querySelector('.me-fait-maison').checked, mentions }
          : { mentions };
      },
      ecrire({ fait_maison = false, mentions = [] } = {}) {
        conteneur.querySelector('.me-fait-maison').checked = !!fait_maison;
        const choisies = new Set(mentions || []);
        cases().forEach(c => { c.checked = choisies.has(c.value); });
        majMax();
      },
    };
  }

  return { MENTIONS, MAX, monter };
})();

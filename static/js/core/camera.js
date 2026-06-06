/* HACCP Monitor — Module caméra réutilisable
 *
 * Problème ciblé : sur tablette Windows (Surface Go) avec Edge, un
 * <input type="file" accept="image/*" capture="environment"> n'ouvre pas
 * la caméra mais propose seulement de choisir un fichier.
 *
 * Solution : on intercepte le clic sur la zone photo et on propose un choix :
 *   📷 Prendre une photo  → flux caméra in-app (getUserMedia), fiable partout
 *   🖼️ Choisir un fichier → input.click() natif (galerie / explorateur)
 *
 * Dans les deux cas, le résultat est injecté dans l'<input> cible via un
 * DataTransfer, puis l'évènement `change` est déclenché : tout le code aval
 * qui lit input.files[0] fonctionne sans modification.
 *
 * API : window.ouvrirChoixPhoto(inputEl)
 */
(function () {
  'use strict';

  const supportCamera = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);

  /* Injecte un File dans un <input type=file> et déclenche `change`. */
  function injecterFichier(input, file) {
    const dt = new DataTransfer();
    dt.items.add(file);
    input.files = dt.files;
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  /* Ouvre le sélecteur de fichier natif (sans forcer la caméra). */
  function choisirFichier(input) {
    const capture = input.getAttribute('capture');
    input.removeAttribute('capture');
    input.click();
    // Restaure l'attribut pour ne pas changer le comportement par défaut ailleurs.
    if (capture !== null) {
      const restore = () => {
        input.setAttribute('capture', capture);
        input.removeEventListener('change', restore);
        window.removeEventListener('focus', restore);
      };
      input.addEventListener('change', restore, { once: true });
      window.addEventListener('focus', restore, { once: true });
    }
  }

  /* ── Feuille de choix ── */
  function ouvrirChoixPhoto(input) {
    // Si la caméra n'est pas dispo, comportement natif direct.
    if (!supportCamera) { input.click(); return; }

    const sheet = document.createElement('div');
    sheet.className = 'cam-sheet';
    sheet.innerHTML = `
      <div class="cam-sheet-backdrop"></div>
      <div class="cam-sheet-panel" role="dialog" aria-label="Ajouter une photo">
        <button type="button" class="cam-sheet-opt" data-act="cam">
          <span class="cam-sheet-ico">📷</span> Prendre une photo
        </button>
        <button type="button" class="cam-sheet-opt" data-act="file">
          <span class="cam-sheet-ico">🖼️</span> Choisir un fichier
        </button>
        <button type="button" class="cam-sheet-opt cam-sheet-annuler" data-act="cancel">
          Annuler
        </button>
      </div>`;
    document.body.appendChild(sheet);

    function fermer() { sheet.remove(); }

    sheet.addEventListener('click', e => {
      const act = e.target.closest('[data-act]')?.dataset.act
        || (e.target.classList.contains('cam-sheet-backdrop') ? 'cancel' : null);
      if (!act) return;
      fermer();
      if (act === 'cam') ouvrirCamera(input);
      else if (act === 'file') choisirFichier(input);
    });
  }

  /* ── Overlay caméra plein écran ── */
  async function ouvrirCamera(input) {
    const overlay = document.createElement('div');
    overlay.className = 'cam-overlay';
    overlay.innerHTML = `
      <video class="cam-video" autoplay playsinline muted></video>
      <div class="cam-barre">
        <button type="button" class="cam-btn cam-annuler" aria-label="Annuler">✕</button>
        <button type="button" class="cam-declencheur" aria-label="Prendre la photo"></button>
        <button type="button" class="cam-btn cam-switch" aria-label="Changer de caméra">🔄</button>
      </div>
      <div class="cam-erreur" hidden></div>`;
    document.body.appendChild(overlay);

    const video   = overlay.querySelector('.cam-video');
    const elErr   = overlay.querySelector('.cam-erreur');
    const btnAnn  = overlay.querySelector('.cam-annuler');
    const btnDecl = overlay.querySelector('.cam-declencheur');
    const btnSw   = overlay.querySelector('.cam-switch');

    let stream = null;
    let facing = 'environment';

    function stopStream() {
      if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
    }
    function fermer() { stopStream(); overlay.remove(); }

    async function demarrer() {
      stopStream();
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: facing } },
          audio: false,
        });
        video.srcObject = stream;
        elErr.hidden = true;
      } catch (err) {
        // Échec caméra → on retombe sur le sélecteur de fichier.
        elErr.textContent = "Caméra indisponible. Ouverture du sélecteur de fichier…";
        elErr.hidden = false;
        setTimeout(() => { fermer(); choisirFichier(input); }, 1200);
      }
    }

    btnAnn.addEventListener('click', fermer);

    btnSw.addEventListener('click', () => {
      facing = facing === 'environment' ? 'user' : 'environment';
      demarrer();
    });

    btnDecl.addEventListener('click', () => {
      if (!stream) return;
      const track = stream.getVideoTracks()[0];
      const settings = track ? track.getSettings() : {};
      const w = settings.width  || video.videoWidth  || 1280;
      const h = settings.height || video.videoHeight || 720;
      const canvas = document.createElement('canvas');
      canvas.width = w;
      canvas.height = h;
      canvas.getContext('2d').drawImage(video, 0, 0, w, h);
      canvas.toBlob(blob => {
        if (!blob) return;
        const file = new File([blob], `photo-${Date.now()}.jpg`, { type: 'image/jpeg' });
        fermer();
        injecterFichier(input, file);
      }, 'image/jpeg', 0.92);
    });

    demarrer();
  }

  window.ouvrirChoixPhoto = ouvrirChoixPhoto;
})();

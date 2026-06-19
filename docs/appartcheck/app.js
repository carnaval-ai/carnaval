/* =====================================================================
   AppartCheck - Visit Companion & Checklist App
   Core Javascript: app.js
   Features: IndexedDB storage, SPA Routing, Photo Compression, 
   Score Computation, Web Share API, Offline Mode, Dark Mode.
   ===================================================================== */

// ---- Database layer (IndexedDB Wrapper) ----
const dbStore = {
  db: null,
  dbName: 'VisiteAppartementDB',
  storeName: 'store',
  
  init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, 1);
      
      request.onupgradeneeded = e => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains(this.storeName)) {
          db.createObjectStore(this.storeName);
        }
      };
      
      request.onsuccess = e => {
        this.db = e.target.result;
        resolve();
      };
      
      request.onerror = e => {
        console.error('IndexedDB failed to initialize:', e.target.error);
        reject(e.target.error);
      };
    });
  },
  
  get(key) {
    return new Promise((resolve, reject) => {
      if (!this.db) return resolve(null);
      const transaction = this.db.transaction([this.storeName], 'readonly');
      const store = transaction.objectStore(this.storeName);
      const request = store.get(key);
      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => reject(request.error);
    });
  },
  
  set(key, value) {
    return new Promise((resolve, reject) => {
      if (!this.db) return resolve();
      const transaction = this.db.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.put(value, key);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  },
  
  del(key) {
    return new Promise((resolve, reject) => {
      if (!this.db) return resolve();
      const transaction = this.db.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.delete(key);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  },

  async clearAll() {
    return new Promise((resolve, reject) => {
      if (!this.db) return resolve();
      const transaction = this.db.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.clear();
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }
};

// ---- App Data & Configuration ----
const SECTIONS = [
  {
    id: 'ext',
    title: '1 - Extérieur et quartier',
    icon: '🏢',
    items: [
      "Distance à pied jusqu'au lycée Vinci",
      "Arrêt de bus et fréquence",
      "Commerces de proximité",
      "Bruit de la rue",
      "Sécurité et éclairage le soir",
      "Stationnement vélo et voiture"
    ]
  },
  {
    id: 'com',
    title: '2 - Parties communes',
    icon: '🔑',
    items: [
      "Propreté hall, escaliers, ascenseur",
      "Boîtes aux lettres",
      "Local poubelles et vélos",
      "Interphone ou digicode",
      "Étage et ascenseur"
    ]
  },
  {
    id: 'ent',
    title: '3 - Entrée et état général',
    icon: '🚪',
    items: [
      "Porte et serrure solides",
      "Luminosité générale",
      "Aération générale (odeurs, renouvellement d'air)",
      "Traces de moisissure murs et plafonds",
      "État des sols et peintures"
    ]
  },
  {
    id: 'sej',
    title: '4 - Séjour et espace commun',
    icon: '🛋️',
    items: [
      "Surface suffisante pour deux",
      "Meublé ou non, état des meubles",
      "Fenêtres et orientation",
      "Chauffage dans la pièce",
      "Nombre de prises électriques",
      "Luminosité pour travailler sur PC (jour + éclairage)",
      "Place pour un coin bureau (table, prise à côté)",
      "Réception WiFi dans le séjour",
      "Machine à laver ou emplacement (arrivée/évacuation eau)",
      "Espace pour sécher le linge (étendoir, balcon)"
    ]
  },
  {
    id: 'cui',
    title: '5 - Cuisine',
    icon: '🍳',
    items: [
      "Électroménager fourni (plaques, four, frigo, hotte)",
      "Appareils testés et fonctionnels",
      "Plan de travail et rangements pour deux",
      "Pression de l'eau chaude et froide",
      "Qualité de l'eau (couleur, odeur)",
      "Évier et robinetterie sans fuite",
      "Aération ou hotte fonctionnelle"
    ]
  },
  {
    id: 'sdb',
    title: '6 - Salle de bain et WC',
    icon: '🚿',
    items: [
      "WC séparé ou dans la SDB",
      "Chasse d'eau fonctionnelle",
      "Ventilation et absence d'odeurs",
      "Pression de la douche testée",
      "Température eau chaude correcte",
      "VMC ou fenêtre pour aération",
      "Joints et sanitaires en bon état",
      "Rangement pour deux"
    ]
  },
  {
    id: 'cha',
    title: '7 - Les deux chambres',
    icon: '🛏️',
    items: [
      "Surfaces équivalentes ou écart noté",
      "Mobilier complet (lit, bureau, armoire)",
      "Fenêtre et luminosité dans chaque chambre",
      "Chauffage fonctionnel dans chaque",
      "Prises électriques près du lit et du bureau",
      "Verrou sur chaque porte de chambre",
      "Isolation au bruit entre les chambres",
      "Qualité de la literie (matelas et sommier)",
      "Luminosité pour le travail PC (sans reflets)",
      "Réception WiFi stable dans chaque chambre"
    ]
  },
  {
    id: 'tec',
    title: '8 - Points techniques',
    icon: '⚡',
    items: [
      "Type de chauffage (électrique, gaz, collectif) et payeur",
      "Double vitrage sur tous les ouvrants",
      "Classe DPE relevée (souvent D ou pire)",
      "Présence et fermeture des volets",
      "Présence de rideaux ou stores",
      "Éligibilité Fibre Optique vérifiée à l'adresse",
      "Compteurs individuels (eau, électricité)",
      "État du tableau électrique",
      "Emplacement de la prise fibre (départ WiFi)"
    ]
  },
  {
    id: 'col',
    title: '9 - Colocation à deux',
    icon: '🤝',
    items: [
      "Type de bail (unique/solidaire ou baux individuels)",
      "Clause de solidarité et impact",
      "Répartition des charges",
      "Dossiers garants ou Visale accepté",
      "Règles en cas de départ d'une colocataire"
    ]
  },
  {
    id: 'bai',
    title: '10 - Questions au bailleur',
    icon: '💬',
    items: [
      "Loyer exact charges comprises et détail",
      "Dépôt de garantie demandé",
      "Durée et type de bail",
      "Assurance habitation requise",
      "Délai de préavis pour partir",
      "Date de disponibilité effective"
    ]
  }
];

const TOTAL_ITEMS = SECTIONS.reduce((acc, sec) => acc + sec.items.length, 0);

// ---- Global State ----
let index = [];
let currentAptId = null;
let aptState = null;
let activeTab = 'checklist'; // 'checklist', 'summary', 'photos'
let activeSections = {}; // tracker for collapsed accordion sections
let theme = 'light';
let pendingSection = null;

// ---- DOM Elements ----
const appEl = document.getElementById('app');
const titleEl = document.getElementById('title');
const subtitleEl = document.getElementById('subtitle');
const backBtn = document.getElementById('backBtn');
const themeToggleBtn = document.getElementById('themeToggleBtn');

// ---- Utilities ----
function uid() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

function esc(str) {
  return (str || '').replace(/[&<>"]/g, c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;'
  }[c]));
}

function toast(message) {
  const t = document.getElementById('toast');
  t.textContent = message;
  t.classList.add('show');
  clearTimeout(t._timeout);
  t._timeout = setTimeout(() => t.classList.remove('show'), 2000);
}

// ---- Score and Stats Calculations ----
function getStats(state) {
  if (!state) return { done: 0, ok: 0, nok: 0, na: 0, score: 0 };
  let ok = 0, nok = 0, na = 0;
  
  Object.values(state.states || {}).forEach(val => {
    if (val === 'ok') ok++;
    else if (val === 'nok') nok++;
    else if (val === 'na') na++;
  });
  
  const done = ok + nok + na;
  const scored = ok + nok;
  const score = scored > 0 ? Math.round((ok / scored) * 100) : 0;
  
  return { done, ok, nok, na, score };
}

// ---- Theme management ----
async function initTheme() {
  theme = (await dbStore.get('settings_theme')) || 'light';
  document.documentElement.setAttribute('data-theme', theme);
  updateThemeIcon();
}

async function toggleTheme() {
  theme = theme === 'light' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', theme);
  await dbStore.set('settings_theme', theme);
  updateThemeIcon();
  toast(theme === 'light' ? 'Mode Clair' : 'Mode Sombre');
}

function updateThemeIcon() {
  if (theme === 'dark') {
    themeToggleBtn.innerHTML = `<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m12.728 0l-.707-.707M6.343 6.343l-.707-.707M14 12a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>`;
  } else {
    themeToggleBtn.innerHTML = `<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path></svg>`;
  }
}

themeToggleBtn.onclick = toggleTheme;

// ---- Data Load & Save Operations ----
async function loadIndex() {
  const data = await dbStore.get('apt_index');
  index = data ? JSON.parse(data) : [];
}

async function saveIndex() {
  await dbStore.set('apt_index', JSON.stringify(index));
}

function getEmptyState() {
  return {
    states: {},
    comments: {},
    photos: []
  };
}

async function loadApt(id) {
  const data = await dbStore.get('apt_' + id);
  aptState = data ? JSON.parse(data) : getEmptyState();
  aptState.states = aptState.states || {};
  aptState.comments = aptState.comments || {};
  aptState.photos = aptState.photos || [];
}

async function saveApt() {
  if (currentAptId && aptState) {
    await dbStore.set('apt_' + currentAptId, JSON.stringify(aptState));
  }
}

// ---- Routing ----
async function goHome() {
  await saveApt();
  currentAptId = null;
  aptState = null;
  renderHome();
}

// ---- RENDER HOME PAGE ----
async function renderHome() {
  backBtn.style.display = 'none';
  titleEl.textContent = 'Mes Visites';
  subtitleEl.textContent = 'Appartements à louer';
  
  await loadIndex();
  
  // Calculate aggregated statistics
  let totalApartments = index.length;
  let totalPhotos = 0;
  let totalNok = 0;
  let averageScore = 0;
  let scoreCount = 0;
  
  const cardElements = [];
  
  for (const item of index) {
    const data = await dbStore.get('apt_' + item.id);
    const state = data ? JSON.parse(data) : getEmptyState();
    const stats = getStats(state);
    
    totalPhotos += (state.photos || []).length;
    totalNok += stats.nok;
    if (stats.ok + stats.nok > 0) {
      averageScore += stats.score;
      scoreCount++;
    }
    
    cardElements.push({
      item,
      stats,
      photoCount: (state.photos || []).length
    });
  }
  
  const avgScoreVal = scoreCount > 0 ? Math.round(averageScore / scoreCount) : 0;
  
  let html = '';
  
  // Stats summary banner
  if (totalApartments > 0) {
    let scoreClass = 'score-mid';
    if (avgScoreVal >= 75) scoreClass = 'score-high';
    else if (avgScoreVal < 50) scoreClass = 'score-low';
    
    html += `
      <div class="card" style="background: var(--primary-gradient); color: #fff; border: none; margin-bottom: 20px;">
        <h3 style="margin-bottom: 8px;">Vue d'ensemble</h3>
        <div class="card-stats">
          <div class="stat-item" style="background: rgba(255,255,255,0.1); color: #fff;">
            Visites <span class="val" style="color:#fff;">${totalApartments}</span>
          </div>
          <div class="stat-item ${scoreClass}" style="background: rgba(255,255,255,0.1); color: #fff;">
            Score Moyen <span class="val" style="color:#fff;">${avgScoreVal}%</span>
          </div>
          <div class="stat-item" style="background: rgba(255,255,255,0.1); color: #fff;">
            Photos <span class="val" style="color:#fff;">${totalPhotos}</span>
          </div>
        </div>
      </div>
    `;
  }
  
  // Search bar
  html += `
    <div class="form-group" style="margin-bottom: 16px;">
      <input id="searchInput" placeholder="🔍 Rechercher un appartement..." style="border-radius: var(--radius-md); box-shadow: var(--shadow-sm);">
    </div>
  `;
  
  // Apartment cards
  html += `<div id="apartmentsList">`;
  if (totalApartments === 0) {
    html += `
      <div class="empty">
        <svg fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h18M10.5 3h3.75a1.125 1.125 0 011.125 1.125V21"></path></svg>
        <span>Aucun appartement enregistré pour le moment.</span>
      </div>
    `;
  } else {
    cardElements.forEach(data => {
      const pct = Math.round(data.stats.done / TOTAL_ITEMS * 100);
      const isComplete = data.stats.done === TOTAL_ITEMS;
      
      let priceInfo = '';
      if (data.item.price) {
        priceInfo += ` • ${data.item.price} €/mois`;
      }
      if (data.item.surface) {
        priceInfo += ` (${data.item.surface} m²)`;
      }
      
      html += `
        <div class="card interactive" data-id="${data.item.id}" data-search-target="${esc(data.item.name).toLowerCase()} ${esc(data.item.address).toLowerCase()}">
          <div class="row">
            <h3>${esc(data.item.name)}</h3>
            <span class="pill ${isComplete ? 'ok' : 'primary'}">${data.stats.done}/${TOTAL_ITEMS}</span>
          </div>
          <p class="sub">${esc(data.item.address || 'Pas d\'adresse renseignée')}${priceInfo}</p>
          <div class="progress-container">
            <div class="bar"><span style="width: ${pct}%"></span></div>
          </div>
          <div class="row" style="margin-top: 10px;">
            <div style="display: flex; gap: 6px;">
              <span class="pill ${data.stats.nok > 0 ? 'nok' : ''}">${data.stats.nok} NOK</span>
              <span class="pill">${data.photoCount} 📷</span>
            </div>
            <span class="pill ok" style="font-size:14px; font-weight:800; padding: 4px 10px;">${data.stats.score}% Match</span>
          </div>
        </div>
      `;
    });
  }
  html += `</div>`;
  
  // Backup buttons & actions
  html += `
    <div style="display: flex; gap: 12px; margin-top: 24px;">
      <button class="btn secondary" id="exportBtn" style="flex: 1;">
        <svg style="width:18px;height:18px;" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"></path></svg>
        Exporter
      </button>
      <button class="btn secondary" id="importBtn" style="flex: 1;">
        <svg style="width:18px;height:18px;" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"></path></svg>
        Importer
      </button>
    </div>
    
    <button class="fab" id="fabAdd" aria-label="Ajouter une visite">
      <svg fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15"></path></svg>
    </button>
  `;
  
  appEl.innerHTML = html;
  
  // Set up event listeners
  document.getElementById('fabAdd').onclick = renderNew;
  document.getElementById('exportBtn').onclick = exportAll;
  document.getElementById('importBtn').onclick = () => document.getElementById('importInput').click();
  
  // Interactive cards
  appEl.querySelectorAll('[data-id]').forEach(card => {
    card.onclick = () => openApt(card.getAttribute('data-id'));
  });
  
  // Search filter
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.oninput = () => {
      const q = searchInput.value.toLowerCase().trim();
      const cards = document.querySelectorAll('#apartmentsList > .card');
      cards.forEach(card => {
        const text = card.getAttribute('data-search-target');
        if (text.includes(q)) {
          card.style.display = 'block';
        } else {
          card.style.display = 'none';
        }
      });
    };
  }
}

// ---- RENDER NEW VISITE FORM ----
function renderNew() {
  backBtn.style.display = '';
  backBtn.onclick = goHome;
  titleEl.textContent = 'Nouvel Appartement';
  subtitleEl.textContent = 'Création de fiche';
  
  appEl.innerHTML = `
    <div class="card" style="cursor: default;">
      <h3 style="margin-bottom: 16px;">Caractéristiques</h3>
      
      <div class="form-group">
        <label for="nName">Repère / Nom court (obligatoire)</label>
        <input id="nName" placeholder="ex: T3 Résidence des Lys">
      </div>
      
      <div class="form-group">
        <label for="nAddr">Adresse complète</label>
        <input id="nAddr" placeholder="ex: 14 Rue de la Paix, Nantes">
      </div>
      
      <div style="display: flex; gap: 12px;">
        <div class="form-group" style="flex: 1;">
          <label for="nPrice">Loyer mensuel (€ CC)</label>
          <input id="nPrice" type="number" inputmode="numeric" placeholder="ex: 650">
        </div>
        <div class="form-group" style="flex: 1;">
          <label for="nSurface">Surface (m²)</label>
          <input id="nSurface" type="number" inputmode="numeric" placeholder="ex: 54">
        </div>
      </div>
      
      <div class="form-group">
        <label for="nContact">Contact (Agence / Propriétaire)</label>
        <input id="nContact" placeholder="ex: Agence Blot / M. Martin">
      </div>
      
      <div class="form-group">
        <label for="nPhone">Téléphone du contact</label>
        <input id="nPhone" type="tel" inputmode="tel" placeholder="ex: 06 12 34 56 78">
      </div>
    </div>
    
    <button class="btn" id="createBtn">Créer la fiche</button>
  `;
  
  document.getElementById('nName').focus();
  
  document.getElementById('createBtn').onclick = async () => {
    const name = document.getElementById('nName').value.trim();
    const address = document.getElementById('nAddr').value.trim();
    const price = document.getElementById('nPrice').value.trim();
    const surface = document.getElementById('nSurface').value.trim();
    const contact = document.getElementById('nContact').value.trim();
    const phone = document.getElementById('nPhone').value.trim();
    
    if (!name) {
      toast('Veuillez renseigner au moins un repère.');
      return;
    }
    
    const id = uid();
    index.unshift({
      id,
      name,
      address,
      price: price ? parseInt(price, 10) : '',
      surface: surface ? parseInt(surface, 10) : '',
      contact,
      phone,
      created: Date.now()
    });
    
    await saveIndex();
    await dbStore.set('apt_' + id, JSON.stringify(getEmptyState()));
    
    toast('Appartement ajouté !');
    openApt(id);
  };
}

// ---- RENDER EDIT VISITE FORM ----
function renderEdit(id) {
  const aptInfo = index.find(x => x.id === id);
  if (!aptInfo) return goHome();
  
  backBtn.style.display = '';
  backBtn.onclick = () => openApt(id);
  titleEl.textContent = 'Modifier';
  subtitleEl.textContent = aptInfo.name;
  
  appEl.innerHTML = `
    <div class="card" style="cursor: default;">
      <h3 style="margin-bottom: 16px;">Détails de l'appartement</h3>
      
      <div class="form-group">
        <label for="eName">Repère / Nom court (obligatoire)</label>
        <input id="eName" value="${esc(aptInfo.name)}">
      </div>
      
      <div class="form-group">
        <label for="eAddr">Adresse complète</label>
        <input id="eAddr" value="${esc(aptInfo.address)}">
      </div>
      
      <div style="display: flex; gap: 12px;">
        <div class="form-group" style="flex: 1;">
          <label for="ePrice">Loyer mensuel (€ CC)</label>
          <input id="ePrice" type="number" inputmode="numeric" value="${aptInfo.price || ''}">
        </div>
        <div class="form-group" style="flex: 1;">
          <label for="eSurface">Surface (m²)</label>
          <input id="eSurface" type="number" inputmode="numeric" value="${aptInfo.surface || ''}">
        </div>
      </div>
      
      <div class="form-group">
        <label for="eContact">Contact (Agence / Propriétaire)</label>
        <input id="eContact" value="${esc(aptInfo.contact)}">
      </div>
      
      <div class="form-group">
        <label for="ePhone">Téléphone du contact</label>
        <input id="ePhone" type="tel" inputmode="tel" value="${esc(aptInfo.phone)}">
      </div>
    </div>
    
    <button class="btn" id="saveEditBtn">Enregistrer les modifications</button>
    <button class="btn secondary" id="cancelEditBtn" style="margin-top: 10px;">Annuler</button>
  `;
  
  document.getElementById('cancelEditBtn').onclick = () => openApt(id);
  
  document.getElementById('saveEditBtn').onclick = async () => {
    const name = document.getElementById('eName').value.trim();
    const address = document.getElementById('eAddr').value.trim();
    const price = document.getElementById('ePrice').value.trim();
    const surface = document.getElementById('eSurface').value.trim();
    const contact = document.getElementById('eContact').value.trim();
    const phone = document.getElementById('ePhone').value.trim();
    
    if (!name) {
      toast('Veuillez renseigner au moins un repère.');
      return;
    }
    
    const item = index.find(x => x.id === id);
    if (item) {
      item.name = name;
      item.address = address;
      item.price = price ? parseInt(price, 10) : '';
      item.surface = surface ? parseInt(surface, 10) : '';
      item.contact = contact;
      item.phone = phone;
    }
    
    await saveIndex();
    toast('Modifications enregistrées !');
    openApt(id);
  };
}

// ---- OPEN APARTMENT DETAIL PAGE ----
async function openApt(id) {
  currentAptId = id;
  await loadApt(id);
  
  const aptInfo = index.find(x => x.id === id);
  if (!aptInfo) return goHome();
  
  backBtn.style.display = '';
  backBtn.onclick = goHome;
  titleEl.textContent = aptInfo.name;
  
  let subText = esc(aptInfo.address || 'Pas d\'adresse');
  if (aptInfo.price) subText += ` • ${aptInfo.price} €/mois`;
  subtitleEl.innerHTML = subText;
  
  renderAptShell(aptInfo);
  renderTabContent();
}

function renderAptShell(aptInfo) {
  let quickActions = '';
  if (aptInfo.phone) {
    const cleanPhone = aptInfo.phone.replace(/[^+0-9]/g, '');
    quickActions += `
      <a href="tel:${cleanPhone}" class="btn-quick-call">
        <svg style="width:16px;height:16px;" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-2.824-1.802-5.122-4.1-6.924-6.924l1.293-.97a1.125 1.125 0 00.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z"></path></svg>
        Appeler
      </a>
      <a href="sms:${cleanPhone}" class="btn-quick-sms">
        <svg style="width:16px;height:16px;" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z"></path></svg>
        SMS
      </a>
    `;
  }
  if (aptInfo.address) {
    quickActions += `
      <a href="https://maps.google.com/?q=${encodeURIComponent(aptInfo.address)}" target="_blank" class="btn-quick-map">
        <svg style="width:16px;height:16px;" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z"></path></svg>
        Itinéraire
      </a>
    `;
  }
  
  appEl.innerHTML = `
    <!-- Contact & Quick Info Banner -->
    <div class="card" style="cursor: default; padding: 12px 14px; margin-bottom: 12px;">
      <div style="font-size: 13px; color: var(--text-muted);">
        <strong>Contact :</strong> ${esc(aptInfo.contact || 'Non renseigné')} ${aptInfo.phone ? `(${esc(aptInfo.phone)})` : ''}
      </div>
      ${quickActions ? `<div class="contact-quick-actions">${quickActions}</div>` : ''}
    </div>
    
    <!-- Tab Navigation -->
    <div class="tab-nav">
      <button class="${activeTab === 'checklist' ? 'active' : ''}" id="tab-checklist-btn">
        📋 Checklist
      </button>
      <button class="${activeTab === 'summary' ? 'active' : ''}" id="tab-summary-btn">
        📊 Synthèse
      </button>
      <button class="${activeTab === 'photos' ? 'active' : ''}" id="tab-photos-btn">
        📷 Photos
      </button>
    </div>
    
    <!-- Tab Contents -->
    <div id="tab-checklist" class="tab-content ${activeTab === 'checklist' ? 'active' : ''}"></div>
    <div id="tab-summary" class="tab-content ${activeTab === 'summary' ? 'active' : ''}"></div>
    <div id="tab-photos" class="tab-content ${activeTab === 'photos' ? 'active' : ''}"></div>
    
    <!-- Actions Bar -->
    <div style="margin-top: 24px; display: flex; flex-direction: column; gap: 10px;">
      <button class="btn secondary" id="editAptBtn">
        ✏️ Modifier les détails
      </button>
      <button class="btn danger" id="deleteAptBtn">
        🗑️ Supprimer cette visite
      </button>
    </div>
  `;
  
  // Tab click handlers
  document.getElementById('tab-checklist-btn').onclick = () => switchTab('checklist');
  document.getElementById('tab-summary-btn').onclick = () => switchTab('summary');
  document.getElementById('tab-photos-btn').onclick = () => switchTab('photos');
  
  // Action handlers
  document.getElementById('editAptBtn').onclick = () => renderEdit(aptInfo.id);
  document.getElementById('deleteAptBtn').onclick = async () => {
    if (!confirm('Supprimer définitivement cet appartement, ses réponses et toutes ses photos ?')) return;
    
    // Delete all photos associated
    for (const photo of (aptState.photos || [])) {
      await dbStore.del('photo_' + currentAptId + '_' + photo.pid);
    }
    // Delete apartment state
    await dbStore.del('apt_' + currentAptId);
    
    // Remove from index
    index = index.filter(x => x.id !== currentAptId);
    await saveIndex();
    
    toast('Appartement supprimé.');
    goHome();
  };
}

function switchTab(tabName) {
  activeTab = tabName;
  document.querySelectorAll('.tab-nav button').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  
  if (tabName === 'checklist') {
    document.getElementById('tab-checklist-btn').classList.add('active');
    document.getElementById('tab-checklist').classList.add('active');
  } else if (tabName === 'summary') {
    document.getElementById('tab-summary-btn').classList.add('active');
    document.getElementById('tab-summary').classList.add('active');
  } else if (tabName === 'photos') {
    document.getElementById('tab-photos-btn').classList.add('active');
    document.getElementById('tab-photos').classList.add('active');
  }
  
  renderTabContent();
}

async function renderTabContent() {
  if (activeTab === 'checklist') {
    renderChecklistTab();
  } else if (activeTab === 'summary') {
    renderSummaryTab();
  } else if (activeTab === 'photos') {
    renderPhotosTab();
  }
}

// ---- TAB 1: CHECKLIST RENDER ----
function renderChecklistTab() {
  const container = document.getElementById('tab-checklist');
  let html = '';
  
  SECTIONS.forEach(sec => {
    const isCollapsed = activeSections[sec.id] === true;
    
    // Count stats for this section specifically
    let secOk = 0, secNok = 0, secNa = 0;
    sec.items.forEach((_, i) => {
      const k = sec.id + '_' + i;
      const st = aptState.states[k];
      if (st === 'ok') secOk++;
      else if (st === 'nok') secNok++;
      else if (st === 'na') secNa++;
    });
    
    const answeredCount = secOk + secNok + secNa;
    const itemsTotal = sec.items.length;
    
    let badgeHtml = `<span class="pill">${answeredCount}/${itemsTotal}</span>`;
    if (secNok > 0) {
      badgeHtml += ` <span class="pill nok">${secNok} NOK</span>`;
    }
    
    const ph = (aptState.photos || []).filter(p => p.section === sec.id);
    let thumbsHtml = '';
    ph.forEach(p => {
      thumbsHtml += `
        <div class="thumb-wrapper" data-photo-id="${p.pid}">
          <img src="" alt="Photo" id="img-thumb-${p.pid}">
        </div>
      `;
    });
    
    html += `
      <div class="section ${isCollapsed ? 'collapsed' : ''}" id="section-card-${sec.id}">
        <div class="section-head" data-toggle-sec="${sec.id}">
          <div class="section-head-title">
            <span style="font-size: 18px;">${sec.icon}</span>
            <span>${sec.title}</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            ${badgeHtml}
            <svg class="chevron" style="width:16px;height:16px;" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5"></path></svg>
          </div>
        </div>
        
        <div class="section-content">
          <div class="items-list">
    `;
    
    sec.items.forEach((label, i) => {
      const k = sec.id + '_' + i;
      const st = aptState.states[k] || '';
      const cm = aptState.comments[k] || '';
      
      html += `
        <div class="item ${st}" data-item-key="${k}">
          <div class="label">${esc(label)}</div>
          <div class="segmented-choices">
            <button class="choice-btn ok-btn" data-choice="ok" data-key="${k}">Conforme (OK)</button>
            <button class="choice-btn na-btn" data-choice="na" data-key="${k}">N/A</button>
            <button class="choice-btn nok-btn" data-choice="nok" data-key="${k}">Non Conforme (NOK)</button>
          </div>
          <div class="cmt-wrapper">
            <input class="cmt" placeholder="📝 Ajouter un commentaire..." value="${esc(cm)}" data-cmt-key="${k}">
          </div>
        </div>
      `;
    });
    
    html += `
          </div>
          
          <div class="photos-box">
            <div class="photo-actions">
              <div class="photo-buttons">
                <button class="btn-photo-action primary" data-btn-camera="${sec.id}">
                  📸 Photo
                </button>
                <button class="btn-photo-action" data-btn-gallery="${sec.id}">
                  🖼️ Galerie
                </button>
              </div>
              <span class="pill" style="font-size: 11px;">${ph.length} photo(s)</span>
            </div>
            <div class="thumbs-list" id="thumbs-${sec.id}">${thumbsHtml}</div>
          </div>
        </div>
      </div>
    `;
  });
  
  container.innerHTML = html;
  
  // Attach Event Listeners
  // Accordion Toggle
  container.querySelectorAll('[data-toggle-sec]').forEach(header => {
    header.onclick = () => {
      const secId = header.getAttribute('data-toggle-sec');
      activeSections[secId] = !activeSections[secId];
      const card = document.getElementById(`section-card-${secId}`);
      if (activeSections[secId]) {
        card.classList.add('collapsed');
      } else {
        card.classList.remove('collapsed');
      }
    };
  });
  
  // Segmented Choices Click
  container.querySelectorAll('.choice-btn').forEach(btn => {
    btn.onclick = () => {
      const k = btn.getAttribute('data-key');
      const choice = btn.getAttribute('data-choice');
      const itemEl = container.querySelector(`[data-item-key="${k}"]`);
      
      if (aptState.states[k] === choice) {
        // Toggle off
        aptState.states[k] = '';
        itemEl.className = 'item';
      } else {
        aptState.states[k] = choice;
        itemEl.className = `item ${choice}`;
      }
      
      saveApt();
      updateSectionBadges(k.split('_')[0]);
    };
  });
  
  // Comments input change
  container.querySelectorAll('[data-cmt-key]').forEach(input => {
    input.oninput = () => {
      const k = input.getAttribute('data-cmt-key');
      aptState.comments[k] = input.value;
      saveApt();
    };
  });
  
  // Photo buttons click
  container.querySelectorAll('[data-btn-camera]').forEach(btn => {
    btn.onclick = () => {
      pendingSection = btn.getAttribute('data-btn-camera');
      document.getElementById('fileInput').click();
    };
  });
  container.querySelectorAll('[data-btn-gallery]').forEach(btn => {
    btn.onclick = () => {
      pendingSection = btn.getAttribute('data-btn-gallery');
      document.getElementById('galInput').click();
    };
  });
  
  // Thumbnail photo viewer click & Lazy Loading base64
  container.querySelectorAll('[data-photo-id]').forEach(wrapper => {
    const pid = wrapper.getAttribute('data-photo-id');
    const img = document.getElementById(`img-thumb-${pid}`);
    
    // Lazy load the base64 from IDB
    dbStore.get('photo_' + currentAptId + '_' + pid).then(data => {
      if (data && img) img.src = data;
    });
    
    wrapper.onclick = () => viewPhoto(wrapper.getAttribute('data-photo-id'));
  });
}

function updateSectionBadges(secId) {
  const sec = SECTIONS.find(s => s.id === secId);
  if (!sec) return;
  
  let secOk = 0, secNok = 0, secNa = 0;
  sec.items.forEach((_, i) => {
    const k = sec.id + '_' + i;
    const st = aptState.states[k];
    if (st === 'ok') secOk++;
    else if (st === 'nok') secNok++;
    else if (st === 'na') secNa++;
  });
  
  const answeredCount = secOk + secNok + secNa;
  const itemsTotal = sec.items.length;
  
  const headEl = document.querySelector(`[data-toggle-sec="${secId}"]`);
  if (headEl) {
    const badgeWrapper = headEl.querySelector('div:last-child');
    if (badgeWrapper) {
      let badgeHtml = `<span class="pill">${answeredCount}/${itemsTotal}</span>`;
      if (secNok > 0) {
        badgeHtml += ` <span class="pill nok">${secNok} NOK</span>`;
      }
      badgeHtml += ` <svg class="chevron" style="width:16px;height:16px;" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5"></path></svg>`;
      badgeWrapper.innerHTML = badgeHtml;
    }
  }
}

// ---- TAB 2: SYNTHÈSE RENDER ----
function renderSummaryTab() {
  const container = document.getElementById('tab-summary');
  const aptInfo = index.find(x => x.id === currentAptId);
  const stats = getStats(aptState);
  
  // Calculate Rentability
  let rentabilityHtml = '';
  if (aptInfo.price && aptInfo.surface) {
    const ratio = (aptInfo.price / aptInfo.surface).toFixed(2);
    rentabilityHtml = `<div style="font-size: 14px; text-align: center; color: var(--text-muted); margin-bottom: 12px;">Rapport prix/m² : <strong>${ratio} €/m²</strong></div>`;
  }
  
  // Generate Lists of Strengths and Weaknesses
  let strengthsList = [];
  let weaknessesList = [];
  
  SECTIONS.forEach(sec => {
    sec.items.forEach((label, i) => {
      const k = sec.id + '_' + i;
      const st = aptState.states[k];
      const cm = aptState.comments[k] || '';
      
      if (st === 'ok') {
        strengthsList.push({ label, comment: cm });
      } else if (st === 'nok') {
        weaknessesList.push({ label, comment: cm });
      }
    });
  });
  
  let strengthsHtml = '';
  if (strengthsList.length === 0) {
    strengthsHtml = '<li>Aucun point fort relevé.</li>';
  } else {
    strengthsList.forEach(item => {
      strengthsHtml += `
        <li>
          <strong>${esc(item.label)}</strong>
          ${item.comment ? `<span style="display:block; font-size:12px; color:var(--text-muted); font-style:italic;">"${esc(item.comment)}"</span>` : ''}
        </li>
      `;
    });
  }
  
  let weaknessesHtml = '';
  if (weaknessesList.length === 0) {
    weaknessesHtml = '<li>Aucun point faible relevé.</li>';
  } else {
    weaknessesList.forEach(item => {
      weaknessesHtml += `
        <li>
          <strong>${esc(item.label)}</strong>
          ${item.comment ? `<span style="display:block; font-size:12px; color:var(--text-muted); font-style:italic;">"${esc(item.comment)}"</span>` : ''}
        </li>
      `;
    });
  }
  
  let scoreColorClass = 'score-mid';
  if (stats.score >= 75) scoreColorClass = 'score-high';
  else if (stats.score < 50) scoreColorClass = 'score-low';
  
  // Format sharing text
  const shareText = generateShareText(aptInfo, stats, strengthsList, weaknessesList);
  
  container.innerHTML = `
    <!-- Score Circle -->
    <div class="score-circle-wrapper">
      <div class="score-circle">
        <span class="num">${stats.score}%</span>
        <span class="label">Match Score</span>
      </div>
    </div>
    
    ${rentabilityHtml}
    
    <!-- Checklist Stats Grid -->
    <div class="card-stats" style="margin-bottom: 20px;">
      <div class="stat-item">
        OK <span class="val" style="color:var(--ok);">${stats.ok}</span>
      </div>
      <div class="stat-item">
        NOK <span class="val" style="color:var(--nok);">${stats.nok}</span>
      </div>
      <div class="stat-item">
        Non Requis <span class="val">${stats.na}</span>
      </div>
    </div>
    
    <!-- Strengths / Weaknesses Grid -->
    <div class="strengths-weaknesses">
      <div class="sw-panel strengths">
        <h4>🟢 Points Forts (${strengthsList.length})</h4>
        <ul>${strengthsHtml}</ul>
      </div>
      
      <div class="sw-panel weaknesses">
        <h4>🔴 Points Faibles (${weaknessesList.length})</h4>
        <ul>${weaknessesHtml}</ul>
      </div>
    </div>
    
    <!-- Share & Copy Report Box -->
    <div class="share-box">
      <h3 style="font-size: 15px; margin-bottom: 12px; display: flex; align-items:center; gap: 8px;">
        📢 Partager ce compte-rendu
      </h3>
      <textarea class="share-textarea" readonly id="shareTextarea">${esc(shareText)}</textarea>
      <button class="btn" id="shareReportBtn">
        <svg style="width:18px;height:18px;" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186l5.358-2.679m-5.358 2.679l5.358 2.678A2.25 2.25 0 1013.5 19.5a2.25 2.25 0 00-1.842-2.213L6.3 14.61a2.25 2.25 0 000-1.22l5.358-2.68A2.25 2.25 0 1013.5 4.5a2.25 2.25 0 00-1.842 2.213l-5.358 2.679z"></path></svg>
        Partager via Whatsapp / Mail
      </button>
      <button class="btn secondary" id="copyReportBtn" style="margin-top: 8px;">
        📋 Copier le rapport
      </button>
    </div>
  `;
  
  // Share & Copy events
  document.getElementById('shareReportBtn').onclick = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `Rapport de visite : ${aptInfo.name}`,
          text: shareText
        });
        toast('Partage réussi');
      } catch (err) {
        if (err.name !== 'AbortError') {
          copyToClipboard(shareText);
        }
      }
    } else {
      copyToClipboard(shareText);
    }
  };
  
  document.getElementById('copyReportBtn').onclick = () => {
    copyToClipboard(shareText);
  };
}

function generateShareText(aptInfo, stats, strengths, weaknesses) {
  let text = `🏠 Visite d'appartement : ${aptInfo.name.toUpperCase()}\n`;
  if (aptInfo.address) text += `📍 Adresse : ${aptInfo.address}\n`;
  if (aptInfo.price) text += `💰 Loyer : ${aptInfo.price} €/mois CC\n`;
  if (aptInfo.surface) text += `📐 Surface : ${aptInfo.surface} m²\n`;
  if (aptInfo.price && aptInfo.surface) text += `📊 Ratio : ${(aptInfo.price / aptInfo.surface).toFixed(2)} €/m²\n`;
  if (aptInfo.contact) text += `📞 Contact : ${aptInfo.contact} (${aptInfo.phone || ''})\n`;
  
  text += `\n🎯 MATCH SCORE : ${stats.score}%\n`;
  text += `📈 Résultat : ${stats.ok} OK | ${stats.nok} NOK | ${stats.na} N/A\n`;
  
  text += `\n🟢 POINTS FORTS :\n`;
  if (strengths.length === 0) {
    text += `- Aucun point fort noté\n`;
  } else {
    strengths.slice(0, 10).forEach(item => {
      text += `- ${item.label}${item.comment ? ` (${item.comment})` : ''}\n`;
    });
    if (strengths.length > 10) text += `- Et ${strengths.length - 10} autres points forts...\n`;
  }
  
  text += `\n🔴 POINTS FAIBLES :\n`;
  if (weaknesses.length === 0) {
    text += `- Aucun point faible noté\n`;
  } else {
    weaknesses.slice(0, 10).forEach(item => {
      text += `- ${item.label}${item.comment ? ` (${item.comment})` : ''}\n`;
    });
    if (weaknesses.length > 10) text += `- Et ${weaknesses.length - 10} autres points faibles...\n`;
  }
  
  text += `\nEnvoyé depuis AppartCheck 📱`;
  return text;
}

function copyToClipboard(text) {
  const textarea = document.createElement('textarea');
  textarea.value = text;
  document.body.appendChild(textarea);
  textarea.select();
  try {
    document.execCommand('copy');
    toast('Rapport copié dans le presse-papiers');
  } catch (err) {
    toast('Impossible de copier');
  }
  document.body.removeChild(textarea);
}

// ---- TAB 3: PHOTOS RENDER ----
function renderPhotosTab() {
  const container = document.getElementById('tab-photos');
  const photos = aptState.photos || [];
  
  if (photos.length === 0) {
    container.innerHTML = `
      <div class="empty" style="padding: 32px 0;">
        <svg fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"></path></svg>
        <span>Aucune photo prise pour le moment.</span>
        <button class="btn secondary" id="switchToChecklistBtn" style="width: auto;">Aller dans la Checklist</button>
      </div>
    `;
    document.getElementById('switchToChecklistBtn').onclick = () => switchTab('checklist');
    return;
  }
  
  let gridHtml = '<div style="display:grid; grid-template-columns:repeat(3, 1fr); gap: 8px;">';
  photos.forEach(photo => {
    const sec = SECTIONS.find(s => s.id === photo.section);
    const secName = sec ? sec.title.split(' - ')[1] : 'Inconnu';
    
    gridHtml += `
      <div class="thumb-wrapper" style="width:100%; height:0; padding-bottom:100%; position:relative;" data-photo-id="${photo.pid}">
        <img src="" alt="photo" id="grid-thumb-${photo.pid}" style="position:absolute; top:0; left:0; width:100%; height:100%; object-fit:cover;">
        <span style="position:absolute; bottom:2px; left:2px; font-size:9px; background:rgba(0,0,0,0.6); color:#fff; padding:2px 4px; border-radius:4px; max-width:90%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
          ${secName}
        </span>
      </div>
    `;
  });
  gridHtml += '</div>';
  
  container.innerHTML = gridHtml;
  
  // Lazy load images
  photos.forEach(photo => {
    dbStore.get('photo_' + currentAptId + '_' + photo.pid).then(data => {
      if (data) {
        const img = document.getElementById(`grid-thumb-${photo.pid}`);
        if (img) img.src = data;
      }
    });
    
    const wrapper = container.querySelector(`[data-photo-id="${photo.pid}"]`);
    if (wrapper) {
      wrapper.onclick = () => viewPhoto(photo.pid);
    }
  });
}

// ---- Image Compression Logic ----
function compressFile(file, section) {
  const reader = new FileReader();
  reader.onload = () => {
    const img = new Image();
    img.onload = async () => {
      const max = 1280;
      let w = img.width;
      let h = img.height;
      
      // Calculate aspect ratio
      if (w > h && w > max) {
        h = Math.round((h * max) / w);
        w = max;
      } else if (h >= w && h > max) {
        w = Math.round((w * max) / h);
        h = max;
      }
      
      const canvas = document.createElement('canvas');
      canvas.width = w;
      canvas.height = h;
      
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, w, h);
      
      const compressedDataUrl = canvas.toDataURL('image/jpeg', 0.65);
      await savePhoto(section, compressedDataUrl);
    };
    img.src = reader.result;
  };
  reader.readAsDataURL(file);
}

document.getElementById('fileInput').onchange = e => {
  const file = e.target.files[0];
  e.target.value = '';
  if (file) {
    toast('Traitement de la photo...');
    compressFile(file, pendingSection);
  }
};

document.getElementById('galInput').onchange = e => {
  const file = e.target.files[0];
  e.target.value = '';
  if (file) {
    toast('Traitement de la photo...');
    compressFile(file, pendingSection);
  }
};

async function savePhoto(section, dataUrl) {
  const pid = uid();
  await dbStore.set('photo_' + currentAptId + '_' + pid, dataUrl);
  
  aptState.photos = aptState.photos || [];
  aptState.photos.push({
    pid,
    section,
    ts: Date.now()
  });
  
  await saveApt();
  toast('Photo enregistrée !');
  
  // Refresh page tab content
  renderTabContent();
}

// ---- PHOTO FULLSCREEN VIEWER ----
let viewingPhotoId = null;

async function viewPhoto(pid) {
  viewingPhotoId = pid;
  const data = await dbStore.get('photo_' + currentAptId + '_' + pid);
  if (!data) return;
  
  document.getElementById('viewerImg').src = data;
  document.getElementById('viewer').style.display = 'flex';
}

document.getElementById('viewerClose').onclick = () => {
  document.getElementById('viewer').style.display = 'none';
  viewingPhotoId = null;
};

document.getElementById('viewerDel').onclick = async () => {
  if (!viewingPhotoId) return;
  if (!confirm('Voulez-vous vraiment supprimer cette photo ?')) return;
  
  await dbStore.del('photo_' + currentAptId + '_' + viewingPhotoId);
  
  aptState.photos = (aptState.photos || []).filter(p => p.pid !== viewingPhotoId);
  await saveApt();
  
  document.getElementById('viewer').style.display = 'none';
  viewingPhotoId = null;
  
  toast('Photo supprimée.');
  renderTabContent();
};

// ---- EXPORT / IMPORT DATA SYSTEM ----
async function exportAll() {
  await loadIndex();
  const data = {
    app: 'AppartCheck',
    version: 2,
    exportedAt: new Date().toISOString(),
    index,
    apts: {},
    photos: {}
  };
  
  for (const item of index) {
    const s = await dbStore.get('apt_' + item.id);
    const state = s ? JSON.parse(s) : getEmptyState();
    data.apts[item.id] = state;
    
    for (const p of (state.photos || [])) {
      const pData = await dbStore.get('photo_' + item.id + '_' + p.pid);
      if (pData) {
        data.photos[item.id + '_' + p.pid] = pData;
      }
    }
  }
  
  try {
    const blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `appartcheck_export_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(url), 2000);
    toast('Sauvegarde exportée !');
  } catch (e) {
    toast('Échec de l\'exportation');
  }
}

function importAll(file) {
  const reader = new FileReader();
  reader.onload = async () => {
    try {
      const data = JSON.parse(reader.result);
      if (!data || data.app !== 'AppartCheck' || !Array.isArray(data.index)) {
        throw new Error('Fichier AppartCheck invalide.');
      }
      
      await loadIndex();
      const existingIds = new Set(index.map(a => a.id));
      
      for (const a of data.index) {
        if (!existingIds.has(a.id)) {
          index.push(a);
          existingIds.add(a.id);
        }
      }
      await saveIndex();
      
      // Save apartment details
      for (const id in (data.apts || {})) {
        await dbStore.set('apt_' + id, JSON.stringify(data.apts[id]));
      }
      
      // Save photos
      for (const k in (data.photos || {})) {
        await dbStore.set('photo_' + k, data.photos[k]);
      }
      
      toast('Importation réussie !');
      renderHome();
    } catch (e) {
      toast('Fichier JSON d\'importation invalide ou corrompu.');
    }
  };
  reader.readAsText(file);
}

document.getElementById('importInput').onchange = e => {
  const file = e.target.files[0];
  e.target.value = '';
  if (file) {
    importAll(file);
  }
};

// ---- INITIALIZATION ----
(async () => {
  try {
    await dbStore.init();
    await initTheme();
    await loadIndex();
    renderHome();
  } catch (err) {
    console.error('Failed to bootstrap app:', err);
    alert('Erreur d\'initialisation du stockage. L\'application peut ne pas fonctionner.');
  }
})();

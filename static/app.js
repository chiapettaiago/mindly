// scripts leves para interatividade futura
console.log('Lembrete app carregado');

let synth = window.speechSynthesis;
let utterance = null;
let notificationInterval;
let currentNotifications = [];
// Conjunto para evitar repetir modal/toast para o mesmo lembrete de alta urgência
let notifiedHigh = new Set();
// Media query para acompanhar o tema do sistema
let themeMedia = null;
// Preferências em memória
let prefs = { themePreference: 'system', notifyHighToast: true, useSystemNotifications: true, fontScale:'medium', listDensity:'default', playSoundHigh:false };

// PWA install state
let deferredPrompt = null;
let isStandalone = false;

function checkStandalone() {
  return (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) || 
         window.navigator.standalone === true ||
         document.referrer.includes('android-app://');
}

function showInstallButtons() {
  const btn = document.getElementById('installPwaBtn');
  const chip = document.getElementById('installChip');
  if (btn) btn.style.display = 'inline-flex';
  if (chip) chip.style.display = 'inline-flex';
}

function hideInstallButtons() {
  const btn = document.getElementById('installPwaBtn');
  const chip = document.getElementById('installChip');
  if (btn) btn.style.display = 'none';
  if (chip) chip.style.display = 'none';
}

function applyInterfacePrefs(){
  const root = document.documentElement;
  root.setAttribute('data-font', prefs.fontScale || 'medium');
  root.setAttribute('data-density', prefs.listDensity || 'default');
}

// Preferências: helpers
function loadPreferences(){
  try{
    const raw = localStorage.getItem('userPreferences');
    if (raw){ prefs = Object.assign(prefs, JSON.parse(raw)); }
  }catch{}
}
function persistPreferences(){
  try{ localStorage.setItem('userPreferences', JSON.stringify(prefs)); }catch{}
}
function openPreferences(){
  loadPreferences();
  // Tema
  const theme = prefs.themePreference || 'system';
  ({ system:'themePrefSystem', light:'themePrefLight', dark:'themePrefDark' }[theme] && (document.getElementById({ system:'themePrefSystem', light:'themePrefLight', dark:'themePrefDark' }[theme]).checked = true));
  // Interface
  const fs = prefs.fontScale || 'medium';
  ({ small:'fontSmall', medium:'fontMedium', large:'fontLarge' }[fs] && (document.getElementById({ small:'fontSmall', medium:'fontMedium', large:'fontLarge' }[fs]).checked = true));
  const ld = prefs.listDensity || 'default';
  ({ compact:'densityCompact', default:'densityDefault', comfortable:'densityComfortable' }[ld] && (document.getElementById({ compact:'densityCompact', default:'densityDefault', comfortable:'densityComfortable' }[ld]).checked = true));
  // Notificações
  const chkToast = document.getElementById('notifyHighToast');
  const chkSystem = document.getElementById('useSystemNotifications');
  const chkSound = document.getElementById('playSoundHigh');
  if (chkToast) chkToast.checked = !!prefs.notifyHighToast;
  if (chkSystem) chkSystem.checked = !!prefs.useSystemNotifications;
  if (chkSound) chkSound.checked = !!prefs.playSoundHigh;
  showModal('preferencesModal');
}
function savePreferences(){
  const selectedTheme = document.querySelector('input[name="themePref"]:checked');
  prefs.themePreference = selectedTheme ? selectedTheme.value : 'system';
  const selectedFont = document.querySelector('input[name="fontScale"]:checked');
  prefs.fontScale = selectedFont ? selectedFont.value : 'medium';
  const selectedDensity = document.querySelector('input[name="listDensity"]:checked');
  prefs.listDensity = selectedDensity ? selectedDensity.value : 'default';
  const chkToast = document.getElementById('notifyHighToast');
  const chkSystem = document.getElementById('useSystemNotifications');
  const chkSound = document.getElementById('playSoundHigh');
  prefs.notifyHighToast = !!(chkToast && chkToast.checked);
  prefs.useSystemNotifications = !!(chkSystem && chkSystem.checked);
  prefs.playSoundHigh = !!(chkSound && chkSound.checked);
  persistPreferences();
  setThemePreference(prefs.themePreference);
  applyInterfacePrefs();
  closeModal('preferencesModal');
  if (typeof showToast==='function') showToast('Preferências salvas.', 'info', { timeout: 2000 });
}

// THEME: helpers
function getSystemTheme(){
  return (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
}
function updateThemeToggleIcons(theme){
  // Sidebar button removido; apenas atualiza ícone do item de perfil no mobile se existir
  const mobileBtn = document.getElementById('profileMobile');
  if (mobileBtn){
    const el = mobileBtn.querySelector('.bottom-nav-icon') || mobileBtn;
    el.textContent = '👤';
  }
}
function applyTheme(theme) {
  const root = document.documentElement;
  root.setAttribute('data-theme', theme);
  updateThemeToggleIcons(theme);
}
function setThemePreference(pref){
  try { localStorage.setItem('themePreference', pref); } catch {}
  // também sincroniza com prefs
  prefs.themePreference = pref;
  persistPreferences();
  const theme = pref === 'system' ? getSystemTheme() : pref;
  applyTheme(theme);
}
function toggleTheme(){
  // Alterna entre claro/escuro e fixa a preferência do usuário
  let pref = prefs.themePreference || 'system';
  const currentApplied = document.documentElement.getAttribute('data-theme') || getSystemTheme();
  let nextPref;
  if (pref === 'system') {
    nextPref = currentApplied === 'light' ? 'dark' : 'light';
  } else {
    nextPref = pref === 'light' ? 'dark' : 'light';
  }
  setThemePreference(nextPref);
  if (typeof showToast === 'function') {
    showToast(`Tema fixado em ${nextPref === 'dark' ? 'escuro' : 'claro'}.`, 'info', { timeout: 2500 });
  }
}
function initTheme() {
  // carrega prefs unificadas
  loadPreferences();
  let pref = prefs.themePreference || 'system';
  // Listener para mudanças do sistema quando seguindo o sistema
  if (window.matchMedia) {
    themeMedia = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => {
      const p = (prefs && prefs.themePreference) || 'system';
      if (p === 'system') applyTheme(getSystemTheme());
    };
    if (typeof themeMedia.addEventListener === 'function') themeMedia.addEventListener('change', handler);
    else if (typeof themeMedia.addListener === 'function') themeMedia.addListener(handler);
  }
  const theme = (prefs.themePreference||'system') === 'system' ? getSystemTheme() : prefs.themePreference;
  applyTheme(theme);
  applyInterfacePrefs();
}

// TTS Functions
function stopSpeaking(){ try{ if (synth && synth.speaking) synth.cancel(); } catch {} }
function buildTextFromReminder(node) {
  const title = node.dataset.title || '';
  const note = node.dataset.note || '';
  const due = node.dataset.due || '';
  let parts = [];
  if (title) parts.push('Lembrete: ' + title + '.');
  if (note) parts.push('Observação: ' + note + '.');
  if (due) parts.push('Prazo: ' + due + '.');
  return parts.join(' ');
}

function speakText(text) {
  if (!synth) {
    alert('Leitor de voz não suportado neste navegador.');
    return;
  }
  stopSpeaking();
  utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'pt-BR';
  synth.speak(utterance);
}

function speakElement(el) {
  const text = buildTextFromReminder(el);
  speakText(text);
}

// Modal Functions
function showModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
  }
}

// System Info
function openSystemInfo(){
  try{
    const v = document.documentElement.getAttribute('data-app-version') || 'dev';
    const m = document.documentElement.getAttribute('data-app-manufacturer') || 'Mindly';
    const ua = navigator.userAgent;
    const plat = navigator.platform || '';
    const lang = navigator.language || '';
    const content = `
      <div class="info-grid" style="display:grid;grid-template-columns:140px 1fr;gap:8px;align-items:center;text-align:left">
  <div class="muted">Desenvolvido por</div><div><strong>Iago Filgueiras Chiapetta</strong></div>
        <div class="muted">Fabricante</div><div><strong>${m}</strong></div>
        <div class="muted">Versão</div><div><strong>${v}</strong></div>
        <div class="muted">Plataforma</div><div>${plat}</div>
        <div class="muted">Idioma</div><div>${lang}</div>
        <div class="muted">User Agent</div><div style="word-break:break-all">${ua}</div>
      </div>`;
    const container = document.getElementById('systemInfoContent');
    if (container){ container.innerHTML = content; }
  }catch{}
  showModal('systemInfoModal');
}

let reminderToDelete = null;

function confirmDelete(reminderId) {
  reminderToDelete = reminderId;
  showModal('deleteModal');
}

function executeDelete() {
  if (reminderToDelete) {
    // Cria form oculto para enviar DELETE
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/delete/${reminderToDelete}`;
    form.style.display = 'none';
    
    // Adicionar token CSRF
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
                     document.querySelector('input[name="csrf_token"]')?.value ||
                     (typeof csrf_token !== 'undefined' ? csrf_token : '');
    
    if (csrfToken) {
      const csrfInput = document.createElement('input');
      csrfInput.type = 'hidden';
      csrfInput.name = 'csrf_token';
      csrfInput.value = csrfToken;
      form.appendChild(csrfInput);
    }
    
    document.body.appendChild(form);
    form.submit();
  }
}

// Notification Functions
async function checkNotifications() {
  try {
    const response = await fetch('/api/notifications');
    const notifications = await response.json();
    
    currentNotifications = notifications;
    updateNotificationBadge(notifications);
    
    // Mostra notificação automática para alta urgência ou vencidos (minutes_left === 0)
    notifications.forEach(notif => {
      if (notif.urgency === 'high' && notif.minutes_left <= 30) {
        if (!notifiedHigh.has(notif.id)) {
          // modal de alerta
          showNotificationModal(notif);
          // toast translúcido (respeitando preferência)
          if (prefs.notifyHighToast) {
            const minutes = notif.minutes_left;
            const timeText = minutes === 0
              ? 'Venceu agora'
              : (minutes < 60 ? `${minutes} minutos` : `${Math.floor(minutes/60)}h ${minutes%60}min`);
            const type = minutes === 0 ? 'danger' : 'info';
            showToast(`⏰ ${notif.title} — ${minutes === 0 ? 'venceu agora!' : 'vence em ' + timeText}`, type, { timeout: 6000 });
          }
          notifiedHigh.add(notif.id);
        }
      }
    });
  } catch (error) {
    console.error('Erro ao buscar notificações:', error);
  }
}

function updateNotificationBadge(notifications) {
  const badge = document.getElementById('notificationBadge');
  const count = document.getElementById('notificationCount');
  
  if (notifications.length > 0) {
    badge.style.display = 'block';
    count.textContent = notifications.length;
  } else {
    badge.style.display = 'none';
  }
}

function showNotifications() {
  if (currentNotifications.length === 0) {
    alert('Nenhuma notificação pendente');
    return;
  }
  
  let content = '<div style="text-align:left">';
  currentNotifications.forEach(notif => {
    const urgencyClass = `urgency-${notif.urgency}`;
    const timeText = notif.minutes_left < 60 ? 
      `${notif.minutes_left} minutos` : 
      `${Math.floor(notif.minutes_left/60)}h ${notif.minutes_left%60}min`;
    
    content += `
      <div class="notification-item ${urgencyClass}" style="padding:12px;margin:8px 0;border-left:4px solid;border-radius:8px;background:rgba(255,255,255,0.1)">
        <strong>${notif.title}</strong><br>
        <small>⏰ ${notif.minutes_left === 0 ? 'Venceu agora' : 'Vence em ' + timeText}</small>
      </div>
    `;
  });
  content += '</div>';
  
  document.getElementById('notificationContent').innerHTML = content;
  showModal('notificationModal');
}

function showNotificationModal(notification) {
  const timeText = notification.minutes_left === 0 ? 
    'Venceu agora' : 
    (notification.minutes_left < 60 ? `${notification.minutes_left} minutos` : `${Math.floor(notification.minutes_left/60)}h ${notification.minutes_left%60}min`);
  
  const content = `
    <div style="text-align:center">
      <h4>⏰ ${notification.title}</h4>
      <p>Este lembrete ${notification.minutes_left === 0 ? 'venceu agora!' : 'vence em ' + timeText + '!'} </p>
    </div>
  `;
  
  document.getElementById('notificationContent').innerHTML = content;
  showModal('notificationModal');
  
  // Som/Toast do navegador (quando permitido)
  if (prefs.useSystemNotifications && 'Notification' in window) {
    try {
      if (Notification.permission === 'granted') {
        new Notification(`Lembrete: ${notification.title}`, { body: timeText, icon: '/static/favicon.ico' });
      }
    } catch (e) { console.warn('Notificação do sistema não disponível:', e); }
  }
}

// Toasts (Windows-like inside app)
function showToast(message, type = 'info', options = {}) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `flash ${type}`;
  toast.setAttribute('role', 'status');
  toast.setAttribute('aria-live', 'polite');

  const content = document.createElement('div');
  content.className = 'toast-content';
  content.textContent = message;

  const close = document.createElement('button');
  close.className = 'toast-close';
  close.setAttribute('aria-label', 'Fechar');
  close.innerText = '✕';
  close.onclick = () => { toast.classList.add('hiding'); setTimeout(() => toast.remove(), 200); };

  toast.appendChild(content);
  toast.appendChild(close);
  container.appendChild(toast);

  const timeout = options.timeout ?? 4000;
  if (timeout > 0) {
    setTimeout(() => {
      if (toast.isConnected) {
        toast.classList.add('hiding');
        setTimeout(() => toast.remove(), 200);
      }
    }, timeout);
  }
}

// Sidebar Preferences
function saveSidebarPref(collapsed){
  try{ localStorage.setItem('sidebarCollapsed', String(!!collapsed)); }catch{}
}
function loadSidebarPref(){
  try{ const v = localStorage.getItem('sidebarCollapsed'); return v === null ? null : v === 'true'; }catch{ return null }
}

// Event Listeners
window.addEventListener('DOMContentLoaded', () => {
  const confirmDeleteBtn = document.getElementById('confirmDelete');
  
  if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', executeDelete);
  // Toggle de senha (delegação)
  document.body.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-toggle="password"]');
    if (!btn) return;
    const form = btn.closest('form');
    if (!form) return;
    // tenta encontrar o input de senha pelo tipo
    let input = form.querySelector('input[type="password"], input[name="password"]');
    if (!input) return;
    const isHidden = input.type === 'password';
    try {
      input.type = isHidden ? 'text' : 'password';
      btn.setAttribute('aria-pressed', String(isHidden));
      btn.title = isHidden ? 'Ocultar senha' : 'Mostrar senha';
      btn.textContent = isHidden ? '🙈' : '👁️';
    } catch {}
  });
  
  // Pedir permissão para notificações uma única vez
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission().catch(() => {});
  }
  
  // Inicializa tema
  initTheme();

  // Sidebar: restaurar preferência (padrão: colapsada em telas grandes)
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.getElementById('mainContent');
  if (sidebar && mainContent) {
    const pref = loadSidebarPref();
    const shouldCollapse = (pref === null) ? (window.innerWidth > 768) : pref;
    if (window.innerWidth > 768 && shouldCollapse) {
      sidebar.classList.add('collapsed');
      mainContent.classList.add('sidebar-collapsed');
    } else {
      sidebar.classList.remove('collapsed');
      mainContent.classList.remove('sidebar-collapsed');
    }
  }
  
  // Verificar notificações com maior frequência (a cada 30s)
  checkNotifications();
  clearInterval(notificationInterval);
  notificationInterval = setInterval(checkNotifications, 30000);
  
  // Fechar modais ao clicar fora
  document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
      closeModal(e.target.id);
    }
  });

  // Auto-hide para flashes renderizados pelo backend (estilo toast)
  const toasts = document.querySelectorAll('#toastContainer .flash');
  toasts.forEach((t, i) => {
    const timeout = 4000 + i * 300;
    setTimeout(() => {
      if (t.isConnected) {
        t.classList.add('hiding');
        setTimeout(() => t.remove(), 200);
      }
    }, timeout);
  });
  
  // PWA: registrar SW
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }
  
  // Verificar se já está em standalone
  isStandalone = checkStandalone();
  
  // Capturar prompt de instalação (Android/Chrome)
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    if (!isStandalone) {
      showInstallButtons();
    }
  });
  
  // iOS: mostrar botões se não estiver instalado
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  if (isIOS && !isStandalone) {
    showInstallButtons();
  }
  
  // Para teste: sempre mostrar botões (remover depois)
  if (!isStandalone) {
    showInstallButtons();
  }
  
  // Ocultar botões após instalação
  window.addEventListener('appinstalled', () => {
    hideInstallButtons();
    isStandalone = true;
    if (typeof showToast==='function') showToast('App instalado com sucesso.', 'success');
  });
  
  try{
    const endpoint = document.body.getAttribute('data-endpoint');
    if (sessionStorage.getItem('openCreateReminder') === '1' && endpoint === 'index'){
      sessionStorage.removeItem('openCreateReminder');
      showModal('createReminderModal');
    }
    if (sessionStorage.getItem('openCreateNote') === '1' && endpoint === 'notes'){
      sessionStorage.removeItem('openCreateNote');
      const isMobile = window.innerWidth <= 768;
      if (isMobile) {
        showModal('createNoteModal');
      } else {
        const input = document.getElementById('noteInput');
        if (input){ input.scrollIntoView({behavior:'smooth', block:'center'}); input.focus(); }
      }
    }
    // Fallback para compatibilidade (antigo focusNewNote)
    if (sessionStorage.getItem('focusNewNote') === '1' && endpoint === 'notes'){
      sessionStorage.removeItem('focusNewNote');
      const input = document.getElementById('noteInput');
      if (input){ input.scrollIntoView({behavior:'smooth', block:'center'}); input.focus(); }
    }
  }catch{}
});

// Sidebar Functions
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.getElementById('mainContent');
  
  sidebar.classList.toggle('collapsed');
  if (sidebar.classList.contains('collapsed')) {
    mainContent.classList.add('sidebar-collapsed');
    saveSidebarPref(true);
  } else {
    mainContent.classList.remove('sidebar-collapsed');
    saveSidebarPref(false);
  }
}

// Auto-collapse sidebar on mobile
function handleResize() {
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.getElementById('mainContent');
  
  if (window.innerWidth <= 768) {
    sidebar.classList.remove('collapsed');
    mainContent.classList.remove('sidebar-collapsed');
  }
}

window.addEventListener('resize', handleResize);
handleResize(); // Call on load

// Som de alta urgência (opcional)
function playHighSound(){
  if (!prefs.playSoundHigh) return;
  try{
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = 'sine'; o.frequency.setValueAtTime(880, ctx.currentTime);
    g.gain.setValueAtTime(0.001, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.2, ctx.currentTime + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.6);
    o.connect(g); g.connect(ctx.destination); o.start(); o.stop(ctx.currentTime + 0.65);
  }catch{}
}

// Integrar som nas notificações de alta urgência
async function checkNotifications(){
  try{
    const response = await fetch('/api/notifications');
    const notifications = await response.json();
    currentNotifications = notifications;
    updateNotificationBadge(notifications);
    notifications.forEach(notif => {
      if (notif.urgency === 'high' && notif.minutes_left <= 30) {
        if (!notifiedHigh.has(notif.id)) {
          showNotificationModal(notif);
          if (prefs.notifyHighToast) {
            const minutes = notif.minutes_left;
            const timeText = minutes === 0 ? 'Venceu agora' : (minutes < 60 ? `${minutes} minutos` : `${Math.floor(minutes/60)}h ${minutes%60}min`);
            const type = minutes === 0 ? 'danger' : 'info';
            showToast(`⏰ ${notif.title} — ${minutes === 0 ? 'venceu agora!' : 'vence em ' + timeText}`, type, { timeout: 6000 });
          }
          playHighSound();
          notifiedHigh.add(notif.id);
        }
      }
    });
  }catch(e){ console.error('Erro ao buscar notificações:', e); }
}

function isMobile(){ return window.innerWidth <= 768; }

function goToCreate(kind){
  closeModal('newItemModal'); // fecha o seletor primeiro
  
  // Se já estiver na página adequada, abre o modal correspondente
  const endpoint = document.body.getAttribute('data-endpoint');
  if (kind === 'reminder'){
    if (endpoint === 'index'){
      showModal('createReminderModal');
      return;
    } else {
      // navegar para home e, após carregar, abrir modal
      sessionStorage.setItem('openCreateReminder', '1');
      window.location.href = '/';
    }
  }
  if (kind === 'note'){
    if (endpoint === 'notes'){
      // em mobile, usa modal; em desktop, foca no campo
      const isMobile = window.innerWidth <= 768;
      if (isMobile) {
        showModal('createNoteModal');
      } else {
        const input = document.getElementById('noteInput');
        if (input){ input.scrollIntoView({behavior:'smooth', block:'center'}); input.focus(); }
      }
      return;
    } else {
      // navegar para notas e sinalizar abertura do modal
      sessionStorage.setItem('openCreateNote', '1');
      window.location.href = '/notes';
    }
  }
}

// PWA: fluxo de instalação
async function installPwa(){
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  
  if (isIOS) {
    const content = `
      <div style="text-align:left">
        <p>Para instalar no iOS (Safari):</p>
        <ol style="padding-left:18px">
          <li>Toque em Compartilhar (ícone de quadrado com seta para cima).</li>
          <li>Selecione <strong>Adicionar à Tela de Início</strong>.</li>
          <li>Confirme e toque em <strong>Adicionar</strong>.</li>
        </ol>
      </div>`;
    const container = document.getElementById('systemInfoContent');
    if (container) container.innerHTML = content;
    showModal('systemInfoModal');
    return;
  }
  
  // Para Android/Chrome: se não há deferredPrompt, mostrar instruções alternativas
  if (!deferredPrompt) {
    const content = `
      <div style="text-align:left">
        <p><strong>Para instalar como app:</strong></p>
        <ol style="padding-left:18px">
          <li>Acesse este site via <strong>HTTPS</strong> (necessário para PWA).</li>
          <li>No Chrome: toque nos 3 pontos → "Instalar app" ou "Adicionar à tela inicial".</li>
          <li>No Firefox: toque no ícone de casa com + na barra de endereço.</li>
        </ol>
        <p class="muted">Nota: Em localhost HTTP, a instalação automática não está disponível.</p>
      </div>`;
    const container = document.getElementById('systemInfoContent');
    if (container) container.innerHTML = content;
    showModal('systemInfoModal');
    return;
  }
  
  // Se temos o prompt nativo, usar
  deferredPrompt.prompt();
  const choice = await deferredPrompt.userChoice.catch(()=>({ outcome:'dismissed' }));
  if (choice && choice.outcome === 'accepted') {
    if (typeof showToast==='function') showToast('Instalação iniciada.', 'success');
  } else {
    if (typeof showToast==='function') showToast('Instalação cancelada.', 'info');
  }
  deferredPrompt = null;
}

// Após carregar, se deve abrir/criar
window.addEventListener('DOMContentLoaded', () => {
  const confirmDeleteBtn = document.getElementById('confirmDelete');
  
  if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', executeDelete);
  // Toggle de senha (delegação)
  document.body.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-toggle="password"]');
    if (!btn) return;
    const form = btn.closest('form');
    if (!form) return;
    // tenta encontrar o input de senha pelo tipo
    let input = form.querySelector('input[type="password"], input[name="password"]');
    if (!input) return;
    const isHidden = input.type === 'password';
    try {
      input.type = isHidden ? 'text' : 'password';
      btn.setAttribute('aria-pressed', String(isHidden));
      btn.title = isHidden ? 'Ocultar senha' : 'Mostrar senha';
      btn.textContent = isHidden ? '🙈' : '👁️';
    } catch {}
  });
  
  // Pedir permissão para notificações uma única vez
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission().catch(() => {});
  }
  
  // Inicializa tema
  initTheme();

  // Sidebar: restaurar preferência (padrão: colapsada em telas grandes)
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.getElementById('mainContent');
  if (sidebar && mainContent) {
    const pref = loadSidebarPref();
    const shouldCollapse = (pref === null) ? (window.innerWidth > 768) : pref;
    if (window.innerWidth > 768 && shouldCollapse) {
      sidebar.classList.add('collapsed');
      mainContent.classList.add('sidebar-collapsed');
    } else {
      sidebar.classList.remove('collapsed');
      mainContent.classList.remove('sidebar-collapsed');
    }
  }
  
  // Verificar notificações com maior frequência (a cada 30s)
  checkNotifications();
  clearInterval(notificationInterval);
  notificationInterval = setInterval(checkNotifications, 30000);
  
  // Fechar modais ao clicar fora
  document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
      closeModal(e.target.id);
    }
  });

  // Auto-hide para flashes renderizados pelo backend (estilo toast)
  const toasts = document.querySelectorAll('#toastContainer .flash');
  toasts.forEach((t, i) => {
    const timeout = 4000 + i * 300;
    setTimeout(() => {
      if (t.isConnected) {
        t.classList.add('hiding');
        setTimeout(() => t.remove(), 200);
      }
    }, timeout);
  });
  
  try{
    const endpoint = document.body.getAttribute('data-endpoint');
    if (sessionStorage.getItem('openCreateReminder') === '1' && endpoint === 'index'){
      sessionStorage.removeItem('openCreateReminder');
      showModal('createReminderModal');
    }
    if (sessionStorage.getItem('openCreateNote') === '1' && endpoint === 'notes'){
      sessionStorage.removeItem('openCreateNote');
      const isMobile = window.innerWidth <= 768;
      if (isMobile) {
        showModal('createNoteModal');
      } else {
        const input = document.getElementById('noteInput');
        if (input){ input.scrollIntoView({behavior:'smooth', block:'center'}); input.focus(); }
      }
    }
    // Fallback para compatibilidade (antigo focusNewNote)
    if (sessionStorage.getItem('focusNewNote') === '1' && endpoint === 'notes'){
      sessionStorage.removeItem('focusNewNote');
      const input = document.getElementById('noteInput');
      if (input){ input.scrollIntoView({behavior:'smooth', block:'center'}); input.focus(); }
    }
  }catch{}
});

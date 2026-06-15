console.log('Mindly carregado');

let synth = window.speechSynthesis;
let notificationInterval = null;
let currentNotifications = [];
let notifiedHigh = new Set();
let reminderDeleteUrl = null;
let deferredPrompt = null;

const defaultPreferences = {
  themePreference: 'system',
  notifyHighToast: true,
  useSystemNotifications: true,
  fontScale: 'medium',
  listDensity: 'default',
  playSoundHigh: false,
};

let prefs = { ...defaultPreferences };

function loadPreferences() {
  try {
    const raw = localStorage.getItem('userPreferences');
    if (raw) {
      prefs = { ...defaultPreferences, ...JSON.parse(raw) };
    }
  } catch (_error) {
    prefs = { ...defaultPreferences };
  }
}

function persistPreferences() {
  try {
    localStorage.setItem('userPreferences', JSON.stringify(prefs));
  } catch (_error) {}
}

function getSystemTheme() {
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
}

function setThemePreference(preference) {
  prefs.themePreference = preference;
  persistPreferences();
  applyTheme(preference === 'system' ? getSystemTheme() : preference);
}

function applyInterfacePrefs() {
  document.documentElement.setAttribute('data-font', prefs.fontScale || 'medium');
  document.documentElement.setAttribute('data-density', prefs.listDensity || 'default');
}

function initTheme() {
  loadPreferences();
  applyTheme((prefs.themePreference || 'system') === 'system' ? getSystemTheme() : prefs.themePreference);
  applyInterfacePrefs();

  if (window.matchMedia) {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = () => {
      if ((prefs.themePreference || 'system') === 'system') {
        applyTheme(getSystemTheme());
      }
    };

    if (typeof media.addEventListener === 'function') {
      media.addEventListener('change', handleChange);
    } else if (typeof media.addListener === 'function') {
      media.addListener(handleChange);
    }
  }
}

function showModal(modalId) {
  const modal = document.getElementById(modalId);
  if (!modal) return;
  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (!modal) return;
  modal.style.display = 'none';
  document.body.style.overflow = '';
}

function openPreferences() {
  loadPreferences();

  const themeId = {
    system: 'themePrefSystem',
    light: 'themePrefLight',
    dark: 'themePrefDark',
  }[prefs.themePreference || 'system'];
  const fontId = {
    small: 'fontSmall',
    medium: 'fontMedium',
    large: 'fontLarge',
  }[prefs.fontScale || 'medium'];
  const densityId = {
    compact: 'densityCompact',
    default: 'densityDefault',
    comfortable: 'densityComfortable',
  }[prefs.listDensity || 'default'];

  if (themeId && document.getElementById(themeId)) document.getElementById(themeId).checked = true;
  if (fontId && document.getElementById(fontId)) document.getElementById(fontId).checked = true;
  if (densityId && document.getElementById(densityId)) document.getElementById(densityId).checked = true;

  const toastToggle = document.getElementById('notifyHighToast');
  const systemToggle = document.getElementById('useSystemNotifications');
  const soundToggle = document.getElementById('playSoundHigh');
  if (toastToggle) toastToggle.checked = !!prefs.notifyHighToast;
  if (systemToggle) systemToggle.checked = !!prefs.useSystemNotifications;
  if (soundToggle) soundToggle.checked = !!prefs.playSoundHigh;

  showModal('preferencesModal');
}

function savePreferences() {
  const theme = document.querySelector('input[name="themePref"]:checked');
  const fontScale = document.querySelector('input[name="fontScale"]:checked');
  const density = document.querySelector('input[name="listDensity"]:checked');

  prefs.themePreference = theme ? theme.value : 'system';
  prefs.fontScale = fontScale ? fontScale.value : 'medium';
  prefs.listDensity = density ? density.value : 'default';
  prefs.notifyHighToast = !!document.getElementById('notifyHighToast')?.checked;
  prefs.useSystemNotifications = !!document.getElementById('useSystemNotifications')?.checked;
  prefs.playSoundHigh = !!document.getElementById('playSoundHigh')?.checked;

  persistPreferences();
  setThemePreference(prefs.themePreference);
  applyInterfacePrefs();
  closeModal('preferencesModal');
  showToast('Preferências salvas.', 'info', { timeout: 2200 });
}

function openSystemInfo() {
  const container = document.getElementById('systemInfoContent');
  if (!container) return;

  const version = document.documentElement.getAttribute('data-app-version') || 'dev';
  const manufacturer = document.documentElement.getAttribute('data-app-manufacturer') || 'Mindly';

  container.innerHTML = `
    <div class="info-grid" style="display:grid;grid-template-columns:140px 1fr;gap:8px;align-items:start;text-align:left">
      <div class="muted">Fabricante</div><div><strong>${manufacturer}</strong></div>
      <div class="muted">Versão</div><div><strong>${version}</strong></div>
      <div class="muted">Plataforma</div><div>${navigator.platform || 'N/A'}</div>
      <div class="muted">Idioma</div><div>${navigator.language || 'N/A'}</div>
      <div class="muted">Navegador</div><div style="word-break:break-word">${navigator.userAgent}</div>
    </div>
  `;

  showModal('systemInfoModal');
}

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

  const closeButton = document.createElement('button');
  closeButton.className = 'toast-close';
  closeButton.setAttribute('aria-label', 'Fechar');
  closeButton.textContent = '✕';
  closeButton.onclick = () => hideToast(toast);

  toast.appendChild(content);
  toast.appendChild(closeButton);
  container.appendChild(toast);

  const timeout = options.timeout ?? 4200;
  if (timeout > 0) {
    setTimeout(() => hideToast(toast), timeout);
  }
}

function hideToast(toast) {
  if (!toast || !toast.isConnected) return;
  toast.classList.add('hiding');
  setTimeout(() => toast.remove(), 200);
}

function stopSpeaking() {
  try {
    if (synth && synth.speaking) synth.cancel();
  } catch (_error) {}
}

function buildTextFromReminder(node) {
  if (!node) return '';
  return node.dataset.reminderText || '';
}

function speakText(text) {
  if (!synth || !text) return;
  stopSpeaking();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'pt-BR';
  synth.speak(utterance);
}

function speakElement(element) {
  speakText(buildTextFromReminder(element));
}

function confirmDelete(deleteUrl) {
  reminderDeleteUrl = deleteUrl;
  showModal('deleteModal');
}

function executeDelete() {
  if (!reminderDeleteUrl) return;

  const form = document.createElement('form');
  form.method = 'POST';
  form.action = reminderDeleteUrl;
  form.style.display = 'none';

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
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

function openEditReminder(card) {
  if (!card) return;
  const form = document.getElementById('editReminderForm');
  const input = document.getElementById('editReminderInput');
  if (!form || !input) return;

  form.action = card.dataset.editUrl || '';
  input.value = card.dataset.reminderText || '';
  showModal('editReminderModal');
  setTimeout(() => input.focus(), 50);
}

function updateNotificationBadge(payload) {
  void payload;
}

function showNotificationModal(notification) {
  const content = document.getElementById('notificationContent');
  if (!content) return;

  const timeText = notification.minutes_left === 0
    ? 'vence agora'
    : notification.minutes_left < 60
      ? `vence em ${notification.minutes_left} minutos`
      : `vence em ${Math.floor(notification.minutes_left / 60)}h ${notification.minutes_left % 60}min`;

  content.innerHTML = `
    <div style="text-align:center">
      <h4>${notification.title}</h4>
      <p>${timeText}.</p>
    </div>
  `;

  showModal('notificationModal');

  if (prefs.useSystemNotifications && 'Notification' in window && Notification.permission === 'granted') {
    try {
      new Notification(notification.title, { body: timeText });
    } catch (_error) {}
  }
}

function showNotifications() {
  if (!currentNotifications.length) {
    showToast('Nenhum lembrete próximo no momento.', 'info', { timeout: 2500 });
    return;
  }

  const content = document.getElementById('notificationContent');
  if (!content) return;

  content.innerHTML = `
    <div style="text-align:left">
      ${currentNotifications.map((notification) => {
        const remaining = notification.minutes_left < 60
          ? `${notification.minutes_left} minutos`
          : `${Math.floor(notification.minutes_left / 60)}h ${notification.minutes_left % 60}min`;
        return `
          <div class="notification-item urgency-${notification.urgency}" style="padding:12px;margin:8px 0;border-left:4px solid;border-radius:10px;background:rgba(255,255,255,0.08)">
            <strong>${notification.title}</strong><br>
            <small>${notification.minutes_left === 0 ? 'Vence agora' : 'Vence em ' + remaining}</small>
          </div>
        `;
      }).join('')}
    </div>
  `;

  showModal('notificationModal');
}

function playHighSound() {
  if (!prefs.playSoundHigh) return;
  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gain = audioContext.createGain();
    oscillator.type = 'sine';
    oscillator.frequency.setValueAtTime(880, audioContext.currentTime);
    gain.gain.setValueAtTime(0.001, audioContext.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.2, audioContext.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, audioContext.currentTime + 0.6);
    oscillator.connect(gain);
    gain.connect(audioContext.destination);
    oscillator.start();
    oscillator.stop(audioContext.currentTime + 0.65);
  } catch (_error) {}
}

async function checkNotifications() {
  try {
    const response = await fetch('/api/notifications');
    const payload = await response.json();
    currentNotifications = payload.notifications || [];
    updateNotificationBadge(payload);

    currentNotifications.forEach((notification) => {
      if (notification.urgency === 'high' && !notifiedHigh.has(notification.id)) {
        showNotificationModal(notification);
        if (prefs.notifyHighToast) {
          const label = notification.minutes_left === 0
            ? 'vence agora'
            : notification.minutes_left < 60
              ? `vence em ${notification.minutes_left} minutos`
              : `vence em ${Math.floor(notification.minutes_left / 60)}h ${notification.minutes_left % 60}min`;
          showToast(`${notification.title} ${label}.`, notification.minutes_left === 0 ? 'danger' : 'info', { timeout: 6000 });
        }
        playHighSound();
        notifiedHigh.add(notification.id);
      }
    });
  } catch (error) {
    console.error('Erro ao buscar notificações:', error);
  }
}

function saveSidebarPref(collapsed) {
  try {
    localStorage.setItem('sidebarCollapsed', String(!!collapsed));
  } catch (_error) {}
}

function loadSidebarPref() {
  try {
    const raw = localStorage.getItem('sidebarCollapsed');
    return raw === null ? null : raw === 'true';
  } catch (_error) {
    return null;
  }
}

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.getElementById('mainContent');
  if (!sidebar || !mainContent) return;

  sidebar.classList.toggle('collapsed');
  mainContent.classList.toggle('sidebar-collapsed');
  saveSidebarPref(sidebar.classList.contains('collapsed'));
}

function handleResize() {
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.getElementById('mainContent');
  if (!sidebar || !mainContent) return;

  if (window.innerWidth <= 768) {
    sidebar.classList.remove('collapsed');
    mainContent.classList.remove('sidebar-collapsed');
  }
}

function focusReminderComposer() {
  showModal('createReminderModal');
  const input = document.getElementById('reminderTextInput');
  if (!input) return;
  setTimeout(() => input.focus(), 50);
}

function goToCreate(kind) {
  if (kind !== 'reminder') return;

  const endpoint = document.body.getAttribute('data-endpoint');
  if (endpoint === 'index') {
    focusReminderComposer();
    return;
  }

  sessionStorage.setItem('openCreateReminder', '1');
  window.location.href = '/';
}

function showInstallButtons() {
  const button = document.getElementById('installPwaBtn');
  const chip = document.getElementById('installChip');
  if (button) button.style.display = 'inline-flex';
  if (chip) chip.style.display = 'inline-flex';
}

function hideInstallButtons() {
  const button = document.getElementById('installPwaBtn');
  const chip = document.getElementById('installChip');
  if (button) button.style.display = 'none';
  if (chip) chip.style.display = 'none';
}

function checkStandalone() {
  return (
    (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) ||
    window.navigator.standalone === true ||
    document.referrer.includes('android-app://')
  );
}

async function installPwa() {
  const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const container = document.getElementById('systemInfoContent');

  if (isIos) {
    if (container) {
      container.innerHTML = `
        <div style="text-align:left">
          <p>Para instalar no iPhone ou iPad:</p>
          <ol style="padding-left:18px">
            <li>Abra o menu de compartilhamento do Safari.</li>
            <li>Escolha <strong>Adicionar à Tela de Início</strong>.</li>
            <li>Confirme para instalar o Mindly.</li>
          </ol>
        </div>
      `;
    }
    showModal('systemInfoModal');
    return;
  }

  if (!deferredPrompt) {
    if (container) {
      container.innerHTML = `
        <div style="text-align:left">
          <p>Seu navegador não mostrou o instalador automático.</p>
          <p>Procure a opção <strong>Instalar app</strong> ou <strong>Adicionar à tela inicial</strong> no menu do navegador.</p>
        </div>
      `;
    }
    showModal('systemInfoModal');
    return;
  }

  deferredPrompt.prompt();
  const choice = await deferredPrompt.userChoice.catch(() => ({ outcome: 'dismissed' }));
  if (choice.outcome === 'accepted') {
    showToast('Instalação iniciada.', 'success');
  } else {
    showToast('Instalação cancelada.', 'info');
  }
  deferredPrompt = null;
}

function restoreSidebarPreference() {
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.getElementById('mainContent');
  if (!sidebar || !mainContent || window.innerWidth <= 768) return;

  const saved = loadSidebarPref();
  const collapsed = saved === null ? true : saved;
  sidebar.classList.toggle('collapsed', collapsed);
  mainContent.classList.toggle('sidebar-collapsed', collapsed);
}

function initPasswordToggle() {
  document.body.addEventListener('click', (event) => {
    const button = event.target.closest('[data-toggle="password"]');
    if (!button) return;

    const form = button.closest('form');
    const input = form?.querySelector('input[type="password"], input[name="password"]');
    if (!input) return;

    const shouldReveal = input.type === 'password';
    input.type = shouldReveal ? 'text' : 'password';
    button.setAttribute('aria-pressed', String(shouldReveal));
    button.title = shouldReveal ? 'Ocultar senha' : 'Mostrar ou ocultar senha';
    button.textContent = shouldReveal ? '🙈' : '👁️';
  });
}

function initModals() {
  document.addEventListener('click', (event) => {
    if (event.target.classList.contains('modal')) {
      closeModal(event.target.id);
    }
  });

  const confirmDeleteButton = document.getElementById('confirmDelete');
  if (confirmDeleteButton) {
    confirmDeleteButton.addEventListener('click', executeDelete);
  }
}

function initFlashes() {
  document.querySelectorAll('#toastContainer .flash').forEach((toast, index) => {
    setTimeout(() => hideToast(toast), 4200 + index * 300);
  });
}

function initPwa() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js?v=cleanup5').catch(() => {});
  }

  const standalone = checkStandalone();
  if (!standalone) {
    showInstallButtons();
  }

  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    deferredPrompt = event;
    if (!checkStandalone()) {
      showInstallButtons();
    }
  });

  window.addEventListener('appinstalled', () => {
    hideInstallButtons();
    showToast('App instalado com sucesso.', 'success');
  });
}

function initPageActions() {
  try {
    const endpoint = document.body.getAttribute('data-endpoint');
    if (sessionStorage.getItem('openCreateReminder') === '1' && endpoint === 'index') {
      sessionStorage.removeItem('openCreateReminder');
      focusReminderComposer();
    }
  } catch (_error) {}
}

window.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initPasswordToggle();
  initModals();
  initFlashes();
  initPwa();
  initPageActions();
  restoreSidebarPreference();
  handleResize();

  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission().catch(() => {});
  }

  checkNotifications();
  clearInterval(notificationInterval);
  notificationInterval = setInterval(checkNotifications, 30000);
});

window.addEventListener('resize', handleResize);

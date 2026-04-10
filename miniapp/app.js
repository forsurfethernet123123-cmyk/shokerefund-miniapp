const tg = window.Telegram?.WebApp;
const mode = new URL(window.location.href).searchParams.get("mode") === "admin" ? "admin" : "user";
const SERVICES = [
  "🍔 Яндекс Еда",
  "🚗 Купер",
  "🛒 Яндекс Лавка",
  "🛵 Самокат",
  "🥗 Delivery Club",
];
const ADMIN_FILTERS = [
  ["all", "Все"],
  ["new", "Новые"],
  ["in_progress", "В работе"],
  ["waiting_user", "Ждёт клиента"],
  ["awaiting_payment", "Ожидает оплату"],
  ["payment_review", "Проверка оплаты"],
  ["closed", "Закрытые"],
  ["rejected", "Отклонённые"],
];
const STORAGE_KEYS = {
  session: "sr_session_token",
  theme: "sr_theme",
  saveCreds: "sr_save_credentials",
  login: "sr_saved_login",
  password: "sr_saved_password",
};

const state = {
  mode,
  initData: tg?.initData || "",
  sessionToken: localStorage.getItem(STORAGE_KEYS.session) || "",
  theme: localStorage.getItem(STORAGE_KEYS.theme) || (tg?.colorScheme === "light" ? "light" : "dark"),
  selectedService: SERVICES[0],
  selectedFiles: [],
  selectedTicketId: null,
  selectedPaymentMethod: null,
  currentTicket: null,
  tickets: [],
  messages: [],
  attachments: [],
  paymentMethods: [],
  promoUsed: false,
  promoMeta: { code: "BUFF", percent: 5, maxUses: 100, remainingUses: 100, used: false },
  adminFilter: "all",
  adminSearch: "",
  adminTickets: [],
  adminSummary: {},
  adminSelectedId: null,
  admins: [],
};

const el = (id) => document.getElementById(id);
const dom = {
  heroEyebrow: el("heroEyebrow"),
  heroTitle: el("heroTitle"),
  heroSubtitle: el("heroSubtitle"),
  modeBadge: el("modeBadge"),
  globalAlert: el("globalAlert"),
  userApp: el("userApp"),
  adminApp: el("adminApp"),
  themeDarkButton: el("themeDarkButton"),
  themeLightButton: el("themeLightButton"),

  telegramUserBadge: el("telegramUserBadge"),
  profileId: el("profileId"),
  profileUsername: el("profileUsername"),
  profileName: el("profileName"),
  channelLink: el("channelLink"),
  reviewsLink: el("reviewsLink"),
  agreementLink: el("agreementLink"),

  authTitle: el("authTitle"),
  authStatusChip: el("authStatusChip"),
  registerBox: el("registerBox"),
  loginBox: el("loginBox"),
  cabinetBox: el("cabinetBox"),
  registerLogin: el("registerLogin"),
  registerPassword: el("registerPassword"),
  registerButton: el("registerButton"),
  registerRemember: el("registerRemember"),
  loginValue: el("loginValue"),
  loginPassword: el("loginPassword"),
  loginButton: el("loginButton"),
  loginRemember: el("loginRemember"),
  logoutButton: el("logoutButton"),
  cabinetLogin: el("cabinetLogin"),
  resetPasswordToggle: el("resetPasswordToggle"),
  resetBox: el("resetBox"),
  resetLogin: el("resetLogin"),
  resetPassword: el("resetPassword"),
  resetButton: el("resetButton"),
  resetRemember: el("resetRemember"),

  ticketFormCard: el("ticketFormCard"),
  serviceGrid: el("serviceGrid"),
  ticketAmount: el("ticketAmount"),
  ticketDescription: el("ticketDescription"),
  summaryCommission: el("summaryCommission"),
  summaryOrder: el("summaryOrder"),
  summaryAfter: el("summaryAfter"),
  createTicketButton: el("createTicketButton"),
  historyCard: el("historyCard"),
  historyCount: el("historyCount"),
  ticketHistory: el("ticketHistory"),

  activeTicketCard: el("activeTicketCard"),
  ticketTitle: el("ticketTitle"),
  ticketStatus: el("ticketStatus"),
  ticketService: el("ticketService"),
  ticketAmountValue: el("ticketAmountValue"),
  ticketUpdated: el("ticketUpdated"),
  ticketDescriptionValue: el("ticketDescriptionValue"),

  paymentCard: el("paymentCard"),
  paymentStatusChip: el("paymentStatusChip"),
  invoiceAmountValue: el("invoiceAmountValue"),
  promoDiscountValue: el("promoDiscountValue"),
  payableAmountValue: el("payableAmountValue"),
  invoiceNoteValue: el("invoiceNoteValue"),
  promoInput: el("promoInput"),
  applyPromoButton: el("applyPromoButton"),
  promoHint: el("promoHint"),
  paymentMethodGrid: el("paymentMethodGrid"),
  verifyPaymentButton: el("verifyPaymentButton"),

  uploadCard: el("uploadCard"),
  photoInput: el("photoInput"),
  uploadPhotosButton: el("uploadPhotosButton"),
  selectedFilesHint: el("selectedFilesHint"),
  attachmentGallery: el("attachmentGallery"),
  attachmentCount: el("attachmentCount"),

  chatCard: el("chatCard"),
  userMessages: el("userMessages"),
  userReplyInput: el("userReplyInput"),
  userReplyButton: el("userReplyButton"),

  adminSummary: el("adminSummary"),
  adminStatusChip: el("adminStatusChip"),
  adminFilters: el("adminFilters"),
  adminSearch: el("adminSearch"),
  adminSearchButton: el("adminSearchButton"),
  ticketCounter: el("ticketCounter"),
  ticketList: el("ticketList"),
  adminTicketTitle: el("adminTicketTitle"),
  adminTicketStatus: el("adminTicketStatus"),
  adminTicketMeta: el("adminTicketMeta"),
  assignBox: el("assignBox"),
  assignAdminSelect: el("assignAdminSelect"),
  invoiceAmountInput: el("invoiceAmountInput"),
  invoiceNoteBox: el("invoiceNoteBox"),
  invoiceNoteInput: el("invoiceNoteInput"),
  adminTicketActions: el("adminTicketActions"),
  adminAttachmentGallery: el("adminAttachmentGallery"),
  adminMessages: el("adminMessages"),
  adminReplyInput: el("adminReplyInput"),
  adminReplyButton: el("adminReplyButton"),
  paymentDecisionSelect: el("paymentDecisionSelect"),
  paymentProviderRefInput: el("paymentProviderRefInput"),
  paymentNoteInput: el("paymentNoteInput"),
  paymentDecisionButton: el("paymentDecisionButton"),
};

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (m) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[m]);
}
function setAlert(text, type = "info") {
  if (!text) {
    dom.globalAlert.className = "alert hidden";
    dom.globalAlert.textContent = "";
    return;
  }
  dom.globalAlert.className = `alert ${type}`;
  dom.globalAlert.textContent = text;
}
function formatRub(value) {
  const num = Number(value || 0);
  return `${new Intl.NumberFormat("ru-RU").format(Math.round(num))} ₽`;
}
function parseAmount(value) {
  const normalized = String(value || "").replace(/\s+/g, "").replace(/,/g, ".").replace(/[^\d.]/g, "");
  const num = Number(normalized);
  return Number.isFinite(num) ? num : 0;
}
function requireTelegram() {
  if (state.initData) return true;
  setAlert("Открой кабинет из Telegram, чтобы авторизация работала корректно.", "error");
  return false;
}
function saveToken(token) {
  state.sessionToken = token || "";
  if (token) localStorage.setItem(STORAGE_KEYS.session, token);
  else localStorage.removeItem(STORAGE_KEYS.session);
}
function rememberCredentials(login, password, shouldRemember) {
  localStorage.setItem(STORAGE_KEYS.saveCreds, shouldRemember ? "1" : "0");
  if (!shouldRemember) {
    localStorage.removeItem(STORAGE_KEYS.login);
    localStorage.removeItem(STORAGE_KEYS.password);
    return;
  }
  localStorage.setItem(STORAGE_KEYS.login, login || "");
  localStorage.setItem(STORAGE_KEYS.password, password || "");
}
function hydrateRememberedCredentials() {
  const save = localStorage.getItem(STORAGE_KEYS.saveCreds) !== "0";
  const savedLogin = localStorage.getItem(STORAGE_KEYS.login) || "";
  const savedPassword = localStorage.getItem(STORAGE_KEYS.password) || "";
  [dom.registerRemember, dom.loginRemember, dom.resetRemember].forEach((x) => { if (x) x.checked = save; });
  if (savedLogin) {
    dom.loginValue.value = savedLogin;
    dom.resetLogin.value = savedLogin;
    dom.registerLogin.value = savedLogin;
  }
  if (savedPassword) {
    dom.loginPassword.value = savedPassword;
    dom.resetPassword.value = savedPassword;
    dom.registerPassword.value = savedPassword;
  }
}
function applyTheme(theme) {
  state.theme = theme === "light" ? "light" : "dark";
  document.body.dataset.theme = state.theme;
  localStorage.setItem(STORAGE_KEYS.theme, state.theme);
  dom.themeDarkButton.classList.toggle("active", state.theme === "dark");
  dom.themeLightButton.classList.toggle("active", state.theme === "light");
  tg?.setHeaderColor?.(state.theme === "dark" ? "#101828" : "#f4f7fb");
  tg?.setBackgroundColor?.(state.theme === "dark" ? "#07111f" : "#f4f7fb");
}
async function apiGet(path, params = {}) {
  const url = new URL(path, window.location.origin);
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v); });
  const res = await fetch(url.toString(), { credentials: "same-origin" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.ok === false) throw new Error(data.message || data.error || `HTTP ${res.status}`);
  return data;
}
async function apiPost(path, payload = {}) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.ok === false) throw new Error(data.message || data.error || `HTTP ${res.status}`);
  return data;
}
function userPayload(extra = {}) {
  return { initData: state.initData, sessionToken: state.sessionToken, ...extra };
}

function updateHero() {
  const isAdmin = state.mode === "admin";
  dom.modeBadge.textContent = isAdmin ? "ADMIN" : "USER";
  dom.heroEyebrow.textContent = isAdmin ? "Панель администратора" : "ShokeRefund";
  dom.heroTitle.textContent = isAdmin ? "Управление тикетами" : "ShokeRefund";
  dom.heroSubtitle.textContent = isAdmin
    ? "Работай с тикетами, назначай ответственных, выставляй счёт и веди диалог с клиентом в одном окне."
    : "Оформляй заявки, загружай фото заказа, отслеживай статус, получай счёт и выбирай способ оплаты внутри кабинета.";
  dom.userApp.classList.toggle("hidden", isAdmin);
  dom.adminApp.classList.toggle("hidden", !isAdmin);
}

function renderServices() {
  dom.serviceGrid.innerHTML = "";
  SERVICES.forEach((service) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `service-card ${state.selectedService === service ? "active" : ""}`;
    btn.innerHTML = `<strong>${escapeHtml(service)}</strong><span>Выбери сервис для обращения</span>`;
    btn.addEventListener("click", () => {
      state.selectedService = service;
      renderServices();
    });
    dom.serviceGrid.appendChild(btn);
  });
}
function updateSummary() {
  const amount = parseAmount(dom.ticketAmount.value);
  const commission = amount * 0.25;
  dom.summaryCommission.textContent = formatRub(commission);
  dom.summaryOrder.textContent = formatRub(amount);
  dom.summaryAfter.textContent = formatRub(Math.max(amount - commission, 0));
}
function renderAttachmentGallery(container, attachments = []) {
  container.innerHTML = "";
  if (!attachments.length) {
    container.innerHTML = `<div class="empty-block">Файлы пока не добавлены.</div>`;
    return;
  }
  attachments.forEach((attachment) => {
    const fig = document.createElement("figure");
    fig.className = "gallery-item";
    fig.innerHTML = `
      <a href="${escapeHtml(attachment.url)}" target="_blank" rel="noreferrer">
        <img src="${escapeHtml(attachment.url)}" alt="${escapeHtml(attachment.filename || "Фото")}" loading="lazy" />
        <figcaption>
          <strong>${escapeHtml(attachment.filename || "Фото")}</strong>
          <span>${escapeHtml(attachment.created_at_label || "")}</span>
        </figcaption>
      </a>`;
    container.appendChild(fig);
  });
}
function renderMessages(container, messages = [], mineRole = "user") {
  container.innerHTML = "";
  if (!messages.length) {
    container.innerHTML = `<div class="empty-chat">Сообщений пока нет.</div>`;
    return;
  }
  messages.forEach((msg) => {
    const role = msg.sender_role || "system";
    const mine = role === mineRole;
    const author = role === "user" ? "Клиент" : role === "admin" ? (msg.sender_name || "Поддержка") : "Система";
    const created = msg.created_at ? new Date(msg.created_at * 1000).toLocaleString("ru-RU") : "";
    const item = document.createElement("div");
    item.className = `message ${mine ? "mine" : ""} ${role}`;
    item.innerHTML = `<div class="message-head"><span>${escapeHtml(author)}</span><span>${escapeHtml(created)}</span></div><div class="message-body">${escapeHtml(msg.text || "")}</div>`;
    container.appendChild(item);
  });
  container.scrollTop = container.scrollHeight;
}
function renderPaymentMethods() {
  dom.paymentMethodGrid.innerHTML = "";
  const methods = state.paymentMethods || [];
  methods.forEach((method) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `method-card ${state.selectedPaymentMethod === method.key ? "active" : ""}`;
    btn.innerHTML = `<strong>${escapeHtml(method.label)}</strong><span>${escapeHtml(method.description || "")}</span>`;
    btn.addEventListener("click", () => runAction(async () => {
      if (!state.currentTicket) return;
      await apiPost(`/api/user/tickets/${state.currentTicket.id}/payment-method`, userPayload({ method: method.key }));
      state.selectedPaymentMethod = method.key;
      await openUserTicket(state.currentTicket.id, false);
      setAlert(`Способ оплаты выбран: ${method.label}.`, "success");
    }));
    dom.paymentMethodGrid.appendChild(btn);
  });
}
function renderHistory() {
  dom.historyCard.classList.toggle("hidden", !state.tickets.length);
  dom.historyCount.textContent = String(state.tickets.length);
  dom.ticketHistory.innerHTML = "";
  if (!state.tickets.length) {
    dom.ticketHistory.innerHTML = `<div class="empty-block">Заявок пока нет.</div>`;
    return;
  }
  state.tickets.forEach((ticket) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = `ticket-item ${state.selectedTicketId === ticket.id ? "active" : ""}`;
    item.innerHTML = `
      <div class="ticket-top"><strong>#${ticket.id} · ${escapeHtml(ticket.service)}</strong><span>${escapeHtml(ticket.status_label || ticket.status)}</span></div>
      <div class="ticket-meta"><span>${formatRub(ticket.amount || 0)}</span><span>${escapeHtml(ticket.updated_at_label || "")}</span></div>
      <div class="ticket-desc">${escapeHtml(ticket.description || "Без описания")}</div>`;
    item.addEventListener("click", () => runAction(() => openUserTicket(ticket.id, true)));
    dom.ticketHistory.appendChild(item);
  });
}
function renderUserProfile(data) {
  dom.telegramUserBadge.textContent = data.user.username ? `@${data.user.username}` : `ID ${data.user.id}`;
  dom.profileId.textContent = data.user.id;
  dom.profileUsername.textContent = data.user.username ? `@${data.user.username}` : "—";
  dom.profileName.textContent = data.user.fullName || "—";
  dom.channelLink.href = data.links.channel;
  dom.reviewsLink.href = data.links.reviews;
  dom.agreementLink.href = data.links.agreement;
  dom.cabinetLogin.textContent = data.account.login || "—";
}
function renderAuthState(data) {
  const account = data.account;
  const hasPassword = !!account.hasPassword;
  const sessionValid = !!account.sessionValid;
  state.promoUsed = !!account.promoBuffUsed;
  state.promoMeta = data.promo || state.promoMeta;
  dom.registerBox.classList.add("hidden");
  dom.loginBox.classList.add("hidden");
  dom.cabinetBox.classList.add("hidden");
  dom.ticketFormCard.classList.add("hidden");
  if (!hasPassword) {
    dom.authTitle.textContent = "Создай логин и пароль";
    dom.authStatusChip.textContent = "первый вход";
    dom.registerBox.classList.remove("hidden");
    return;
  }
  if (!sessionValid) {
    dom.authTitle.textContent = "Вход в кабинет";
    dom.authStatusChip.textContent = "требуется вход";
    dom.loginBox.classList.remove("hidden");
    return;
  }
  dom.authTitle.textContent = "Кабинет активен";
  dom.authStatusChip.textContent = "авторизован";
  dom.cabinetBox.classList.remove("hidden");
  dom.ticketFormCard.classList.remove("hidden");
}
function updatePromoHint() {
  const promo = state.promoMeta || { code: "BUFF", percent: 5, maxUses: 100, remainingUses: 100, used: false };
  if (!dom.promoHint) return;
  const remaining = Number(promo.remainingUses || 0);
  const percent = Number(promo.percent || 5);
  if (promo.used) {
    dom.promoHint.textContent = `${promo.code} уже был активирован на этом аккаунте. Повторное использование недоступно.`;
    return;
  }
  if (remaining <= 0) {
    dom.promoHint.textContent = `${promo.code} больше недоступен: лимит 100 активаций исчерпан.`;
    return;
  }
  dom.promoHint.textContent = `${promo.code} даёт скидку ${percent}% от суммы счёта. Каждый пользователь может активировать код один раз. Осталось активаций: ${remaining} из ${promo.maxUses}.`;
}

function renderUserTicket(ticket, messages = [], attachments = []) {
  state.currentTicket = ticket || null;
  state.selectedTicketId = ticket?.id || null;
  state.messages = messages || [];
  state.attachments = attachments || ticket?.attachments || [];
  renderHistory();
  updatePromoHint();

  const hasTicket = !!ticket;
  dom.activeTicketCard.classList.toggle("hidden", !hasTicket);
  dom.uploadCard.classList.toggle("hidden", !hasTicket);
  dom.chatCard.classList.toggle("hidden", !hasTicket);
  dom.paymentCard.classList.toggle("hidden", !hasTicket || !(ticket.invoice_amount > 0 || ticket.payment_status !== "none"));

  if (!hasTicket) {
    renderAttachmentGallery(dom.attachmentGallery, []);
    renderMessages(dom.userMessages, [], "user");
    return;
  }
  dom.ticketTitle.textContent = `Заявка #${ticket.id}`;
  dom.ticketStatus.textContent = ticket.status_label || ticket.status || "—";
  dom.ticketService.textContent = ticket.service || "—";
  dom.ticketAmountValue.textContent = formatRub(ticket.amount || 0);
  dom.ticketUpdated.textContent = ticket.updated_at_label || "—";
  dom.ticketDescriptionValue.textContent = ticket.description || "Без комментария";
  dom.paymentStatusChip.textContent = ticket.payment_status_label || "—";
  dom.invoiceAmountValue.textContent = formatRub(ticket.invoice_amount || 0);
  dom.promoDiscountValue.textContent = formatRub(ticket.promo_discount || 0);
  dom.payableAmountValue.textContent = formatRub(ticket.payable_amount || 0);
  dom.invoiceNoteValue.textContent = ticket.invoice_note || "Счёт ещё не выставлен.";
  dom.verifyPaymentButton.disabled = !ticket.payment_method || !(ticket.invoice_amount > 0);
  dom.applyPromoButton.disabled = state.promoUsed || ticket.promo_applied || Number(state.promoMeta?.remainingUses || 0) <= 0;
  if (ticket.promo_applied) dom.promoInput.value = ticket.promo_code || "BUFF";
  state.selectedPaymentMethod = ticket.payment_method || null;
  renderPaymentMethods();
  renderAttachmentGallery(dom.attachmentGallery, state.attachments);
  dom.attachmentCount.textContent = `${state.attachments.length}`;
  renderMessages(dom.userMessages, state.messages, "user");
}

async function bootstrapUser() {
  if (!requireTelegram()) return;
  const data = await apiGet("/api/user/bootstrap", { initData: state.initData, sessionToken: state.sessionToken });
  state.tickets = data.tickets || [];
  state.paymentMethods = data.paymentMethods || [];
  state.promoMeta = data.promo || state.promoMeta;
  renderUserProfile(data);
  renderAuthState(data);
  renderHistory();
  renderUserTicket(data.activeTicket, data.messages || [], data.activeTicket?.attachments || []);
}
async function openUserTicket(ticketId, ensureSession = true) {
  if (ensureSession && !state.sessionToken) return;
  const data = await apiGet(`/api/user/tickets/${ticketId}`, { initData: state.initData, sessionToken: state.sessionToken });
  const idx = state.tickets.findIndex((x) => x.id === ticketId);
  if (idx >= 0) state.tickets[idx] = data.ticket;
  renderUserTicket(data.ticket, data.messages, data.attachments);
}
async function registerCabinet() {
  const login = dom.registerLogin.value.trim().toLowerCase();
  const password = dom.registerPassword.value;
  if (!login || !password) return setAlert("Заполни логин и пароль.", "error");
  const data = await apiPost("/api/user/account/register", userPayload({ login, password }));
  saveToken(data.token);
  rememberCredentials(login, password, !!dom.registerRemember.checked);
  setAlert("Кабинет создан. Вход выполнен.", "success");
  await bootstrapUser();
}
async function loginCabinet() {
  const login = dom.loginValue.value.trim().toLowerCase();
  const password = dom.loginPassword.value;
  if (!login || !password) return setAlert("Введи логин и пароль.", "error");
  const data = await apiPost("/api/user/account/login", { initData: state.initData, login, password });
  saveToken(data.token);
  rememberCredentials(login, password, !!dom.loginRemember.checked);
  setAlert("Вход выполнен.", "success");
  await bootstrapUser();
}
async function logoutCabinet() {
  try { await apiPost("/api/user/account/logout", { sessionToken: state.sessionToken }); } catch (_) {}
  saveToken("");
  setAlert("Сессия завершена.", "info");
  await bootstrapUser();
}
async function resetPassword() {
  const login = dom.resetLogin.value.trim().toLowerCase();
  const password = dom.resetPassword.value;
  if (!login || !password) return setAlert("Укажи новый логин и пароль.", "error");
  const data = await apiPost("/api/user/account/reset-password", { initData: state.initData, login, password });
  saveToken(data.token);
  rememberCredentials(login, password, !!dom.resetRemember.checked);
  dom.resetBox.classList.add("hidden");
  setAlert("Новые данные сохранены.", "success");
  await bootstrapUser();
}
async function createTicket() {
  const amount = parseAmount(dom.ticketAmount.value);
  const description = dom.ticketDescription.value.trim();
  if (amount < 100 || amount > 100000) return setAlert("Сумма должна быть от 100 до 100000 ₽.", "error");
  const data = await apiPost("/api/user/tickets/create", userPayload({ service: state.selectedService, amount, description }));
  state.tickets = data.tickets || state.tickets;
  dom.ticketAmount.value = "";
  dom.ticketDescription.value = "";
  updateSummary();
  setAlert("Заявка создана. Теперь можно прикрепить фото и следить за ответами поддержки.", "success");
  renderUserTicket(data.ticket, data.messages, data.attachments);
}
function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      const [, base64] = result.split(",");
      resolve(base64 || "");
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
async function uploadSelectedPhotos() {
  if (!state.currentTicket) return setAlert("Сначала создай заявку.", "error");
  if (!state.selectedFiles.length) return setAlert("Выбери хотя бы одно изображение.", "error");
  for (const file of state.selectedFiles) {
    const contentBase64 = await readFileAsBase64(file);
    const data = await apiPost(`/api/user/tickets/${state.currentTicket.id}/attachments`, userPayload({ filename: file.name, mimeType: file.type || "image/jpeg", contentBase64 }));
    state.tickets = data.tickets || state.tickets;
    renderUserTicket(data.ticket, data.messages, data.attachments);
  }
  state.selectedFiles = [];
  dom.photoInput.value = "";
  dom.selectedFilesHint.textContent = "Файлы загружены.";
  setAlert("Фото успешно загружены.", "success");
}
async function sendUserReply() {
  if (!state.currentTicket) return;
  const text = dom.userReplyInput.value.trim();
  if (!text) return;
  const data = await apiPost(`/api/user/tickets/${state.currentTicket.id}/reply`, userPayload({ text }));
  state.tickets = data.tickets || state.tickets;
  dom.userReplyInput.value = "";
  renderUserTicket(data.ticket, data.messages, data.attachments);
}
async function applyPromo() {
  if (!state.currentTicket) return;
  const code = dom.promoInput.value.trim().toUpperCase();
  if (!code) return setAlert("Введи промокод.", "error");
  const data = await apiPost(`/api/user/tickets/${state.currentTicket.id}/apply-promo`, userPayload({ code }));
  state.promoUsed = true;
  if (state.promoMeta) {
    state.promoMeta.used = true;
    state.promoMeta.remainingUses = Math.max(0, Number(state.promoMeta.remainingUses || 0) - 1);
  }
  state.tickets = data.tickets || state.tickets;
  setAlert("Промокод применён.", "success");
  renderUserTicket(data.ticket, data.messages, data.attachments);
}
async function verifyPayment() {
  if (!state.currentTicket) return;
  if (!state.currentTicket.payment_method) return setAlert("Сначала выбери способ оплаты.", "error");
  const data = await apiPost(`/api/user/tickets/${state.currentTicket.id}/check-payment`, userPayload());
  state.tickets = data.tickets || state.tickets;
  setAlert("Запрос на проверку оплаты отправлен. Ожидайте подтверждения от поддержки.", "success");
  renderUserTicket(data.ticket, data.messages, data.attachments);
}

function renderAdminSummary(summary = {}) {
  dom.adminSummary.innerHTML = "";
  const items = [
    ["Пользователи", summary.users || 0],
    ["Новые", summary.new || 0],
    ["В работе", summary.in_progress || 0],
    ["Ждут клиента", summary.waiting_user || 0],
    ["Счёт", summary.awaiting_payment || 0],
    ["Проверка оплаты", summary.payment_review || 0],
    ["Закрытые", summary.closed || 0],
    ["Отклонённые", summary.rejected || 0],
    ["Оплачено", formatRub(summary.revenue_paid || 0)],
    ["Открытые счета", formatRub(summary.revenue_open || 0)],
  ];
  items.forEach(([title, value]) => {
    const box = document.createElement("div");
    box.className = "summary-card neutral";
    box.innerHTML = `<span>${escapeHtml(title)}</span><strong>${escapeHtml(value)}</strong>`;
    dom.adminSummary.appendChild(box);
  });
}
function renderAdminFilters() {
  dom.adminFilters.innerHTML = "";
  ADMIN_FILTERS.forEach(([key, label]) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `btn ${state.adminFilter === key ? "primary" : "ghost"}`;
    btn.textContent = label;
    btn.addEventListener("click", () => runAction(async () => {
      state.adminFilter = key;
      renderAdminFilters();
      await loadAdminTickets();
    }));
    dom.adminFilters.appendChild(btn);
  });
}
function renderAdminTicketList() {
  dom.ticketCounter.textContent = String(state.adminTickets.length);
  dom.ticketList.innerHTML = "";
  if (!state.adminTickets.length) {
    dom.ticketList.innerHTML = `<div class="empty-block">Тикеты не найдены.</div>`;
    return;
  }
  state.adminTickets.forEach((ticket) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `ticket-item ${state.adminSelectedId === ticket.id ? "active" : ""}`;
    btn.innerHTML = `
      <div class="ticket-top"><strong>#${ticket.id} · ${escapeHtml(ticket.service)}</strong><span>${escapeHtml(ticket.status_label || ticket.status)}</span></div>
      <div class="ticket-meta"><span>User ${ticket.user_id}</span><span>${formatRub(ticket.amount || 0)}</span></div>
      <div class="ticket-meta"><span>${ticket.assigned_admin_name || "Не назначен"}</span><span>${ticket.payment_status_label || ""}</span></div>
      <div class="ticket-desc">${escapeHtml(ticket.description || "Без описания")}</div>`;
    btn.addEventListener("click", () => runAction(() => openAdminTicket(ticket.id)));
    dom.ticketList.appendChild(btn);
  });
}
function renderAdminTicket(ticket, messages = [], attachments = [], admins = []) {
  state.adminSelectedId = ticket?.id || null;
  renderAdminTicketList();
  if (!ticket) return;
  dom.adminTicketTitle.textContent = `Заявка #${ticket.id}`;
  dom.adminTicketStatus.textContent = ticket.status_label || ticket.status || "—";
  dom.adminTicketMeta.innerHTML = `
    <div class="info-grid three">
      <div class="info-card"><span>User ID</span><strong>${escapeHtml(ticket.user_id)}</strong></div>
      <div class="info-card"><span>Сервис</span><strong>${escapeHtml(ticket.service)}</strong></div>
      <div class="info-card"><span>Сумма заказа</span><strong>${formatRub(ticket.amount || 0)}</strong></div>
      <div class="info-card"><span>Ответственный</span><strong>${escapeHtml(ticket.assigned_admin_name || "Не назначен")}</strong></div>
      <div class="info-card"><span>Счёт</span><strong>${formatRub(ticket.invoice_amount || 0)}</strong></div>
      <div class="info-card"><span>Оплата</span><strong>${escapeHtml(ticket.payment_status_label || "—")}</strong></div>
    </div>
    <div class="description">${escapeHtml(ticket.description || "Без комментария")}</div>
    <div class="description top-gap">${escapeHtml(ticket.invoice_note || "Комментарий к счёту пока не добавлен.")}</div>`;
  dom.assignBox.classList.remove("hidden");
  dom.invoiceNoteBox.classList.remove("hidden");
  dom.assignAdminSelect.innerHTML = admins.map((admin) => `<option value="${admin.id}" ${ticket.assigned_admin === admin.id ? "selected" : ""}>${escapeHtml(admin.name)}</option>`).join("");
  dom.invoiceAmountInput.value = ticket.invoice_amount ? String(ticket.invoice_amount) : "";
  dom.invoiceNoteInput.value = ticket.invoice_note || "";
  renderMessages(dom.adminMessages, messages, "admin");
  renderAttachmentGallery(dom.adminAttachmentGallery, attachments);
  renderAdminActions(ticket);
}
function renderAdminActions(ticket) {
  dom.adminTicketActions.innerHTML = "";
  const actions = [
    ["Назначить", () => adminAssign(ticket.id), "secondary"],
    ["В работу", () => adminStatus(ticket.id, "in_progress"), "ghost"],
    ["Ждёт клиента", () => adminStatus(ticket.id, "waiting_user"), "ghost"],
    ["Отклонить", () => adminStatus(ticket.id, "rejected"), "ghost"],
    ["Выставить счёт", () => adminInvoice(ticket.id), "primary"],
  ];
  actions.forEach(([label, handler, kind]) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `btn ${kind}`;
    btn.textContent = label;
    btn.addEventListener("click", () => runAction(handler));
    dom.adminTicketActions.appendChild(btn);
  });
}
async function bootstrapAdmin() {
  if (!requireTelegram()) return;
  const data = await apiGet("/api/admin/bootstrap", { initData: state.initData });
  state.adminSummary = data.summary || {};
  state.adminTickets = data.tickets || [];
  state.admins = data.admins || [];
  dom.adminStatusChip.textContent = "онлайн";
  renderAdminSummary(state.adminSummary);
  renderAdminFilters();
  renderAdminTicketList();
}
async function loadAdminTickets() {
  const data = await apiGet("/api/admin/tickets", { initData: state.initData, status: state.adminFilter, search: state.adminSearch });
  state.adminTickets = data.tickets || [];
  state.adminSummary = data.summary || state.adminSummary;
  renderAdminSummary(state.adminSummary);
  renderAdminTicketList();
}
async function openAdminTicket(ticketId) {
  const data = await apiGet(`/api/admin/tickets/${ticketId}`, { initData: state.initData });
  state.adminSelectedId = ticketId;
  state.admins = data.admins || state.admins;
  renderAdminTicket(data.ticket, data.messages || [], data.attachments || [], state.admins);
}
async function adminAssign(ticketId) {
  const adminId = Number(dom.assignAdminSelect.value || 0);
  await apiPost(`/api/admin/tickets/${ticketId}/assign`, { initData: state.initData, adminId });
  await bootstrapAdmin();
  await openAdminTicket(ticketId);
  setAlert("Ответственный обновлён.", "success");
}
async function adminStatus(ticketId, status) {
  await apiPost(`/api/admin/tickets/${ticketId}/status`, { initData: state.initData, status });
  await bootstrapAdmin();
  await openAdminTicket(ticketId);
  setAlert("Статус обновлён.", "success");
}
async function adminInvoice(ticketId) {
  const amount = parseAmount(dom.invoiceAmountInput.value);
  const note = dom.invoiceNoteInput.value.trim();
  if (amount <= 0) return setAlert("Укажи сумму счёта.", "error");
  await apiPost(`/api/admin/tickets/${ticketId}/invoice`, { initData: state.initData, amount, note });
  await bootstrapAdmin();
  await openAdminTicket(ticketId);
  setAlert("Счёт выставлен. Пользователь увидит кнопку оплаты в кабинете.", "success");
}
async function sendAdminReply() {
  if (!state.adminSelectedId) return;
  const text = dom.adminReplyInput.value.trim();
  if (!text) return;
  await apiPost(`/api/admin/tickets/${state.adminSelectedId}/reply`, { initData: state.initData, text });
  dom.adminReplyInput.value = "";
  await bootstrapAdmin();
  await openAdminTicket(state.adminSelectedId);
}
async function savePaymentDecision() {
  if (!state.adminSelectedId) return;
  await apiPost(`/api/admin/tickets/${state.adminSelectedId}/payment`, {
    initData: state.initData,
    decision: dom.paymentDecisionSelect.value,
    providerRef: dom.paymentProviderRefInput.value.trim(),
    note: dom.paymentNoteInput.value.trim(),
  });
  await bootstrapAdmin();
  await openAdminTicket(state.adminSelectedId);
  setAlert("Решение по оплате сохранено.", "success");
}

async function runAction(fn) {
  try {
    setAlert("");
    await fn();
  } catch (error) {
    console.error(error);
    setAlert(error.message || "Ошибка", "error");
  }
}
function bindEvents() {
  dom.themeDarkButton.addEventListener("click", () => applyTheme("dark"));
  dom.themeLightButton.addEventListener("click", () => applyTheme("light"));

  dom.registerButton?.addEventListener("click", () => runAction(registerCabinet));
  dom.loginButton?.addEventListener("click", () => runAction(loginCabinet));
  dom.logoutButton?.addEventListener("click", () => runAction(logoutCabinet));
  dom.resetPasswordToggle?.addEventListener("click", () => dom.resetBox.classList.toggle("hidden"));
  dom.resetButton?.addEventListener("click", () => runAction(resetPassword));

  dom.ticketAmount?.addEventListener("input", updateSummary);
  dom.createTicketButton?.addEventListener("click", () => runAction(createTicket));
  dom.photoInput?.addEventListener("change", (e) => {
    state.selectedFiles = Array.from(e.target.files || []).filter((file) => file.type.startsWith("image/"));
    dom.selectedFilesHint.textContent = state.selectedFiles.length
      ? `Выбрано ${state.selectedFiles.length} ${state.selectedFiles.length === 1 ? "изображение" : state.selectedFiles.length < 5 ? "изображения" : "изображений"}.`
      : "Файлы не выбраны.";
  });
  dom.uploadPhotosButton?.addEventListener("click", () => runAction(uploadSelectedPhotos));
  dom.userReplyButton?.addEventListener("click", () => runAction(sendUserReply));
  dom.userReplyInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); runAction(sendUserReply); }
  });
  dom.applyPromoButton?.addEventListener("click", () => runAction(applyPromo));
  dom.verifyPaymentButton?.addEventListener("click", () => runAction(verifyPayment));

  dom.adminSearchButton?.addEventListener("click", () => runAction(async () => {
    state.adminSearch = dom.adminSearch.value.trim();
    await loadAdminTickets();
  }));
  dom.adminReplyButton?.addEventListener("click", () => runAction(sendAdminReply));
  dom.adminReplyInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); runAction(sendAdminReply); }
  });
  dom.paymentDecisionButton?.addEventListener("click", () => runAction(savePaymentDecision));
}
async function init() {
  tg?.ready?.();
  tg?.expand?.();
  applyTheme(state.theme);
  updateHero();
  bindEvents();
  renderServices();
  updateSummary();
  hydrateRememberedCredentials();
  try {
    if (state.mode === "admin") await bootstrapAdmin();
    else await bootstrapUser();
  } catch (error) {
    console.error(error);
    setAlert(error.message || "Не удалось загрузить данные.", "error");
    if (state.mode === "admin") dom.adminStatusChip.textContent = "ошибка";
  }
}
init();

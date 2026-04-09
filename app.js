const tg = window.Telegram?.WebApp;
const url = new URL(window.location.href);
const SERVICES = [
  "🍔 Яндекс Еда",
  "🚗 Купер",
  "🛒 Яндекс Лавка",
  "🛵 Самокат",
  "🥗 Delivery Club",
];
const QUICK_REPLIES = [
  "Когда ответит оператор?",
  "Какие скриншоты нужны?",
  "Проверьте мой статус",
  "Я уже отправил доказательства",
];
const ADMIN_FILTERS = [
  { key: "all", label: "Все" },
  { key: "new", label: "Новые" },
  { key: "in_progress", label: "В работе" },
  { key: "done", label: "Завершённые" },
  { key: "rejected", label: "Отклонённые" },
];

const dom = {
  tabSwitch: byId("tabSwitch"),
  userView: byId("userView"),
  adminView: byId("adminView"),
  modeBadge: byId("modeBadge"),
  heroTitle: byId("heroTitle"),
  heroSubtitle: byId("heroSubtitle"),
  serviceGrid: byId("serviceGrid"),
  amountInput: byId("amountInput"),
  descriptionInput: byId("descriptionInput"),
  agreementCheckbox: byId("agreementCheckbox"),
  commissionValue: byId("commissionValue"),
  toPayValue: byId("toPayValue"),
  afterFeeValue: byId("afterFeeValue"),
  submitButton: byId("submitButton"),
  statusButton: byId("statusButton"),
  payloadPreview: byId("payloadPreview"),
  formStatus: byId("formStatus"),
  quickReplies: byId("quickReplies"),
  chatWrap: byId("chatWrap"),
  chatInput: byId("chatInput"),
  chatSendButton: byId("chatSendButton"),
  supportNote: byId("supportNote"),
  adminConnectionBadge: byId("adminConnectionBadge"),
  adminSummary: byId("adminSummary"),
  adminFilters: byId("adminFilters"),
  adminSearch: byId("adminSearch"),
  adminRefreshButton: byId("adminRefreshButton"),
  ticketList: byId("ticketList"),
  ticketsCounter: byId("ticketsCounter"),
  detailTitle: byId("detailTitle"),
  detailPills: byId("detailPills"),
  ticketMeta: byId("ticketMeta"),
  detailActions: byId("detailActions"),
  adminMessages: byId("adminMessages"),
  adminReplyInput: byId("adminReplyInput"),
  adminReplyButton: byId("adminReplyButton"),
};

const state = {
  mode: url.searchParams.get("mode") === "admin" ? "admin" : "user",
  service: SERVICES[0],
  amount: "",
  chatMessages: [],
  userTicket: null,
  adminConnected: false,
  adminFilter: "all",
  adminSearch: "",
  adminTickets: [],
  adminSelectedTicketId: null,
  adminSelectedTicket: null,
  adminMessages: [],
};

const api = {
  initData: tg?.initData || "",
  async get(path, params = {}) {
    const qs = new URLSearchParams();
    if (api.initData) qs.set("initData", api.initData);
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && `${v}` !== "") qs.set(k, v);
    });
    const res = await fetch(`${path}?${qs.toString()}`, { cache: "no-store" });
    return handleResponse(res);
  },
  async post(path, body = {}) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...body, initData: api.initData }),
    });
    return handleResponse(res);
  },
};

const demoAdminData = buildDemoAdminData();

init();

function init() {
  tg?.ready?.();
  tg?.expand?.();
  applyTelegramTheme();
  renderTabs();
  renderServices();
  renderQuickReplies();
  renderAdminFilters();
  bindEvents();
  updateSummary();
  renderPayload();
  setView(state.mode);
  syncMainButton();
}

function bindEvents() {
  dom.amountInput.addEventListener("input", (e) => {
    state.amount = e.target.value;
    updateSummary();
    renderPayload();
    syncMainButton();
  });
  dom.descriptionInput.addEventListener("input", () => {
    renderPayload();
  });
  dom.agreementCheckbox.addEventListener("change", () => {
    updateSummary();
    renderPayload();
    syncMainButton();
  });
  dom.submitButton.addEventListener("click", () => submitForm("create_ticket"));
  dom.statusButton.addEventListener("click", () => submitForm("open_status"));
  dom.chatSendButton.addEventListener("click", onUserChatSend);
  dom.chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      onUserChatSend();
    }
  });
  dom.adminRefreshButton.addEventListener("click", () => loadAdminTickets());
  dom.adminSearch.addEventListener("input", (e) => {
    state.adminSearch = e.target.value.trim();
    debounce(loadAdminTickets, 250)();
  });
  dom.adminReplyButton.addEventListener("click", sendAdminReply);
  dom.adminReplyInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendAdminReply();
    }
  });
  if (tg?.MainButton) {
    tg.MainButton.onClick(() => {
      if (state.mode === "admin") return;
      submitForm("create_ticket");
    });
  }
}

function renderTabs() {
  dom.tabSwitch.innerHTML = "";
  const chip = document.createElement("div");
  chip.className = "active";
  chip.textContent = state.mode === "admin" ? "Web Admin" : "Mini App клиента";
  dom.tabSwitch.appendChild(chip);
}

function setView(mode) {
  state.mode = mode;
  dom.userView.classList.toggle("active", mode === "user");
  dom.adminView.classList.toggle("active", mode === "admin");
  dom.modeBadge.textContent = mode === "admin" ? "ADMIN" : "USER";
  renderTabs();
  if (mode === "admin") {
    dom.heroTitle.textContent = "Web Admin для тикетов и быстрых ответов";
    dom.heroSubtitle.textContent = "Просматривай очереди, назначай ответственных, меняй статусы и отвечай клиентам прямо из чёрно‑фиолетово‑голубой панели.";
    bootAdmin();
  } else {
    dom.heroTitle.textContent = "Оформление заявок только через Mini App";
    dom.heroSubtitle.textContent = "В этой версии новый кейс нельзя создать обычными сообщениями в боте: сначала открой Mini App, заполни форму, а затем досылай файлы в чат.";
    bootUserSupport();
  }
  syncMainButton();
}

function renderServices() {
  dom.serviceGrid.innerHTML = "";
  SERVICES.forEach((service) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `service-card${state.service === service ? " selected" : ""}`;
    btn.innerHTML = `<strong>${service}</strong><span>Сервис доставки для оформления кейса</span>`;
    btn.addEventListener("click", () => {
      state.service = service;
      renderServices();
      renderPayload();
      updateSummary();
      tg?.HapticFeedback?.selectionChanged?.();
    });
    dom.serviceGrid.appendChild(btn);
  });
}

function renderQuickReplies() {
  dom.quickReplies.innerHTML = "";
  QUICK_REPLIES.forEach((item) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "secondary-btn";
    btn.textContent = item;
    btn.addEventListener("click", () => {
      dom.chatInput.value = item;
      onUserChatSend();
    });
    dom.quickReplies.appendChild(btn);
  });
}

function renderAdminFilters() {
  dom.adminFilters.innerHTML = "";
  ADMIN_FILTERS.forEach((item) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = item.label;
    btn.className = state.adminFilter === item.key ? "active" : "";
    btn.addEventListener("click", () => {
      state.adminFilter = item.key;
      renderAdminFilters();
      loadAdminTickets();
    });
    dom.adminFilters.appendChild(btn);
  });
}

function renderPayload() {
  dom.payloadPreview.textContent = JSON.stringify(buildPayload("create_ticket"), null, 2);
}

function buildPayload(action) {
  return {
    action,
    service: state.service,
    amount: getAmountNumber(),
    description: dom.descriptionInput.value.trim(),
    agreementAccepted: dom.agreementCheckbox.checked,
    source: "mini_app",
    uiVersion: "noir-v2",
    sentAt: new Date().toISOString(),
  };
}

function updateSummary() {
  const amount = getAmountNumber();
  const commission = amount * 0.25;
  const afterFee = Math.max(0, amount - commission);
  dom.commissionValue.textContent = formatRub(commission);
  dom.toPayValue.textContent = formatRub(commission);
  dom.afterFeeValue.textContent = formatRub(afterFee);
  dom.formStatus.textContent = isValid() ? "Форма готова" : "Заполни поля";
}

function syncMainButton() {
  if (!tg?.MainButton) return;
  if (state.mode === "admin") {
    tg.MainButton.hide();
    return;
  }
  tg.MainButton.setText(isValid() ? "Создать заявку" : "Заполни форму");
  tg.MainButton.show();
  if (isValid()) tg.MainButton.enable();
  else tg.MainButton.disable();
}

function submitForm(action) {
  if (action === "create_ticket" && !isValid()) {
    notify("Проверь форму", "Выбери сервис, введи сумму от 100 ₽ до 100000 ₽ и подтверди согласие.");
    return;
  }
  const payload = buildPayload(action);
  if (tg?.sendData) {
    tg.sendData(JSON.stringify(payload));
    tg?.HapticFeedback?.notificationOccurred?.("success");
    notify(
      action === "create_ticket" ? "Данные отправлены" : "Открываем статус",
      action === "create_ticket"
        ? "Вернись в чат: бот переведёт тебя к загрузке файлов и дальше покажет статус заявки."
        : "Бот откроет карточку твоей активной заявки."
    );
    setTimeout(() => tg.close?.(), 280);
  } else {
    notify("Демо‑режим", JSON.stringify(payload, null, 2));
  }
}

async function bootUserSupport() {
  state.chatMessages = buildSmartDemoMessages();
  renderUserMessages();
  if (!api.initData) return;
  try {
    const data = await api.get("/api/user/active-ticket");
    if (!data.ok || !data.ticket) return;
    state.userTicket = data.ticket;
    state.chatMessages = data.messages || [];
    dom.supportNote.textContent = `Активная заявка #${data.ticket.id} подключена. Новые сообщения попадут в этот чат и в панель администратора.`;
    renderUserMessages();
  } catch (_) {
    // keep demo state
  }
}

function renderUserMessages() {
  dom.chatWrap.innerHTML = "";
  (state.chatMessages || []).forEach((msg) => {
    const item = document.createElement("div");
    const cls = msg.sender_role === "user" || msg.author === "user" ? "user" : msg.sender_role === "system" || msg.author === "system" ? "system" : "support";
    item.className = `message ${cls}`;
    const name = cls === "user" ? "Ты" : cls === "system" ? "Система" : (msg.sender_name || "Поддержка");
    const timeLabel = msg.created_at ? formatTime(msg.created_at * 1000) : (msg.time || "сейчас");
    item.innerHTML = `
      <div class="message-head"><span>${escapeHtml(name)}</span><span>${escapeHtml(timeLabel)}</span></div>
      <div>${escapeHtml(msg.text || msg.content || "")}</div>
    `;
    dom.chatWrap.appendChild(item);
  });
  dom.chatWrap.scrollTop = dom.chatWrap.scrollHeight;
}

async function onUserChatSend() {
  const text = dom.chatInput.value.trim();
  if (!text) return;

  if (state.userTicket && api.initData) {
    try {
      const data = await api.post(`/api/user/tickets/${state.userTicket.id}/reply`, { text });
      if (data.ok) {
        state.chatMessages = data.messages || [];
        renderUserMessages();
        dom.chatInput.value = "";
        return;
      }
    } catch (_) {}
  }

  state.chatMessages.push({ author: "user", text, time: nowTime() });
  state.chatMessages.push({ author: "support", text: smartSupportReply(text), time: nowTime() });
  dom.chatInput.value = "";
  renderUserMessages();
}

async function bootAdmin() {
  if (!api.initData) {
    renderAdminDemo();
    return;
  }
  try {
    const data = await api.get("/api/admin/bootstrap");
    if (!data.ok) throw new Error("unauthorized");
    state.adminConnected = true;
    dom.adminConnectionBadge.textContent = "live";
    renderAdminSummary(data.summary || {});
    state.adminTickets = data.tickets || [];
    renderAdminTickets();
    if (!state.adminSelectedTicketId && state.adminTickets[0]) {
      await openAdminTicket(state.adminTickets[0].id);
    }
  } catch (_) {
    renderAdminDemo();
  }
}

function renderAdminDemo() {
  state.adminConnected = false;
  dom.adminConnectionBadge.textContent = "demo";
  renderAdminSummary(demoAdminData.summary);
  state.adminTickets = demoAdminData.tickets;
  renderAdminTickets();
  if (!state.adminSelectedTicketId && state.adminTickets[0]) {
    openAdminTicket(state.adminTickets[0].id, true);
  }
}

function renderAdminSummary(summary = {}) {
  const cards = [
    ["Пользователи", summary.users ?? 0, "violet"],
    ["Новые", summary.new ?? 0, "violet"],
    ["В работе", summary.in_progress ?? 0, "cyan"],
    ["Завершённые", summary.done ?? 0, "green"],
    ["Отклонённые", summary.rejected ?? 0, "red"],
    ["Выручка", formatRub(summary.revenue ?? 0), "dark"],
  ];
  dom.adminSummary.innerHTML = cards
    .map(([label, value, cls]) => `<div class="metric-card ${cls}"><span>${label}</span><strong>${value}</strong></div>`)
    .join("");
}

async function loadAdminTickets() {
  if (!state.adminConnected) {
    const items = demoAdminData.tickets.filter(matchesAdminFilters);
    state.adminTickets = items;
    renderAdminTickets();
    return;
  }
  try {
    const data = await api.get("/api/admin/tickets", { status: state.adminFilter, search: state.adminSearch });
    state.adminTickets = data.tickets || [];
    renderAdminTickets();
    if (state.adminSelectedTicketId) {
      await openAdminTicket(state.adminSelectedTicketId);
    }
  } catch (_) {
    renderAdminDemo();
  }
}

function matchesAdminFilters(ticket) {
  const q = state.adminSearch.toLowerCase();
  const passesStatus = state.adminFilter === "all" || ticket.status === state.adminFilter;
  const passesSearch = !q || String(ticket.id).includes(q) || String(ticket.user_id).includes(q) || (ticket.service || "").toLowerCase().includes(q);
  return passesStatus && passesSearch;
}

function renderAdminTickets() {
  const tickets = state.adminConnected ? state.adminTickets : state.adminTickets.filter(matchesAdminFilters);
  dom.ticketsCounter.textContent = `${tickets.length} тикетов`;
  dom.ticketList.innerHTML = "";
  if (!tickets.length) {
    dom.ticketList.innerHTML = `<div class="alert-box">Сейчас ничего не найдено. Попробуй другой фильтр или строку поиска.</div>`;
    return;
  }
  tickets.forEach((ticket) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = `ticket-item${state.adminSelectedTicketId === ticket.id ? " active" : ""}`;
    item.innerHTML = `
      <div class="ticket-title">
        <span>#${ticket.id} · ${escapeHtml(ticket.service)}</span>
        <span>${escapeHtml(ticket.status_label || ticket.status)}</span>
      </div>
      <div class="ticket-meta">user: ${ticket.user_id} · сумма: ${formatRub(ticket.amount || 0)} · файлов: ${ticket.media_count || 0}</div>
      <div class="ticket-preview">${escapeHtml(ticket.description || ticket.last_message_text || "Без комментария")}</div>
    `;
    item.addEventListener("click", () => openAdminTicket(ticket.id, !state.adminConnected));
    dom.ticketList.appendChild(item);
  });
}

async function openAdminTicket(ticketId, demo = false) {
  state.adminSelectedTicketId = ticketId;
  renderAdminTickets();

  if (demo || !state.adminConnected) {
    const ticket = demoAdminData.tickets.find((x) => x.id === ticketId);
    state.adminSelectedTicket = ticket;
    state.adminMessages = demoAdminData.messages[ticketId] || [];
    renderAdminDetail();
    return;
  }

  try {
    const data = await api.get(`/api/admin/tickets/${ticketId}`);
    state.adminSelectedTicket = data.ticket;
    state.adminMessages = data.messages || [];
    renderAdminDetail();
  } catch (_) {
    renderAdminDemo();
  }
}

function renderAdminDetail() {
  const t = state.adminSelectedTicket;
  if (!t) return;
  dom.detailTitle.textContent = `Тикет #${t.id}`;
  dom.detailPills.innerHTML = [
    pillMarkup(t.status_label || t.status, t.status === "done" ? "green" : t.status === "rejected" ? "red" : t.status === "in_progress" ? "cyan" : "violet"),
    pillMarkup(t.payment_status_label || t.payment_status, t.payment_status === "paid" ? "green" : "violet"),
    pillMarkup(`user ${t.user_id}`, "dark"),
  ].join("");
  dom.ticketMeta.innerHTML = `
    <div class="meta-grid">
      <div class="meta-box"><span>Сервис</span><strong>${escapeHtml(t.service)}</strong></div>
      <div class="meta-box"><span>Сумма заказа</span><strong>${formatRub(t.amount || 0)}</strong></div>
      <div class="meta-box"><span>Комиссия</span><strong>${formatRub(t.commission || 0)}</strong></div>
      <div class="meta-box"><span>Ответственный</span><strong>${escapeHtml(t.assigned_admin_name || "не назначен")}</strong></div>
      <div class="meta-box"><span>Создано</span><strong>${escapeHtml(t.created_at_label || "—")}</strong></div>
      <div class="meta-box"><span>Обновлено</span><strong>${escapeHtml(t.updated_at_label || "—")}</strong></div>
    </div>
    <div class="alert-box">${escapeHtml(t.description || "Комментарий не указан")}</div>
  `;
  renderDetailActions();
  renderAdminMessages();
}

function renderDetailActions() {
  const t = state.adminSelectedTicket;
  if (!t) return;
  dom.detailActions.innerHTML = "";

  const assignBtn = buttonEl("Назначить на меня", "secondary-btn", async () => {
    if (!state.adminConnected) {
      notify("Демо", "В живом режиме эта кнопка назначает тикет на текущего администратора.");
      return;
    }
    const data = await api.post(`/api/admin/tickets/${t.id}/assign`, {});
    state.adminSelectedTicket = data.ticket;
    await loadAdminTickets();
    renderAdminDetail();
  });

  const select = document.createElement("select");
  [
    ["new", "new"],
    ["in_progress", "in_progress"],
    ["done", "done"],
    ["rejected", "rejected"],
  ].forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    option.selected = t.status === value;
    select.appendChild(option);
  });
  select.addEventListener("change", async () => {
    if (!state.adminConnected) {
      notify("Демо", `В живом режиме статус сменится на ${select.value}.`);
      return;
    }
    const data = await api.post(`/api/admin/tickets/${t.id}/status`, { status: select.value });
    state.adminSelectedTicket = data.ticket;
    await loadAdminTickets();
    renderAdminDetail();
  });

  [
    ["Запросить скриншоты", "Пришлите, пожалуйста, дополнительные скриншоты заказа и переписки с поддержкой."],
    ["Сообщить: в работе", "Ваша заявка уже в работе. Обновлю статус, как только появятся новые детали."],
    ["Возврат готов", "Возврат подготовлен. Проверьте зачисление в течение 1–3 рабочих дней."],
  ].forEach(([label, text]) => {
    dom.detailActions.appendChild(buttonEl(label, "secondary-btn", () => {
      dom.adminReplyInput.value = text;
      dom.adminReplyInput.focus();
    }));
  });

  dom.detailActions.appendChild(assignBtn);
  dom.detailActions.appendChild(select);
}

function renderAdminMessages() {
  dom.adminMessages.innerHTML = "";
  if (!state.adminMessages.length) {
    dom.adminMessages.innerHTML = `<div class="alert-box">Сообщений по тикету пока нет. Можно сразу отправить первое сообщение пользователю.</div>`;
    return;
  }
  state.adminMessages.forEach((msg) => {
    const cls = msg.sender_role === "admin" ? "user" : msg.sender_role === "system" ? "system" : "support";
    const name = msg.sender_role === "admin" ? (msg.sender_name || "Админ") : msg.sender_role === "user" ? (msg.sender_name || "Клиент") : "Система";
    const item = document.createElement("div");
    item.className = `message ${cls}`;
    item.innerHTML = `
      <div class="message-head"><span>${escapeHtml(name)}</span><span>${escapeHtml(msg.created_at ? formatTime(msg.created_at * 1000) : "сейчас")}</span></div>
      <div>${escapeHtml(msg.text || "")}</div>
    `;
    dom.adminMessages.appendChild(item);
  });
  dom.adminMessages.scrollTop = dom.adminMessages.scrollHeight;
}

async function sendAdminReply() {
  const text = dom.adminReplyInput.value.trim();
  const ticket = state.adminSelectedTicket;
  if (!text || !ticket) return;

  if (!state.adminConnected) {
    state.adminMessages.push({ sender_role: "admin", sender_name: "Админ", text, created_at: Date.now() / 1000 });
    dom.adminReplyInput.value = "";
    renderAdminMessages();
    return;
  }

  try {
    const data = await api.post(`/api/admin/tickets/${ticket.id}/reply`, { text });
    state.adminMessages = data.messages || [];
    state.adminSelectedTicket = data.ticket || state.adminSelectedTicket;
    dom.adminReplyInput.value = "";
    await loadAdminTickets();
    renderAdminDetail();
  } catch (e) {
    notify("Ошибка", "Не удалось отправить сообщение пользователю.");
  }
}

function buildSmartDemoMessages() {
  return [
    { author: "support", text: "Здравствуйте! Это обновлённый чат поддержки внутри Mini App. После создания кейса здесь можно вести переписку по заявке.", time: "сейчас" },
    { author: "system", text: "В live‑режиме сообщения здесь синхронизируются с тикетом и Web Admin панелью.", time: "сейчас" },
  ];
}

function smartSupportReply(text) {
  const normalized = text.toLowerCase();
  if (normalized.includes("скрин") || normalized.includes("доказ")) {
    return "Подойдут скриншоты заказа, переписки с поддержкой сервиса, состава заказа и подтверждение оплаты. Их можно дослать в чат бота сразу после отправки формы.";
  }
  if (normalized.includes("статус") || normalized.includes("когда")) {
    return "В обновлённой версии статус заявки дублируется и в боте, и в Web Admin. Оператор увидит твоё сообщение сразу после отправки.";
  }
  return "Сообщение принято. В живом режиме оно попадёт в карточку тикета и Web Admin панель администратора.";
}

function buildDemoAdminData() {
  const tickets = [
    {
      id: 1042,
      user_id: 553311221,
      service: "🍔 Яндекс Еда",
      amount: 1890,
      commission: 472.5,
      description: "Привезли не тот заказ, поддержка отказала в компенсации.",
      status: "new",
      status_label: "Новая",
      payment_status: "none",
      payment_status_label: "Не запрошена",
      assigned_admin_name: null,
      media_count: 3,
      created_at_label: "10.04 11:42",
      updated_at_label: "10.04 11:49",
      last_message_text: "Жду ответа по заявке",
    },
    {
      id: 1041,
      user_id: 553311220,
      service: "🛵 Самокат",
      amount: 1120,
      commission: 280,
      description: "Часть заказа не привезли, есть фото пакета.",
      status: "in_progress",
      status_label: "В работе",
      payment_status: "pending",
      payment_status_label: "Ожидает оплату",
      assigned_admin_name: "Главный админ",
      media_count: 5,
      created_at_label: "10.04 10:10",
      updated_at_label: "10.04 11:25",
      last_message_text: "Пришлите, пожалуйста, ещё скрин оплаты.",
    },
    {
      id: 1038,
      user_id: 553311218,
      service: "🚗 Купер",
      amount: 2390,
      commission: 597.5,
      description: "Курьер отменил заказ после списания средств.",
      status: "done",
      status_label: "Завершена",
      payment_status: "paid",
      payment_status_label: "Оплачена",
      assigned_admin_name: "Главный админ",
      media_count: 2,
      created_at_label: "09.04 18:02",
      updated_at_label: "10.04 09:10",
      last_message_text: "Возврат подготовлен.",
    },
  ];

  return {
    summary: { users: 214, new: 8, in_progress: 14, done: 67, rejected: 6, revenue: 18450 },
    tickets,
    messages: {
      1042: [
        { sender_role: "system", sender_name: "System", text: "Тикет создан через Mini App Noir.", created_at: Date.now() / 1000 - 3600 },
        { sender_role: "user", sender_name: "Клиент", text: "Привезли не тот заказ, поддержка отказала в компенсации.", created_at: Date.now() / 1000 - 3300 },
      ],
      1041: [
        { sender_role: "user", sender_name: "Клиент", text: "Часть заказа не привезли, отправил фото пакета.", created_at: Date.now() / 1000 - 5000 },
        { sender_role: "admin", sender_name: "Главный админ", text: "Пришлите, пожалуйста, ещё скрин оплаты.", created_at: Date.now() / 1000 - 4300 },
      ],
      1038: [
        { sender_role: "admin", sender_name: "Главный админ", text: "Возврат подготовлен. Проверьте зачисление в течение 1–3 дней.", created_at: Date.now() / 1000 - 7600 },
      ],
    },
  };
}

function applyTelegramTheme() {
  if (!tg?.themeParams) return;
  document.documentElement.style.setProperty("--tg-bg", tg.themeParams.bg_color || "");
}

function getAmountNumber() {
  const normalized = String(state.amount || "")
    .replace(/\s+/g, "")
    .replace(/,/g, ".")
    .replace(/[^\d.]/g, "");
  const amount = Number(normalized);
  return Number.isFinite(amount) ? amount : 0;
}

function isValid() {
  const amount = getAmountNumber();
  return Boolean(state.service) && amount >= 100 && amount <= 100000 && dom.agreementCheckbox.checked;
}

function handleResponse(res) {
  return res.json();
}

function byId(id) {
  return document.getElementById(id);
}

function formatRub(value) {
  return `${new Intl.NumberFormat("ru-RU").format(Math.round(Number(value) || 0))} ₽`;
}

function formatTime(ts) {
  return new Date(ts).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

function nowTime() {
  return formatTime(Date.now());
}

function pillMarkup(text, color) {
  return `<span class="pill ${color || ""}">${escapeHtml(text)}</span>`;
}

function buttonEl(label, className, onClick) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = className;
  btn.textContent = label;
  btn.addEventListener("click", onClick);
  return btn;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function notify(title, message) {
  if (tg?.showPopup) {
    tg.showPopup({ title, message, buttons: [{ type: "ok" }] });
  } else {
    alert(`${title}\n\n${message}`);
  }
}

function debounce(fn, wait) {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn(...args), wait);
  };
}

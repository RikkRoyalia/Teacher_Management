const state = {
  user: null,
  csrfToken: "",
  currentView: "overview",
  teachers: [],
  departments: [],
  users: [],
  selectedTeacherId: "",
  detailEdit: null,
  contractWarningDays: 30,
  table: { rows: [], size: 10, page: 1 },
  notifications: [],
  notifTimer: null,
  detailTab: "info",
  teacherQuery: "",
};

const viewTitles = {
  overview: "Tổng quan",
  teachers: "Hồ sơ giảng viên",
  teacherDetail: "Chi tiết hồ sơ giảng viên",
  departments: "Khoa & bộ môn",
  changes: "Yêu cầu thay đổi",
  reports: "Báo cáo nhân sự",
  accounts: "Quản trị hệ thống",
  audit: "Nhật ký hoạt động",
};

const roleLabels = {
  admin: "Quản trị viên",
  hr: "Nhân viên nhân sự",
  manager: "Người quản lý",
};
const statusLabels = {
  active: "Đang công tác",
  paused: "Tạm ngừng",
  ended: "Đã kết thúc",
  pending: "Chờ duyệt",
  needs_info: "Cần bổ sung",
  approved: "Đã duyệt",
  rejected: "Từ chối",
  expiring: "Sắp hết hạn",
  expired: "Đã hết hạn",
  terminated: "Đã chấm dứt",
};
const checklistClassifications = {
  required: "Bắt buộc theo danh mục",
  conditional: "Có điều kiện",
  optional: "Tùy chọn",
};
const checklistRequirementStatuses = {
  review: "Chưa rà soát",
  required: "Bắt buộc với giảng viên này",
  optional: "Tùy chọn",
  not_applicable: "Không áp dụng",
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function makeElement(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined && text !== null) element.textContent = String(text);
  return element;
}

function addPasswordToggle(input) {
  const field = input.closest(".form-field");
  if (!field || input.dataset.passwordToggle) return;

  input.dataset.passwordToggle = "true";
  input.id ||= `password-field-${crypto.randomUUID()}`;
  const container = makeElement("div", "form-field password-field");
  const label = makeElement(
    "label",
    "form-field-label",
    field.querySelector(":scope > span").textContent,
  );
  label.htmlFor = input.id;
  const control = makeElement("div", "password-input-wrap");
  const toggle = makeElement("button", "password-toggle", "Hiện");
  toggle.type = "button";
  toggle.setAttribute("aria-label", "Hiện mật khẩu");
  toggle.setAttribute("aria-pressed", "false");
  toggle.addEventListener("click", () => {
    const showPassword = input.type === "password";
    input.type = showPassword ? "text" : "password";
    toggle.textContent = showPassword ? "Ẩn" : "Hiện";
    toggle.setAttribute(
      "aria-label",
      `${showPassword ? "Ẩn" : "Hiện"} mật khẩu`,
    );
    toggle.setAttribute("aria-pressed", String(showPassword));
  });
  field.replaceWith(container);
  control.append(input, toggle);
  container.append(label, control);
}

function resetPasswordToggles(form) {
  $$('[data-password-toggle="true"]', form).forEach((input) => {
    if (input.type === "text") input.type = "password";
    const toggle = input
      .closest(".password-input-wrap")
      .querySelector("button");
    toggle.textContent = "Hiện";
    toggle.setAttribute("aria-label", "Hiện mật khẩu");
    toggle.setAttribute("aria-pressed", "false");
  });
}

function initials(name = "") {
  return name
    .trim()
    .split(/\s+/)
    .slice(-2)
    .map((part) => Array.from(part)[0] || "")
    .join("")
    .toLocaleUpperCase("vi");
}

function showToast(message, isError = false) {
  const toast = makeElement(
    "div",
    `toast${isError ? " toast-error" : ""}`,
    message,
  );
  $("#toast-region").append(toast);
  window.setTimeout(() => toast.remove(), 4500);
}

function showError(target, message) {
  target.textContent = message;
  target.classList.remove("hidden");
}

function clearError(target) {
  target.textContent = "";
  target.classList.add("hidden");
}

function showLogin() {
  state.user = null;
  stopNotifications();
  $("#theme-fab").classList.add("hidden");
  state.csrfToken = "";
  $("#app-shell").classList.add("hidden");
  $("#login-screen").classList.remove("hidden");
}

function showApp(user) {
  state.user = user;
  state.csrfToken = user.csrf_token;
  $("#login-screen").classList.add("hidden");
  $("#app-shell").classList.remove("hidden");
  $("#profile-name").textContent = user.full_name;
  $("#profile-role").textContent = roleLabels[user.role] || user.role;
  $("#profile-initials").textContent = initials(user.full_name);
  $$("[data-roles]").forEach((link) => {
    const roles = (link.dataset.roles || "").split(",").filter(Boolean);
    link.classList.toggle(
      "hidden",
      roles.length > 0 && !roles.includes(user.role),
    );
  });
  $("#theme-fab").classList.remove("hidden");
  startNotifications();
  navigate("overview");
}

async function api(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers || {});
  if (options.body instanceof FormData) {
    headers.delete("Content-Type");
  } else if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!["GET", "HEAD", "OPTIONS"].includes(method) && state.csrfToken) {
    headers.set("X-CSRF-Token", state.csrfToken);
  }
  const response = await fetch(path, {
    ...options,
    method,
    headers,
    credentials: "same-origin",
  });
  if (response.status === 401 && state.user) showLogin();
  if (!response.ok) {
    let message = `Yêu cầu không thành công (${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail))
        message = body.detail.map((item) => item.msg).join(" ");
    } catch {
      message = `Yêu cầu không thành công (${response.status}).`;
    }
    throw new Error(message);
  }
  if (response.status === 204) return null;
  if (response.headers.get("content-type")?.includes("application/json"))
    return response.json();
  return response;
}

async function refreshData() {
  if (state.user.role === "admin") {
    state.departments = [];
    state.teachers = [];
    return;
  }
  const [departments, teachers] = await Promise.all([
    api("/departments?include_inactive=true").catch(() => []),
    state.user.role === "hr"
      ? api("/teachers").catch(() => [])
      : Promise.resolve([]),
  ]);
  state.departments = departments;
  state.teachers = teachers;
}

function navigate(view) {
  if (!viewTitles[view]) return;
  state.currentView = view;
  $$(".view-section").forEach((section) => section.classList.add("hidden"));
  $("#breadcrumb-current").textContent = viewTitles[view];
  $("#sidebar").classList.remove("open");
  const activeView = view === "teacherDetail" ? "teachers" : view;
  $$(".nav-link").forEach((link) =>
    link.classList.toggle("active", link.dataset.view === activeView),
  );
  window.scrollTo({ top: 0 });
  if (view === "overview") {
    $("#view-overview").classList.remove("hidden");
    renderOverview();
    return;
  }
  if (view === "teacherDetail") {
    $("#view-detail").classList.remove("hidden");
    renderWorkspace().catch((error) => showToast(error.message, true));
    return;
  }
  $("#view-workspace").classList.remove("hidden");
  $("#workspace-title").textContent = viewTitles[view];
  $("#workspace-description").textContent = workspaceDescription(view);
  renderWorkspace().catch((error) => showToast(error.message, true));
}

function workspaceDescription(view) {
  const descriptions = {
    teachers: "Tìm kiếm, lọc và quản lý hồ sơ giảng viên.",
    departments:
      "Quản lý cây đơn vị; đơn vị đã tham chiếu được lưu trữ thay vì xóa.",
    changes: "Thay đổi quan trọng chỉ cập nhật hồ sơ chính thức sau khi duyệt.",
    reports:
      "Thống kê theo đơn vị, trình độ, chức danh và trạng thái; vai trò quản lý chỉ xem tổng hợp.",
    accounts:
      "Quản lý tài khoản và vai trò; tài khoản bị khóa được giữ lại để bảo toàn lịch sử và nhật ký.",
    audit: "Nhật ký chỉ đọc, ghi nhận các thao tác quan trọng.",
  };
  return descriptions[view] || "";
}

const SVG_NS = "http://www.w3.org/2000/svg";
const badgeTone = {
  active: "ok",
  approved: "ok",
  paused: "warn",
  pending: "warn",
  needs_info: "warn",
  expiring: "warn",
  ended: "muted",
  terminated: "muted",
  expired: "bad",
  rejected: "bad",
};

function svgEl(tag, attributes = {}) {
  const element = document.createElementNS(SVG_NS, tag);
  Object.entries(attributes).forEach(([name, value]) =>
    element.setAttribute(name, String(value)),
  );
  return element;
}

function iconEl(name) {
  const svg = svgEl("svg", { class: "ico", "aria-hidden": "true" });
  svg.append(svgEl("use", { href: `#i-${name}` }));
  return svg;
}

function badge(value, label) {
  return makeElement(
    "span",
    `badge ${badgeTone[value] || ""}`.trim(),
    label || statusLabels[value] || value,
  );
}

function headerButton(label, action, icon, primary = true) {
  const button = makeElement(
    "button",
    `button ${primary ? "button-primary" : "button-secondary"}`,
  );
  button.type = "button";
  button.dataset.action = action;
  button.append(iconEl(icon), document.createTextNode(label));
  return button;
}

function departmentName(id) {
  return state.departments.find((unit) => unit.id === id)?.name || "—";
}

function buildTable(headers, rows, emptyText = "Không có dữ liệu.") {
  const wrap = makeElement("div", "table-wrap");
  const table = document.createElement("table");
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  headers.forEach((header) => headRow.append(makeElement("th", "", header)));
  head.append(headRow);
  const body = document.createElement("tbody");
  for (const values of rows) {
    const row = document.createElement("tr");
    values.forEach((value) => {
      const cell = document.createElement("td");
      if (value instanceof Node) cell.append(value);
      else
        cell.textContent =
          value === null || value === undefined || value === ""
            ? "—"
            : String(value);
      row.append(cell);
    });
    body.append(row);
  }
  table.append(head, body);
  wrap.append(table);
  if (!rows.length) wrap.append(makeElement("div", "empty-state", emptyText));
  return wrap;
}

function chartCard(title) {
  const card = makeElement("article", "chart-card");
  card.append(makeElement("h3", "", title));
  return card;
}

function barChart(title, counts, labelOf = (key) => key) {
  const card = chartCard(title);
  const entries = Object.entries(counts || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);
  if (!entries.length) {
    card.append(makeElement("p", "chart-empty", "Chưa có dữ liệu."));
    return card;
  }
  const max = Math.max(...entries.map(([, count]) => count), 1);
  for (const [key, count] of entries) {
    const row = makeElement("div", "bar-row");
    const name = makeElement("span", "bar-name", labelOf(key));
    name.title = labelOf(key);
    const svg = svgEl("svg", {
      class: "bar-svg",
      viewBox: "0 0 100 12",
      preserveAspectRatio: "none",
      "aria-hidden": "true",
    });
    svg.append(
      svgEl("rect", {
        class: "bar-track",
        x: 0,
        y: 0,
        width: 100,
        height: 12,
        rx: 3,
      }),
      svgEl("rect", {
        class: "bar-fill",
        x: 0,
        y: 0,
        width: Math.max(2, (count / max) * 100),
        height: 12,
        rx: 3,
      }),
    );
    row.append(name, svg, makeElement("b", "bar-count", count));
    card.append(row);
  }
  return card;
}

function donutChart(title, counts, labelOf = (key) => key) {
  const card = chartCard(title);
  const entries = Object.entries(counts || {})
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);
  const total = entries.reduce((sum, [, count]) => sum + count, 0);
  if (!total) {
    card.append(makeElement("p", "chart-empty", "Chưa có dữ liệu."));
    return card;
  }
  const wrap = makeElement("div", "donut-wrap");
  const svg = svgEl("svg", {
    class: "donut",
    viewBox: "0 0 42 42",
    role: "img",
    "aria-label": title,
  });
  svg.append(
    svgEl("circle", { class: "donut-ring", cx: 21, cy: 21, r: 15.915 }),
  );
  let offset = 25;
  const legend = makeElement("ul", "legend");
  entries.forEach(([key, count], index) => {
    const percent = (count / total) * 100;
    svg.append(
      svgEl("circle", {
        class: `donut-seg seg${index}`,
        cx: 21,
        cy: 21,
        r: 15.915,
        "stroke-dasharray": `${percent} ${100 - percent}`,
        "stroke-dashoffset": offset,
      }),
    );
    offset -= percent;
    const item = makeElement("li");
    item.append(
      makeElement("i", `dot${index}`),
      makeElement("span", "", labelOf(key)),
      makeElement("b", "", count),
    );
    legend.append(item);
  });
  const centre = svgEl("text", { class: "donut-total", x: 21, y: 22.5 });
  centre.textContent = String(total);
  const caption = svgEl("text", { class: "donut-cap", x: 21, y: 27 });
  caption.textContent = "tổng";
  svg.append(centre, caption);
  wrap.append(svg, legend);
  card.append(wrap);
  return card;
}

function buildTimeline(history) {
  const list = makeElement("ol", "timeline");
  if (!history.length)
    return makeElement("p", "empty-state", "Chưa có quá trình công tác.");
  [...history]
    .sort((a, b) => String(b.starts_on).localeCompare(String(a.starts_on)))
    .forEach((item) => {
      const entry = makeElement("li", item.ends_on ? "" : "current");
      entry.append(
        makeElement(
          "time",
          "",
          `${item.starts_on} – ${item.ends_on || "Hiện tại"}`,
        ),
        makeElement(
          "strong",
          "",
          [departmentName(item.department_id), item.position_title]
            .filter((part) => part && part !== "—")
            .join(" · "),
        ),
      );
      if (item.reason) entry.append(makeElement("span", "", item.reason));
      list.append(entry);
    });
  return list;
}

function statCard(label, value, icon, view) {
  const card = makeElement(view ? "button" : "article", "stat-card");
  if (view) {
    card.type = "button";
    card.dataset.action = "goto";
    card.dataset.view = view;
  }
  const iconBox = makeElement("span", "stat-icon");
  iconBox.append(iconEl(icon));
  const text = makeElement("span", "stat-text");
  text.append(
    makeElement("span", "stat-value", value),
    makeElement("span", "stat-label", label),
  );
  card.append(iconBox, text);
  return card;
}

async function downloadResponse(path, filename) {
  const response = await api(path);
  const link = document.createElement("a");
  link.href = URL.createObjectURL(await response.blob());
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

async function renderOverview() {
  const cards = $("#summary-cards");
  const charts = $("#overview-charts");
  const extra = $("#overview-extra");
  [cards, charts, extra].forEach((region) => region.replaceChildren());
  const isAdmin = state.user.role === "admin";
  const isHr = state.user.role === "hr";
  $("#contract-panel").classList.toggle("hidden", isAdmin);
  $("#certificate-panel").classList.toggle("hidden", !isHr);
  $("#profile-review-panel").classList.toggle("hidden", !isHr);
  try {
    if (isAdmin) {
      const [users, logs] = await Promise.all([
        api("/users"),
        api("/audit-logs?limit=8"),
      ]);
      const active = users.filter((user) => user.is_active);
      cards.append(
        statCard("Tổng tài khoản", users.length, "users", "accounts"),
        statCard("Đang hoạt động", active.length, "check", "accounts"),
        statCard("Đã khóa", users.length - active.length, "lock", "accounts"),
        statCard(
          "Quản trị viên",
          active.filter((user) => user.role === "admin").length,
          "user",
          "accounts",
        ),
      );
      const panel = makeElement("section", "panel");
      const heading = makeElement("div", "panel-heading");
      heading.append(
        makeElement("h2", "", "Hoạt động gần đây"),
        makeElement(
          "p",
          "",
          "Các thao tác mới nhất được ghi nhận trong hệ thống.",
        ),
      );
      panel.append(
        heading,
        buildTable(
          ["Thời gian", "Thao tác", "Đối tượng", "Kết quả"],
          logs.map((item) => [
            new Date(item.created_at).toLocaleString("vi-VN"),
            item.action,
            item.entity_type,
            item.outcome,
          ]),
          "Chưa có hoạt động nào.",
        ),
      );
      extra.append(panel);
      return;
    }
    const [summary, profileReview] = await Promise.all([
      api("/reports/summary"),
      isHr ? api("/profile-reviews") : Promise.resolve(null),
    ]);
    const target = (hrView) => (isHr ? hrView : "reports");
    cards.append(
      statCard(
        "Tổng giảng viên",
        summary.total_teachers,
        "users",
        target("teachers"),
      ),
      statCard(
        "Hồ sơ chưa đầy đủ",
        summary.incomplete_profiles,
        "warn",
        target("teachers"),
      ),
      statCard(
        "Hợp đồng sắp/đã hết hạn",
        summary.expiring_or_expired_contracts,
        "clock",
        target("teachers"),
      ),
      statCard(
        "Yêu cầu chờ duyệt",
        summary.change_requests_by_status?.pending || 0,
        "chat",
        "changes",
      ),
    );
    charts.append(
      barChart("Giảng viên theo đơn vị", summary.teachers_by_department),
      donutChart("Cơ cấu trình độ", summary.teachers_by_degree),
      donutChart(
        "Trạng thái công tác",
        summary.teachers_by_status,
        (key) => statusLabels[key] || key,
      ),
    );
    const alertBody = $("#contract-alert-rows");
    alertBody.replaceChildren();
    if (isHr) {
      const alerts = await api("/contracts/alerts");
      for (const alert of alerts) {
        const row = document.createElement("tr");
        [
          alert.contract_code,
          alert.teacher_name,
          alert.ends_on,
          alert.days_remaining,
          badge(alert.status),
        ].forEach((value) => {
          const cell = document.createElement("td");
          if (value instanceof Node) cell.append(value);
          else cell.textContent = String(value);
          row.append(cell);
        });
        alertBody.append(row);
      }
    }
    const empty = $("#contract-empty");
    empty.classList.toggle("hidden", alertBody.children.length > 0);
    empty.textContent = isHr
      ? "Hiện chưa có hợp đồng nào cần chú ý."
      : "Vai trò Người quản lý chỉ xem số liệu tổng hợp; chi tiết hợp đồng do bộ phận nhân sự quản lý.";
    if (isHr) {
      $("#certificate-warning-days").value = String(
        (await api("/settings/certificate-warning-days")).days,
      );
      const certificateAlerts = profileReview.items.flatMap((item) =>
        item.expiring_certificates.map((certificate) => [
          item.employee_code,
          item.teacher_name,
          certificate.title,
          certificate.expires_on,
          certificate.days_remaining,
          badge(certificate.status),
        ]),
      );
      $("#certificate-alert-table").replaceChildren(
        buildTable(
          [
            "Mã giảng viên",
            "Giảng viên",
            "Chứng chỉ",
            "Ngày hết hạn",
            "Ngày còn lại",
            "Trạng thái",
          ],
          certificateAlerts,
          "Hiện chưa có chứng chỉ nào cần chú ý.",
        ),
      );
      const modelStatus = profileReview.model;
      $("#profile-review-model-status").textContent =
        `${modelStatus.message} (Đã đánh giá ${modelStatus.profile_count} hồ sơ.)`;
      const reviewRows = profileReview.items.map((item) => [
        item.employee_code,
        item.teacher_name,
        item.missing.length,
        item.needs_review.length,
        item.invalid_data.length,
        item.expiring_certificates.length,
        item.suggestions.length,
        item.anomaly
          ? badge("expiring", "ML: cần HR xem lại")
          : "—",
        actionButton("Mở hồ sơ", "teacher-detail", item.teacher_id),
      ]);
      $("#profile-review-table").replaceChildren(
        buildTable(
          [
            "Mã giảng viên",
            "Giảng viên",
            "Thiếu bắt buộc",
            "Chờ rà soát điều kiện",
            "Dữ liệu cần kiểm tra",
            "Chứng chỉ sắp/đã hết hạn",
            "Gợi ý tùy chọn",
            "Cờ bất thường",
            "",
          ],
          reviewRows,
          "Không có hồ sơ cần chú ý theo checklist và dữ liệu hiện có.",
        ),
      );
    }
  } catch (error) {
    showToast(`Không thể tải tổng quan: ${error.message}`, true);
  }
}

function setTable(headers, rows, options = {}) {
  const head = $("#workspace-head");
  head.replaceChildren();
  const headingRow = document.createElement("tr");
  headers.forEach((header) => headingRow.append(makeElement("th", "", header)));
  head.append(headingRow);
  state.table = { rows, size: options.pageSize || 10, page: 1 };
  drawTablePage();
}

function drawTablePage() {
  const { rows, size } = state.table;
  const pages = Math.max(1, Math.ceil(rows.length / size));
  state.table.page = Math.min(Math.max(1, state.table.page), pages);
  const body = $("#workspace-rows");
  body.replaceChildren();
  const first = (state.table.page - 1) * size;
  for (const values of rows.slice(first, first + size)) {
    const row = document.createElement("tr");
    values.forEach((value) => {
      const cell = document.createElement("td");
      if (value instanceof Node) cell.append(value);
      else
        cell.textContent =
          value === null || value === undefined ? "—" : String(value);
      row.append(cell);
    });
    body.append(row);
  }
  $("#workspace-empty").classList.toggle("hidden", rows.length > 0);
  const pager = $("#workspace-pager");
  pager.replaceChildren();
  pager.classList.toggle("hidden", pages <= 1);
  if (pages > 1) {
    const previous = actionButton("‹ Trước", "page-prev");
    previous.disabled = state.table.page === 1;
    const next = actionButton("Sau ›", "page-next");
    next.disabled = state.table.page === pages;
    pager.append(
      previous,
      makeElement(
        "span",
        "",
        `Trang ${state.table.page}/${pages} · ${rows.length} bản ghi`,
      ),
      next,
    );
  }
}

function actionButton(label, action, id, className = "") {
  const button = makeElement("button", `row-action ${className}`.trim(), label);
  button.type = "button";
  button.dataset.action = action;
  if (id !== undefined) button.dataset.id = String(id);
  return button;
}

function actionGroup(buttons) {
  const group = document.createElement("div");
  group.className = "workspace-actions";
  group.append(...buttons);
  return group;
}

function clearWorkspace() {
  $("#workspace-filters").replaceChildren();
  $("#workspace-form-region").replaceChildren();
  $("#workspace-actions").replaceChildren();
}

async function renderWorkspace() {
  clearWorkspace();
  await refreshData();
  const renderers = {
    teachers: renderTeachers,
    teacherDetail: renderTeacherDetail,
    departments: renderDepartments,
    changes: renderChanges,
    reports: renderReports,
    accounts: renderAccounts,
    audit: renderAudit,
  };
  await renderers[state.currentView]?.();
}

async function renderTeachers() {
  $("#workspace-actions").append(
    headerButton("Thêm giảng viên", "add-teacher", "plus"),
    headerButton("Nhập Excel", "import-teachers", "up", false),
    headerButton("Xuất Excel", "export-teachers", "down", false),
  );
  const filter = makeElement("input", "workspace-search");
  filter.type = "search";
  filter.placeholder = "Tìm theo tên hoặc mã";
  const departmentFilter = document.createElement("select");
  departmentFilter.append(new Option("Tất cả đơn vị", ""));
  state.departments.forEach((unit) =>
    departmentFilter.add(new Option(unit.name, String(unit.id))),
  );
  const degreeFilter = document.createElement("select");
  degreeFilter.append(new Option("Tất cả trình độ", ""));
  [
    ...new Set(
      state.teachers.map((teacher) => teacher.academic_degree).filter(Boolean),
    ),
  ]
    .sort((left, right) => left.localeCompare(right, "vi"))
    .forEach((degree) => degreeFilter.add(new Option(degree, degree)));
  const statusFilter = document.createElement("select");
  statusFilter.append(new Option("Tất cả trạng thái", ""));
  [
    ["active", "Đang công tác"],
    ["paused", "Tạm ngừng"],
    ["ended", "Đã kết thúc"],
  ].forEach(([value, label]) => statusFilter.add(new Option(label, value)));
  $("#workspace-filters").append(
    filter,
    departmentFilter,
    degreeFilter,
    statusFilter,
  );
  const drawRows = () => {
    const query = filter.value.trim().toLocaleLowerCase("vi");
    const filtered = state.teachers.filter(
      (teacher) =>
        `${teacher.employee_code} ${teacher.full_name}`
          .toLocaleLowerCase("vi")
          .includes(query) &&
        (!departmentFilter.value ||
          teacher.department_id === Number(departmentFilter.value)) &&
        (!degreeFilter.value ||
          teacher.academic_degree === degreeFilter.value) &&
        (!statusFilter.value ||
          teacher.employment_status === statusFilter.value),
    );
    const params = new URLSearchParams();
    if (filter.value.trim()) params.set("q", filter.value.trim());
    if (departmentFilter.value)
      params.set("department_id", departmentFilter.value);
    if (degreeFilter.value) params.set("academic_degree", degreeFilter.value);
    if (statusFilter.value) params.set("employment_status", statusFilter.value);
    state.teacherQuery = params.toString();
    setTable(
      ["Mã", "Họ tên", "Đơn vị", "Trình độ", "Trạng thái", "Thao tác"],
      filtered.map((teacher) => [
        teacher.employee_code,
        teacher.full_name,
        departmentName(teacher.department_id),
        teacher.academic_degree || "—",
        badge(teacher.employment_status),
        actionGroup([
          actionButton("Xem hồ sơ", "teacher-open", teacher.id, "primary"),
          actionButton("Sửa", "edit-teacher", teacher.id),
          actionButton("Xóa", "delete-teacher", teacher.id, "danger"),
        ]),
      ]),
    );
  };
  [filter, departmentFilter, degreeFilter, statusFilter].forEach((control) =>
    control.addEventListener("input", drawRows),
  );
  [departmentFilter, degreeFilter, statusFilter].forEach((control) =>
    control.addEventListener("change", drawRows),
  );
  drawRows();
}

async function renderDepartments() {
  if (state.user.role === "hr") {
    $("#workspace-actions").append(
      headerButton("Thêm đơn vị", "add-department", "plus"),
    );
  }
  const rows = state.departments.map((department) => {
    const parent = state.departments.find(
      (item) => item.id === department.parent_id,
    );
    const actions = makeElement("div", "workspace-actions");
    if (state.user.role === "hr") {
      actions.append(actionButton("Sửa", "edit-department", department.id));
      if (department.is_active)
        actions.append(
          actionButton("Ngừng", "toggle-department", department.id),
        );
      else
        actions.append(
          actionButton("Kích hoạt", "toggle-department", department.id),
        );
      actions.append(
        actionButton("Xóa", "delete-department", department.id, "danger"),
      );
    }
    return [
      department.code,
      department.name,
      parent?.name || "—",
      department.description || "—",
      badge(
        department.is_active ? "active" : "ended",
        department.is_active ? "Đang hoạt động" : "Đã ngừng",
      ),
      actions,
    ];
  });
  setTable(["Mã", "Đơn vị", "Đơn vị cha", "Mô tả", "Trạng thái", ""], rows);
}

async function renderChanges() {
  const requests = await api("/change-requests");
  setTable(
    [
      "ID",
      "Giảng viên",
      "Loại",
      "Hiện tại",
      "Đề xuất",
      "Lý do",
      "Trạng thái",
      "Thao tác",
    ],
    requests.map((item) => {
      const actions = document.createElement("div");
      if (state.user.role === "manager" && item.status === "pending") {
        actions.append(actionButton("Duyệt", "decide-change", item.id));
        actions.append(actionButton("Từ chối", "reject-change", item.id));
        actions.append(
          actionButton("Yêu cầu bổ sung", "request-info", item.id),
        );
      }
      if (state.user.role === "hr" && item.status === "needs_info") {
        actions.append(actionButton("Bổ sung", "resubmit-change", item.id));
      }
      return [
        item.id,
        item.teacher_id,
        item.change_type,
        JSON.stringify(item.current_value),
        JSON.stringify(item.proposed_value),
        item.reason,
        badge(item.status),
        actions,
      ];
    }),
  );
  if (state.user.role === "hr") {
    const teacherSelect = document.createElement("select");
    teacherSelect.required = true;
    teacherSelect.append(new Option("Chọn giảng viên", ""));
    state.teachers.forEach((teacher) =>
      teacherSelect.add(
        new Option(
          `${teacher.employee_code} — ${teacher.full_name}`,
          String(teacher.id),
        ),
      ),
    );
    const type = inputField({
      name: "change_type",
      label: "Loại thay đổi",
      required: true,
    });
    const field = document.createElement("select");
    field.name = "field";
    field.required = true;
    field.append(
      new Option("Chọn nội dung", ""),
      new Option("Đơn vị công tác", "department_id"),
      new Option("Trình độ", "academic_degree"),
      new Option("Chức danh", "academic_title"),
      new Option("Trạng thái công tác", "employment_status"),
    );
    const proposed = inputField({
      name: "proposed",
      label: "Giá trị đề xuất",
      required: true,
    });
    const reason = inputField({
      name: "reason",
      label: "Lý do",
      required: true,
    });
    const effective = inputField({
      name: "effective_on",
      label: "Ngày có hiệu lực",
      type: "date",
    });
    const form = document.createElement("form");
    form.className = "inline-form";
    form.append(
      makeElement("strong", "", "Tạo yêu cầu thay đổi"),
      teacherSelect,
      type,
      field,
      proposed,
      reason,
      effective,
    );
    const submit = makeElement(
      "button",
      "button button-primary",
      "Gửi yêu cầu",
    );
    submit.type = "submit";
    form.append(submit);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const fieldName = field.value;
      const value = ["department_id"].includes(fieldName)
        ? Number(proposed.value)
        : proposed.value;
      const current = state.teachers.find(
        (teacher) => teacher.id === Number(teacherSelect.value),
      );
      try {
        await api(`/teachers/${teacherSelect.value}/change-requests`, {
          method: "POST",
          body: JSON.stringify({
            change_type: type.value,
            current_value: { [fieldName]: current?.[fieldName] ?? null },
            proposed_value: { [fieldName]: value },
            reason: reason.value,
            effective_on: effective.value || null,
          }),
        });
        showToast("Đã gửi yêu cầu.");
        await navigate(state.currentView);
      } catch (error) {
        showToast(error.message, true);
      }
    });
    $("#workspace-form-region").append(form);
  }
}

async function renderReports() {
  const departments = await api("/departments");
  const department = document.createElement("select");
  department.setAttribute("aria-label", "Đơn vị");
  department.append(new Option("Tất cả đơn vị", ""));
  departments.forEach((item) =>
    department.add(new Option(item.name, String(item.id))),
  );
  const start = inputField({
    name: "start_date",
    label: "Từ ngày",
    type: "date",
  });
  const end = inputField({ name: "end_date", label: "Đến ngày", type: "date" });
  const form = document.createElement("form");
  form.className = "inline-form";
  form.append(
    makeElement("strong", "", "Điều kiện lọc"),
    department,
    start,
    end,
  );
  const run = makeElement("button", "button button-primary", "Tạo báo cáo");
  run.type = "submit";
  const exportButton = makeElement(
    "button",
    "button button-secondary",
    "Xuất Excel",
  );
  exportButton.type = "button";
  form.append(run, exportButton);
  const startInput = start.querySelector("input");
  const endInput = end.querySelector("input");
  const query = () => {
    const params = new URLSearchParams();
    if (department.value) params.set("department_id", department.value);
    if (startInput.value) params.set("start_date", startInput.value);
    if (endInput.value) params.set("end_date", endInput.value);
    return params.toString();
  };
  const results = makeElement("div", "report-results");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const summary = await api(`/reports/summary?${query()}`);
      const requests = summary.change_requests_by_status || {};
      const cards = makeElement("div", "stats-grid");
      cards.append(
        statCard("Tổng giảng viên", summary.total_teachers, "users"),
        statCard("Hồ sơ chưa đầy đủ", summary.incomplete_profiles, "warn"),
        statCard(
          "Hợp đồng sắp/đã hết hạn",
          summary.expiring_or_expired_contracts,
          "clock",
        ),
        statCard("Yêu cầu chờ duyệt", requests.pending || 0, "chat"),
      );
      const charts = makeElement("div", "chart-grid");
      charts.append(
        barChart("Giảng viên theo đơn vị", summary.teachers_by_department),
        donutChart("Theo trình độ", summary.teachers_by_degree),
        barChart("Theo chức danh", summary.teachers_by_title),
        donutChart(
          "Theo trạng thái công tác",
          summary.teachers_by_status,
          (key) => statusLabels[key] || key,
        ),
        donutChart(
          "Yêu cầu thay đổi",
          requests,
          (key) => statusLabels[key] || key,
        ),
      );
      results.replaceChildren(cards, charts);
      const scope = [`Đơn vị: ${department.selectedOptions[0].textContent}`];
      if (startInput.value) scope.push(`từ ${startInput.value}`);
      if (endInput.value) scope.push(`đến ${endInput.value}`);
      scope.push("tính theo ngày tạo hồ sơ");
      const listOf = (counts, labelOf = (key) => key) =>
        Object.entries(counts || {}).map(([name, count]) => [
          labelOf(name),
          count,
        ]);
      setTable(
        ["Chỉ số", "Giá trị"],
        [
          ["Điều kiện lọc", scope.join(" · ")],
          ["Tổng giảng viên", summary.total_teachers],
          ["Hồ sơ chưa đầy đủ", summary.incomplete_profiles],
          ["Hợp đồng sắp/đã hết hạn", summary.expiring_or_expired_contracts],
          ...listOf(summary.teachers_by_department).map(([name, count]) => [
            `Đơn vị: ${name}`,
            count,
          ]),
          ...listOf(summary.teachers_by_degree).map(([name, count]) => [
            `Trình độ: ${name}`,
            count,
          ]),
          ...listOf(summary.teachers_by_title).map(([name, count]) => [
            `Chức danh: ${name}`,
            count,
          ]),
          ...listOf(
            summary.teachers_by_status,
            (key) => statusLabels[key] || key,
          ).map(([name, count]) => [`Trạng thái: ${name}`, count]),
          ...listOf(requests, (key) => statusLabels[key] || key).map(
            ([name, count]) => [`Yêu cầu: ${name}`, count],
          ),
        ],
        { pageSize: 15 },
      );
    } catch (error) {
      showToast(error.message, true);
    }
  });
  exportButton.addEventListener("click", async () => {
    try {
      await downloadResponse(
        `/reports/export.xlsx?${query()}`,
        "teacher_report.xlsx",
      );
    } catch (error) {
      showToast(error.message, true);
    }
  });
  $("#workspace-filters").append(form);
  $("#workspace-form-region").append(results);
  form.requestSubmit();
}

async function renderAccounts() {
  const users = await api("/users");
  state.users = users;
  const activeUsers = users.filter((user) => user.is_active);
  const statistics = makeElement("div", "stats-grid account-stats");
  [
    ["Tổng tài khoản", users.length],
    ["Đang hoạt động", activeUsers.length],
    ["Đã khóa", users.length - activeUsers.length],
    [
      "Quản trị viên",
      activeUsers.filter((user) => user.role === "admin").length,
    ],
  ].forEach(([label, value]) => {
    const card = makeElement("article", "stat-card account-stat-card");
    card.append(
      makeElement("div", "stat-label", label),
      makeElement("div", "stat-value", value),
    );
    statistics.append(card);
  });
  $("#workspace-form-region").append(statistics);

  const createForm = document.createElement("form");
  createForm.className = "inline-form admin-account-form";
  createForm.append(makeElement("strong", "", "Tạo tài khoản"));
  const username = inputField({
    name: "username",
    label: "Tên tài khoản",
    required: true,
  });
  username.querySelector("input").maxLength = 80;
  username.querySelector("input").autocomplete = "off";
  const fullName = inputField({
    name: "full_name",
    label: "Họ tên",
    required: true,
  });
  fullName.querySelector("input").maxLength = 160;
  const password = inputField({
    name: "password",
    label: "Mật khẩu (ít nhất 12 ký tự)",
    type: "password",
    required: true,
  });
  password.querySelector("input").minLength = 12;
  password.querySelector("input").maxLength = 256;
  password.querySelector("input").autocomplete = "new-password";
  const role = inputField({
    name: "role",
    label: "Vai trò",
    type: "select",
    required: true,
    options: [
      ["hr", "Nhân viên nhân sự"],
      ["manager", "Người quản lý"],
      ["admin", "Quản trị viên"],
    ],
  });
  createForm.append(username, fullName, password, role);
  addPasswordToggle(password.querySelector("input"));
  const createButton = makeElement(
    "button",
    "button button-primary",
    "Tạo tài khoản",
  );
  createButton.type = "submit";
  createForm.append(createButton);
  createForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    try {
      await api("/users", { method: "POST", body: JSON.stringify(values) });
      showToast("Đã tạo tài khoản.");
      await renderWorkspace();
    } catch (error) {
      showToast(error.message, true);
    }
  });
  const accountNote = makeElement(
    "p",
    "account-management-note",
    "Tài khoản không bị xóa vĩnh viễn để giữ nguyên lịch sử thao tác. Hãy khóa tài khoản khi người dùng không còn quyền truy cập.",
  );
  $("#workspace-form-region").append(createForm, accountNote);

  const search = makeElement("input", "workspace-search");
  search.type = "search";
  search.placeholder = "Tìm tên, họ tên hoặc vai trò";
  search.setAttribute("aria-label", "Tìm tài khoản");
  const roleFilter = document.createElement("select");
  roleFilter.setAttribute("aria-label", "Lọc theo vai trò");
  roleFilter.append(new Option("Tất cả vai trò", ""));
  for (const [value, label] of [
    ["admin", "Quản trị viên"],
    ["hr", "Nhân viên nhân sự"],
    ["manager", "Người quản lý"],
  ]) {
    roleFilter.add(new Option(label, value));
  }
  const statusFilter = document.createElement("select");
  statusFilter.setAttribute("aria-label", "Lọc theo trạng thái");
  statusFilter.append(
    new Option("Tất cả trạng thái", ""),
    new Option("Đang hoạt động", "active"),
    new Option("Đã khóa", "inactive"),
  );
  $("#workspace-filters").append(search, roleFilter, statusFilter);
  const drawRows = () => {
    const query = search.value.trim().toLocaleLowerCase("vi");
    const filtered = users.filter(
      (user) =>
        `${user.username} ${user.full_name} ${roleLabels[user.role] || user.role}`
          .toLocaleLowerCase("vi")
          .includes(query) &&
        (!roleFilter.value || user.role === roleFilter.value) &&
        (!statusFilter.value ||
          user.is_active === (statusFilter.value === "active")),
    );
    setTable(
      [
        "Tên tài khoản",
        "Họ tên",
        "Vai trò",
        "Trạng thái",
        "Tạo lúc",
        "Thao tác",
      ],
      filtered.map((user) => [
        user.username,
        user.full_name,
        roleLabels[user.role] || user.role,
        badge(
          user.is_active ? "active" : "ended",
          user.is_active ? "Đang hoạt động" : "Đã khóa",
        ),
        new Date(user.created_at).toLocaleString("vi-VN"),
        makeAccountActions(user),
      ]),
    );
  };
  search.addEventListener("input", drawRows);
  roleFilter.addEventListener("change", drawRows);
  statusFilter.addEventListener("change", drawRows);
  drawRows();
}

function openAccountModal(user) {
  const form = $("#account-form");
  form.reset();
  clearError($("#account-form-error"));
  form.elements.user_id.value = user.id;
  form.elements.username.value = user.username;
  form.elements.full_name.value = user.full_name;
  form.elements.role.value = user.role;
  $("#account-modal-title").textContent =
    `Chỉnh sửa tài khoản ${user.username}`;
  $("#account-backdrop").classList.remove("hidden");
}

function closeAccountModal() {
  $("#account-backdrop").classList.add("hidden");
  $("#account-form").reset();
}

async function updateAccount(userId, changes) {
  await api(`/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
  await renderWorkspace();
}

function makeAccountActions(user) {
  const edit = actionButton("Chỉnh sửa", "edit-account", user.id);
  const toggle = actionButton(
    user.is_active ? "Khóa" : "Mở khóa",
    "toggle-user",
    user.id,
  );
  if (user.id === state.user.id && user.is_active) {
    toggle.disabled = true;
    toggle.title = "Bạn không thể tự khóa tài khoản đang đăng nhập.";
  }
  const reset = actionButton("Đặt lại mật khẩu", "reset-password", user.id);
  if (user.id === state.user.id) {
    reset.disabled = true;
    reset.title = "Dùng chức năng Đổi mật khẩu cho tài khoản của bạn.";
  }
  return actionGroup([edit, reset, toggle]);
}

async function renderAudit() {
  const actorId = inputField({
    name: "actor_id",
    label: "Tài khoản ID",
    type: "number",
  });
  const action = inputField({ name: "action", label: "Thao tác" });
  const start = inputField({
    name: "start_date",
    label: "Từ ngày",
    type: "date",
  });
  const end = inputField({ name: "end_date", label: "Đến ngày", type: "date" });
  const form = document.createElement("form");
  form.className = "inline-form";
  form.append(
    makeElement("strong", "", "Lọc nhật ký"),
    actorId,
    action,
    start,
    end,
  );
  const submit = makeElement("button", "button button-primary", "Tìm kiếm");
  submit.type = "submit";
  form.append(submit);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const params = new URLSearchParams({ limit: "200" });
    for (const [name, control] of [
      ["actor_id", actorId.querySelector("input")],
      ["action", action.querySelector("input")],
      ["start_date", start.querySelector("input")],
      ["end_date", end.querySelector("input")],
    ]) {
      if (control.value) params.set(name, control.value);
    }
    try {
      const entries = await api(`/audit-logs?${params}`);
      setTable(
        [
          "Thời gian",
          "Tài khoản ID",
          "Thao tác",
          "Đối tượng",
          "ID",
          "Kết quả",
          "Chi tiết",
        ],
        entries.map((item) => [
          new Date(item.created_at).toLocaleString("vi-VN"),
          item.actor_id || "—",
          item.action,
          item.entity_type,
          item.entity_id || "—",
          item.outcome,
          JSON.stringify(item.details || {}),
        ]),
        { pageSize: 20 },
      );
    } catch (error) {
      showToast(error.message, true);
    }
  });
  $("#workspace-filters").append(form);
  form.requestSubmit();
}

function inputField(config) {
  const wrapper = makeElement("label", "form-field");
  wrapper.append(makeElement("span", "", config.label));
  let input;
  if (config.type === "select") {
    input = document.createElement("select");
    input.append(new Option("Chọn", ""));
    config.options.forEach(([value, label]) =>
      input.add(new Option(label, value)),
    );
  } else {
    input = document.createElement("input");
    input.type = config.type || "text";
  }
  input.name = config.name;
  input.required = Boolean(config.required);
  if (config.type === "checkbox") {
    wrapper.classList.add("checkbox-field");
    wrapper.append(input);
  } else {
    wrapper.append(input);
  }
  return wrapper;
}

function buildForm(fields, title, onSubmit, initialValues = {}, includeEmpty = false) {
  const form = document.createElement("form");
  form.className = "inline-form";
  form.append(makeElement("strong", "", title));
  const controls = new Map();
  for (const config of fields) {
    const wrapper = inputField(config);
    controls.set(config.name, wrapper.querySelector(`[name="${config.name}"]`));
    form.append(wrapper);
  }
  for (const [name, value] of Object.entries(initialValues)) {
    const control = controls.get(name);
    if (!control) continue;
    if (control.type === "checkbox") control.checked = Boolean(value);
    else control.value = value ?? "";
  }
  const submit = makeElement("button", "button button-primary", "Lưu");
  submit.type = "submit";
  form.append(submit);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = {};
    for (const [name, control] of controls) {
      if (control.type === "checkbox") values[name] = control.checked;
      else if (control.value !== "") values[name] = control.value;
      else if (includeEmpty) values[name] = null;
    }
    try {
      await onSubmit(values);
      showToast("Đã lưu dữ liệu.");
      await renderWorkspace();
    } catch (error) {
      showToast(error.message, true);
    }
  });
  return form;
}

function populateDepartmentSelect(select, selectedValue = "") {
  select.replaceChildren(new Option("Chọn đơn vị", ""));
  state.departments
    .filter((item) => item.is_active)
    .forEach((item) => select.add(new Option(item.name, String(item.id))));
  select.value = selectedValue ? String(selectedValue) : "";
}

function openTeacherModal(teacher = null) {
  const form = $("#teacher-form");
  form.reset();
  clearError($("#form-error"));
  const departmentSelect = form.elements.department_id;
  populateDepartmentSelect(departmentSelect, teacher?.department_id);
  $("#modal-title").textContent = teacher
    ? "Chỉnh sửa hồ sơ"
    : "Thêm giảng viên";
  $("#teacher-submit").textContent = teacher ? "Lưu thay đổi" : "Lưu hồ sơ";
  form.elements.teacher_id.value = teacher?.id || "";
  if (teacher) {
    for (const [key, value] of Object.entries(teacher)) {
      if (form.elements[key]) form.elements[key].value = value ?? "";
    }
    for (const key of [
      "department_id",
      "employment_status",
      "academic_degree",
      "academic_title",
    ]) {
      form.elements[key].disabled = true;
    }
    showToast(
      "Đơn vị, trạng thái, trình độ và chức danh chỉ đổi qua yêu cầu phê duyệt.",
    );
  } else {
    for (const key of [
      "department_id",
      "employment_status",
      "academic_degree",
      "academic_title",
    ]) {
      form.elements[key].disabled = false;
    }
  }
  $("#modal-backdrop").classList.remove("hidden");
}

function closeTeacherModal() {
  $("#modal-backdrop").classList.add("hidden");
  $("#teacher-form").reset();
}

function openDepartmentModal(department = null) {
  const form = $("#department-form");
  form.reset();
  clearError($("#department-form-error"));
  form.elements.department_id.value = department?.id || "";
  $("#department-modal-title").textContent = department
    ? "Chỉnh sửa đơn vị"
    : "Thêm đơn vị";
  const parent = form.elements.parent_id;
  parent.replaceChildren(new Option("Không có", ""));
  state.departments
    .filter((item) => item.is_active && item.id !== department?.id)
    .forEach((item) => parent.add(new Option(item.name, String(item.id))));
  if (department) {
    for (const [key, value] of Object.entries(department)) {
      if (form.elements[key]) form.elements[key].value = value ?? "";
    }
  }
  $("#department-backdrop").classList.remove("hidden");
}

function bindEvents() {
  $("#login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    clearError($("#login-error"));
    const data = new FormData(form);
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          username: data.get("username"),
          password: data.get("password"),
        }),
      });
      const user = await response.json();
      if (!response.ok) throw new Error(user.detail || "Không thể đăng nhập.");
      resetPasswordToggles(form);
      form.reset();
      showApp(user);
    } catch (error) {
      showError($("#login-error"), error.message);
    }
  });

  $("#logout-button").addEventListener("click", async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch (error) {
      showToast(error.message, true);
    } finally {
      showLogin();
    }
  });
  $("#password-button").addEventListener("click", () => {
    const form = $("#password-form");
    resetPasswordToggles(form);
    form.reset();
    clearError($("#password-error"));
    $("#password-backdrop").classList.remove("hidden");
  });
  const closePasswordModal = () => {
    resetPasswordToggles($("#password-form"));
    $("#password-form").reset();
    $("#password-backdrop").classList.add("hidden");
  };
  $("#password-close").addEventListener("click", closePasswordModal);
  $("#password-cancel").addEventListener("click", closePasswordModal);
  $("#password-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    try {
      await api("/auth/password", {
        method: "POST",
        body: JSON.stringify({
          current_password: data.get("current_password"),
          new_password: data.get("new_password"),
        }),
      });
      closePasswordModal();
      showLogin();
      showToast("Mật khẩu đã đổi. Đăng nhập lại bằng mật khẩu mới.");
    } catch (error) {
      showError($("#password-error"), error.message);
    }
  });
  $$(".nav-link").forEach((button) =>
    button.addEventListener("click", () => navigate(button.dataset.view)),
  );
  $("#mobile-menu").addEventListener("click", () =>
    $("#sidebar").classList.toggle("open"),
  );
  $("#teacher-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const teacherId = data.get("teacher_id");
    const payload = {};
    for (const [key, value] of data.entries()) {
      if (key !== "teacher_id" && value !== "") payload[key] = value;
    }
    payload.department_id = Number(payload.department_id);
    try {
      await api(teacherId ? `/teachers/${teacherId}` : "/teachers", {
        method: teacherId ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      closeTeacherModal();
      showToast("Đã lưu hồ sơ giảng viên.");
      await renderWorkspace();
    } catch (error) {
      showError($("#form-error"), error.message);
    }
  });
  $("#certificate-warning-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const days = Number($("#certificate-warning-days").value);
    try {
      await api(`/settings/certificate-warning-days?days=${days}`, {
        method: "PUT",
      });
      showToast("Đã cập nhật ngưỡng cảnh báo chứng chỉ.");
      await renderOverview();
    } catch (error) {
      showToast(error.message, true);
    }
  });
  $("#department-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const id = data.get("department_id");
    const payload = Object.fromEntries(
      [...data.entries()].filter(
        ([key, value]) => key !== "department_id" && value !== "",
      ),
    );
    if (payload.parent_id) payload.parent_id = Number(payload.parent_id);
    try {
      await api(id ? `/departments/${id}` : "/departments", {
        method: id ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      $("#department-backdrop").classList.add("hidden");
      showToast("Đã lưu đơn vị.");
      await renderWorkspace();
    } catch (error) {
      showError($("#department-form-error"), error.message);
    }
  });
  $("#modal-close").addEventListener("click", closeTeacherModal);
  $("#modal-cancel").addEventListener("click", closeTeacherModal);
  $("#account-modal-close").addEventListener("click", closeAccountModal);
  $("#account-modal-cancel").addEventListener("click", closeAccountModal);
  $("#account-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const userId = form.elements.user_id.value;
    const payload = {
      full_name: form.elements.full_name.value,
      role: form.elements.role.value,
    };
    try {
      await updateAccount(userId, payload);
      closeAccountModal();
      showToast("Đã cập nhật tài khoản.");
    } catch (error) {
      showError($("#account-form-error"), error.message);
    }
  });
  $("#department-modal-close").addEventListener("click", () =>
    $("#department-backdrop").classList.add("hidden"),
  );
  $("#department-modal-cancel").addEventListener("click", () =>
    $("#department-backdrop").classList.add("hidden"),
  );

  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    const id = Number(button.dataset.id);
    try {
      switch (button.dataset.action) {
        case "add-teacher":
          await refreshData();
          openTeacherModal();
          break;
        case "edit-teacher":
          await refreshData();
          openTeacherModal(state.teachers.find((teacher) => teacher.id === id));
          break;
        case "teacher-detail":
          state.selectedTeacherId = String(id);
          state.detailTab = "info";
          state.detailEdit = null;
          navigate("teacherDetail");
          break;
        case "teacher-checklist":
          state.selectedTeacherId = String(id);
          state.detailTab = "completeness";
          state.detailEdit = null;
          navigate("teacherDetail");
          break;
        case "edit-qualification":
          if (state.user.role !== "hr")
            throw new Error("Bạn không có quyền sửa bằng cấp.");
          state.detailEdit = { kind: "qualification", id };
          await renderWorkspace();
          break;
        case "edit-contract":
          if (state.user.role !== "hr")
            throw new Error("Bạn không có quyền sửa hợp đồng.");
          state.detailEdit = { kind: "contract", id };
          await renderWorkspace();
          break;
        case "toggle-contract-status": {
          if (state.user.role !== "hr")
            throw new Error("Bạn không có quyền cập nhật hợp đồng.");
          const contracts = await api(
            `/teachers/${state.selectedTeacherId}/contracts`,
          );
          const contract = contracts.find((item) => item.id === id);
          if (!contract) throw new Error("Không tìm thấy hợp đồng cần cập nhật.");
          await api(`/contracts/${id}`, {
            method: "PATCH",
            body: JSON.stringify({
              status: contract.status === "terminated" ? "active" : "terminated",
            }),
          });
          await renderWorkspace();
          break;
        }
        case "add-department":
          await refreshData();
          openDepartmentModal();
          break;
        case "edit-department":
          openDepartmentModal(state.departments.find((unit) => unit.id === id));
          break;
        case "toggle-department": {
          const unit = state.departments.find((item) => item.id === id);
          await api(`/departments/${id}`, {
            method: "PATCH",
            body: JSON.stringify({ is_active: !unit.is_active }),
          });
          await renderWorkspace();
          break;
        }
        case "download-document": {
          const response = await api(`/documents/${id}/download`);
          const link = document.createElement("a");
          link.href = URL.createObjectURL(await response.blob());
          link.download = "evidence";
          link.click();
          URL.revokeObjectURL(link.href);
          break;
        }
        case "decide-change":
          await api(`/change-requests/${id}/decision`, {
            method: "POST",
            body: JSON.stringify({ action: "approve" }),
          });
          showToast("Yêu cầu đã được duyệt.");
          await renderWorkspace();
          break;
        case "reject-change":
        case "request-info": {
          const reason = window.prompt("Nhập lý do (bắt buộc):");
          if (!reason?.trim()) break;
          await api(`/change-requests/${id}/decision`, {
            method: "POST",
            body: JSON.stringify({
              action:
                button.dataset.action === "reject-change"
                  ? "reject"
                  : "request_info",
              reason,
            }),
          });
          await renderWorkspace();
          break;
        }
        case "resubmit-change": {
          const currentRequests = await api("/change-requests");
          const change = currentRequests.find((item) => item.id === id);
          if (!change) break;
          const proposalText = window.prompt(
            "Cập nhật nội dung đề xuất (JSON):",
            JSON.stringify(change.proposed_value),
          );
          if (!proposalText) break;
          const reason = window.prompt("Ghi nội dung bổ sung/lý do:");
          if (!reason?.trim()) break;
          const proposedValue = JSON.parse(proposalText);
          await api(`/change-requests/${id}`, {
            method: "PATCH",
            body: JSON.stringify({
              proposed_value: proposedValue,
              reason,
              effective_on: change.effective_on,
            }),
          });
          await renderWorkspace();
          break;
        }
        case "edit-checklist-item": {
          if (state.user.role !== "hr")
            throw new Error("Bạn không có quyền sửa danh mục checklist.");
          const items = await api("/checklist-items");
          const item = items.find((entry) => entry.id === id);
          if (!item) throw new Error("Không tìm thấy mục checklist cần sửa.");
          const classification = window.prompt(
            "Phân loại: required, conditional hoặc optional",
            item?.classification || "conditional",
          );
          if (
            !classification ||
            !["required", "conditional", "optional"].includes(classification)
          )
            break;
          const applicability = window.prompt(
            "Điều kiện áp dụng",
            item?.applicability || "",
          );
          if (applicability === null) break;
          await api(`/checklist-items/${id}`, {
            method: "PATCH",
            body: JSON.stringify({ classification, applicability }),
          });
          await renderWorkspace();
          break;
        }
        case "toggle-checklist-active": {
          if (state.user.role !== "hr")
            throw new Error("Bạn không có quyền cập nhật danh mục checklist.");
          const items = await api("/checklist-items");
          const item = items.find((entry) => entry.id === id);
          if (!item) throw new Error("Không tìm thấy mục checklist cần cập nhật.");
          await api(`/checklist-items/${id}`, {
            method: "PATCH",
            body: JSON.stringify({ is_active: !item.is_active }),
          });
          await renderWorkspace();
          break;
        }
        case "toggle-user": {
          const user = state.users.find((entry) => entry.id === id);
          if (!user) throw new Error("Không tìm thấy tài khoản cần cập nhật.");
          if (
            user.is_active &&
            !window.confirm(`Khóa tài khoản "${user.username}"?`)
          )
            break;
          await updateAccount(id, { is_active: !user.is_active });
          showToast(
            user.is_active ? "Đã khóa tài khoản." : "Đã mở khóa tài khoản.",
          );
          break;
        }
        case "edit-account": {
          const user = state.users.find((entry) => entry.id === id);
          if (!user) throw new Error("Không tìm thấy tài khoản cần cập nhật.");
          openAccountModal(user);
          break;
        }
        default:
          break;
      }
    } catch (error) {
      showToast(error.message, true);
    }
  });
}

const qualificationTypeLabels = {
  degree: "Bằng cấp",
  certificate: "Chứng chỉ",
  research: "Nghiên cứu",
  other: "Khác",
};
const detailTabs = [
  ["info", "Thông tin"],
  ["quals", "Bằng cấp"],
  ["contracts", "Hợp đồng"],
  ["history", "Quá trình công tác"],
  ["docs", "Tài liệu"],
  ["completeness", "Hồ sơ còn thiếu"],
];

function detailButton(label, action, icon, id, primary = false) {
  const button = headerButton(label, action, icon, primary);
  button.dataset.id = String(id);
  return button;
}

async function renderTeacherDetail() {
  const teacher = state.teachers.find(
    (item) => String(item.id) === String(state.selectedTeacherId),
  );
  if (!teacher) {
    navigate("teachers");
    return;
  }
  $("#detail-title").textContent = teacher.full_name;
  $("#detail-subtitle").textContent =
    `${teacher.employee_code} · ${departmentName(teacher.department_id)}`;
  const actions = [
    detailButton("Danh sách", "detail-back", "chev", teacher.id, false),
  ];
  if (state.user.role === "hr") {
    actions.push(
      detailButton("Sửa hồ sơ", "edit-teacher", "check", teacher.id, true),
      detailButton("Checklist", "teacher-checklist", "list", teacher.id, false),
      detailButton("Xóa hồ sơ", "delete-teacher", "trash", teacher.id, false),
    );
  }
  $("#detail-actions").replaceChildren(...actions);
  const tabs = $("#detail-tabs");
  tabs.replaceChildren();
  for (const [key, label] of detailTabs) {
    const tab = makeElement(
      "button",
      `tab${state.detailTab === key ? " active" : ""}`,
      label,
    );
    tab.type = "button";
    tab.dataset.action = "detail-tab";
    tab.dataset.tab = key;
    tab.setAttribute("role", "tab");
    tabs.append(tab);
  }
  await drawDetailTab(teacher);
}

async function drawDetailTab(teacher) {
  const body = $("#detail-body");
  body.replaceChildren();
  const id = teacher.id;
  const isHr = state.user.role === "hr";
  if (state.detailTab === "info") {
    const list = makeElement("dl", "info-grid");
    const fields = [
      ["Mã giảng viên", teacher.employee_code],
      ["Họ và tên", teacher.full_name],
      ["Đơn vị công tác", departmentName(teacher.department_id)],
      ["Trạng thái", badge(teacher.employment_status)],
      ["Ngày sinh", teacher.date_of_birth],
      ["Giới tính", teacher.gender],
      ["Email", teacher.email],
      ["Số điện thoại", teacher.phone],
      ["Trình độ", teacher.academic_degree],
      ["Chức danh", teacher.academic_title],
      ["Địa chỉ liên hệ", teacher.address],
    ];
    for (const [label, value] of fields) {
      const row = document.createElement("div");
      const term = makeElement("dt", "", label);
      const detail = document.createElement("dd");
      if (value instanceof Node) detail.append(value);
      else detail.textContent = value || "—";
      row.append(term, detail);
      list.append(row);
    }
    body.append(list);
  } else if (state.detailTab === "quals") {
    const items = await api(`/teachers/${id}/qualifications`);
    body.append(
      buildTable(
        [
          "Loại",
          "Tên",
          "Chuyên ngành",
          "Cơ sở đào tạo",
          "Năm",
          "Ngày hết hạn",
          ...(isHr ? ["Thao tác"] : []),
        ],
        items.map((item) => [
          qualificationTypeLabels[item.qualification_type] ||
            item.qualification_type,
          item.title,
          item.specialty,
          item.institution,
          item.issued_year || item.issued_on,
          item.expires_on,
          ...(isHr
            ? [actionButton("Sửa", "edit-qualification", item.id)]
            : []),
        ]),
        "Chưa có bằng cấp hoặc chứng chỉ.",
      ),
    );
    if (isHr) {
      const editing =
        state.detailEdit?.kind === "qualification"
          ? items.find((item) => item.id === state.detailEdit.id)
          : null;
      const fields = [
        {
          name: "qualification_type",
          label: "Loại",
          type: "select",
          required: true,
          options: [
            ["degree", "Bằng cấp"],
            ["certificate", "Chứng chỉ"],
            ["research", "Nghiên cứu"],
            ["other", "Khác"],
          ],
        },
        { name: "title", label: "Tên văn bằng/chứng chỉ", required: true },
        { name: "specialty", label: "Chuyên ngành" },
        { name: "institution", label: "Cơ sở đào tạo" },
        { name: "issued_year", label: "Năm cấp", type: "number" },
        { name: "expires_on", label: "Ngày hết hạn (nếu có)", type: "date" },
      ];
      body.append(
        buildForm(
          fields,
          editing
            ? "Sửa bằng cấp hoặc chứng chỉ"
            : "Thêm bằng cấp hoặc chứng chỉ",
          async (values) => {
            if (values.issued_year)
              values.issued_year = Number(values.issued_year);
            await api(
              editing
                ? `/qualifications/${editing.id}`
                : `/teachers/${id}/qualifications`,
              {
                method: editing ? "PATCH" : "POST",
                body: JSON.stringify(values),
              },
            );
            state.detailEdit = null;
          },
          editing
            ? {
                qualification_type: editing.qualification_type,
                title: editing.title,
                specialty: editing.specialty,
                institution: editing.institution,
                issued_year: editing.issued_year,
                expires_on: editing.expires_on,
              }
            : {},
          Boolean(editing),
        ),
      );
    }
  } else if (state.detailTab === "contracts") {
    const items = await api(`/teachers/${id}/contracts`);
    if (isHr) {
      state.contractWarningDays = (
        await api("/settings/contract-warning-days")
      ).days;
      body.append(
        buildForm(
          [
            {
              name: "days",
              label: `Cảnh báo trước bao nhiêu ngày (hiện tại ${state.contractWarningDays})`,
              type: "number",
              required: true,
            },
          ],
          "Cấu hình cảnh báo hợp đồng",
          async (values) => {
            const days = Number(values.days);
            if (!Number.isInteger(days) || days < 0 || days > 365)
              throw new Error("Số ngày phải từ 0 đến 365.");
            await api(`/settings/contract-warning-days?days=${days}`, {
              method: "PUT",
            });
            state.contractWarningDays = days;
          },
          { days: state.contractWarningDays },
        ),
      );
    }
    body.append(
      buildTable(
        [
          "Mã hợp đồng",
          "Loại",
          "Bắt đầu",
          "Kết thúc",
          "Trạng thái",
          ...(isHr ? ["Thao tác"] : []),
        ],
        items.map((item) => [
          item.contract_code,
          item.contract_type,
          item.starts_on,
          item.ends_on || "Không thời hạn",
          badge(item.display_status),
          ...(isHr
            ? [
                actionGroup([
                  actionButton("Sửa", "edit-contract", item.id),
                  actionButton(
                    item.status === "terminated" ? "Kích hoạt" : "Chấm dứt",
                    "toggle-contract-status",
                    item.id,
                  ),
                ]),
              ]
            : []),
        ]),
        "Chưa có hợp đồng.",
      ),
    );
    if (isHr) {
      const editing =
        state.detailEdit?.kind === "contract"
          ? items.find((item) => item.id === state.detailEdit.id)
          : null;
      const fields = [
        { name: "contract_code", label: "Mã hợp đồng", required: true },
        { name: "contract_type", label: "Loại hợp đồng", required: true },
        { name: "signed_on", label: "Ngày ký", type: "date" },
        {
          name: "starts_on",
          label: "Ngày bắt đầu",
          type: "date",
          required: true,
        },
        { name: "ends_on", label: "Ngày kết thúc", type: "date" },
        ...(editing
          ? [
              {
                name: "status",
                label: "Trạng thái",
                type: "select",
                required: true,
                options: [
                  ["active", "Đang hiệu lực"],
                  ["terminated", "Đã chấm dứt"],
                ],
              },
            ]
          : []),
      ];
      body.append(
        buildForm(
          fields,
          editing ? "Sửa hợp đồng" : "Thêm hợp đồng",
          async (values) => {
            await api(
              editing
                ? `/contracts/${editing.id}`
                : `/teachers/${id}/contracts`,
              {
                method: editing ? "PATCH" : "POST",
                body: JSON.stringify(values),
              },
            );
            state.detailEdit = null;
          },
          editing
            ? {
                contract_code: editing.contract_code,
                contract_type: editing.contract_type,
                signed_on: editing.signed_on,
                starts_on: editing.starts_on,
                ends_on: editing.ends_on,
                status: editing.status,
              }
            : {},
          Boolean(editing),
        ),
      );
    }
  } else if (state.detailTab === "history") {
    const history = await api(`/teachers/${id}/work-history`);
    body.append(buildTimeline(history));
    body.append(
      buildTable(
        ["Đơn vị", "Chức danh", "Bắt đầu", "Kết thúc", "Lý do"],
        history.map((item) => [
          state.departments.find((unit) => unit.id === item.department_id)
            ?.name || "—",
          item.position_title || "—",
          item.starts_on,
          item.ends_on || "Hiện tại",
          item.reason || "—",
        ]),
        "Chưa có quá trình công tác.",
      ),
    );
    if (isHr) {
      body.append(
        buildForm(
          [
            {
              name: "department_id",
              label: "Đơn vị",
              type: "select",
              required: true,
              options: state.departments.map((unit) => [
                String(unit.id),
                unit.name,
              ]),
            },
            { name: "position_title", label: "Chức danh" },
            {
              name: "starts_on",
              label: "Ngày bắt đầu",
              type: "date",
              required: true,
            },
            { name: "ends_on", label: "Ngày kết thúc", type: "date" },
            { name: "reason", label: "Lý do" },
          ],
          "Bổ sung giai đoạn công tác",
          async (values) => {
            values.department_id = Number(values.department_id);
            await api(`/teachers/${id}/work-history`, {
              method: "POST",
              body: JSON.stringify(values),
            });
          },
        ),
      );
    }
  } else if (state.detailTab === "docs") {
    const items = await api(`/teachers/${id}/documents`);
    body.append(
      buildTable(
        ["Tài liệu", "Dung lượng", "Ngày tải", ...(isHr ? ["Tải xuống"] : [])],
        items.map((item) => [
          item.original_name,
          `${Math.ceil(item.size_bytes / 1024)} KB`,
          new Date(item.created_at).toLocaleString("vi-VN"),
          ...(isHr
            ? [actionButton("Tải tệp", "download-document", item.id)]
            : []),
        ]),
        "Chưa có tài liệu minh chứng.",
      ),
    );
    if (isHr) {
      const [checklist, qualifications, contracts] = await Promise.all([
        api("/checklist-items"),
        api(`/teachers/${id}/qualifications`),
        api(`/teachers/${id}/contracts`),
      ]);
      const form = document.createElement("form");
      form.className = "inline-form";
      form.append(makeElement("strong", "", "Tải minh chứng"));
      const fileLabel = makeElement("label", "form-field");
      fileLabel.append(makeElement("span", "", "Chọn tệp"));
      const file = document.createElement("input");
      file.type = "file";
      file.name = "file";
      file.accept = ".pdf,.png,.jpg,.jpeg";
      file.required = true;
      fileLabel.append(file);
      form.append(fileLabel);

      const checklistLabel = makeElement("label", "form-field");
      checklistLabel.append(makeElement("span", "", "Gắn checklist"));
      const checklistSelect = document.createElement("select");
      checklistSelect.name = "checklist_item_id";
      checklistSelect.append(new Option("Không gắn checklist", ""));
      checklist
        .filter((item) => item.is_active)
        .forEach((item) =>
          checklistSelect.add(new Option(item.label, String(item.id))),
        );
      checklistLabel.append(checklistSelect);
      form.append(checklistLabel);

      const qualificationLabel = makeElement("label", "form-field");
      qualificationLabel.append(makeElement("span", "", "Gắn bằng cấp"));
      const qualificationSelect = document.createElement("select");
      qualificationSelect.name = "qualification_id";
      qualificationSelect.append(new Option("Không gắn bằng cấp", ""));
      qualifications.forEach((item) =>
        qualificationSelect.add(new Option(item.title, String(item.id))),
      );
      qualificationLabel.append(qualificationSelect);
      form.append(qualificationLabel);

      const contractLabel = makeElement("label", "form-field");
      contractLabel.append(makeElement("span", "", "Gắn hợp đồng"));
      const contractSelect = document.createElement("select");
      contractSelect.name = "contract_id";
      contractSelect.append(new Option("Không gắn hợp đồng", ""));
      contracts.forEach((item) =>
        contractSelect.add(new Option(item.contract_code, String(item.id))),
      );
      contractLabel.append(contractSelect);
      form.append(contractLabel);

      qualificationSelect.addEventListener("change", () => {
        contractSelect.disabled = Boolean(qualificationSelect.value);
      });
      contractSelect.addEventListener("change", () => {
        qualificationSelect.disabled = Boolean(contractSelect.value);
      });
      const submit = makeElement("button", "button button-primary", "Tải lên");
      submit.type = "submit";
      form.append(submit);
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const data = new FormData();
        data.append("file", file.files[0]);
        if (checklistSelect.value)
          data.append("checklist_item_id", checklistSelect.value);
        if (qualificationSelect.value)
          data.append("qualification_id", qualificationSelect.value);
        if (contractSelect.value)
          data.append("contract_id", contractSelect.value);
        try {
          await api(`/teachers/${id}/documents`, {
            method: "POST",
            body: data,
          });
          showToast("Đã tải tài liệu lên.");
          await renderWorkspace();
        } catch (error) {
          showToast(error.message, true);
        }
      });
      body.append(form);
    }
  } else {
    const [requirements, completeness] = await Promise.all([
      api(`/teachers/${id}/checklist-requirements`),
      api(`/teachers/${id}/completeness`),
    ]);
    body.append(
      makeElement(
        "p",
        "page-subtitle",
        `${teacher.employee_code} — ${teacher.full_name}. ` +
          (completeness.is_complete
            ? "Hồ sơ đầy đủ theo các yêu cầu đã rà soát."
            : `Còn thiếu: ${completeness.missing.join(", ") || "không có"}. ` +
              `Cần rà soát điều kiện: ${completeness.needs_review.join(", ") || "không có"}.`),
      ),
    );
    body.append(
      buildTable(
        [
          "Tài liệu",
          "Nhóm",
          "Phân loại",
          "Điều kiện áp dụng",
          "Yêu cầu với giảng viên",
          "Minh chứng",
        ],
        requirements.map((item) => {
          let requirementStatus;
          if (isHr) {
            requirementStatus = document.createElement("select");
            requirementStatus.dataset.itemId = String(item.item_id);
            for (const [value, label] of Object.entries(
              checklistRequirementStatuses,
            )) {
              requirementStatus.add(new Option(label, value));
            }
            requirementStatus.value = item.status;
            requirementStatus.addEventListener("change", async () => {
              requirementStatus.disabled = true;
              try {
                await api(
                  `/teachers/${id}/checklist-requirements/${item.item_id}`,
                  {
                    method: "PATCH",
                    body: JSON.stringify({ status: requirementStatus.value }),
                  },
                );
                showToast("Đã cập nhật yêu cầu checklist.");
                await renderWorkspace();
              } catch (error) {
                showToast(error.message, true);
                await drawDetailTab(teacher);
              }
            });
          } else {
            requirementStatus = checklistRequirementStatuses[item.status];
          }
          const evidence = makeElement(
            "span",
            "",
            item.status === "required" &&
              completeness.missing.includes(item.label)
              ? "Chưa tải lên"
              : item.status === "required"
                ? "Đã có"
                : "—",
          );
          return [
            item.label,
            item.category,
            checklistClassifications[item.classification] ||
              item.classification,
            item.applicability || "—",
            requirementStatus,
            evidence,
          ];
        }),
        "Chưa có mục checklist cần rà soát.",
      ),
    );
    if (isHr) {
      body.append(makeElement("h3", "detail-section-title", "Quản lý danh mục checklist"));
      const items = await api("/checklist-items");
      body.append(
        buildTable(
          [
            "Mã",
            "Tài liệu",
            "Nhóm",
            "Phân loại",
            "Điều kiện áp dụng",
            "Nhạy cảm",
            "Trạng thái",
            "Thao tác",
          ],
          items.map((item) => [
            item.code,
            item.label,
            item.category,
            checklistClassifications[item.classification] ||
              item.classification,
            item.applicability || "—",
            item.is_sensitive ? "Có" : "Không",
            item.is_active ? "Đang dùng" : "Đã ngừng",
            actionGroup([
              actionButton("Sửa điều kiện", "edit-checklist-item", item.id),
              actionButton(
                item.is_active ? "Ngừng" : "Kích hoạt",
                "toggle-checklist-active",
                item.id,
              ),
            ]),
          ]),
          "Chưa có mục checklist.",
        ),
      );
      body.append(
        buildForm(
          [
            {
              name: "code",
              label: "Mã mục (chữ thường, số, gạch ngang)",
              required: true,
            },
            { name: "label", label: "Tên trường/tài liệu", required: true },
            { name: "category", label: "Nhóm", required: true },
            {
              name: "classification",
              label: "Phân loại trong danh mục",
              type: "select",
              required: true,
              options: [
                ["required", "Bắt buộc"],
                ["conditional", "Có điều kiện"],
                ["optional", "Tùy chọn"],
              ],
            },
            {
              name: "applicability",
              label: "Điều kiện áp dụng (tối đa 500 ký tự)",
            },
            { name: "is_sensitive", label: "Dữ liệu nhạy cảm", type: "checkbox" },
          ],
          "Thêm mục checklist",
          async (values) => {
            values.is_sensitive = Boolean(values.is_sensitive);
            await api("/checklist-items", {
              method: "POST",
              body: JSON.stringify(values),
            });
          },
        ),
      );
    }
  }
}

const seenKey = () => `neu-notifications-${state.user?.id}`;
function seenIds() {
  try {
    return new Set(JSON.parse(localStorage.getItem(seenKey()) || "[]"));
  } catch {
    return new Set();
  }
}
function saveSeen(ids) {
  try {
    localStorage.setItem(seenKey(), JSON.stringify([...ids].slice(-200)));
  } catch {
    /* lưu trữ cục bộ không khả dụng */
  }
}

async function loadNotifications() {
  if (!state.user) return;
  try {
    state.notifications = await api("/notifications");
  } catch {
    state.notifications = [];
  }
  drawNotifications();
}

function drawNotifications() {
  if (!state.user) return;
  const seen = seenIds();
  const list = $("#notif-list");
  list.replaceChildren();
  const unread = state.notifications.filter(
    (item) => !seen.has(item.id),
  ).length;
  const counter = $("#notif-count");
  counter.textContent = unread > 9 ? "9+" : String(unread);
  counter.classList.toggle("hidden", unread === 0);
  if (!state.notifications.length) {
    list.append(makeElement("div", "notif-empty", "Chưa có thông báo mới."));
    return;
  }
  for (const item of state.notifications) {
    const entry = makeElement(
      "button",
      `notif-item${seen.has(item.id) ? "" : " unread"}`,
    );
    entry.type = "button";
    entry.dataset.action = "notif-open";
    entry.dataset.view = item.view;
    entry.dataset.notif = item.id;
    entry.append(
      makeElement("strong", "", item.title),
      makeElement("span", "", item.message),
    );
    list.append(entry);
  }
}

function startNotifications() {
  stopNotifications();
  loadNotifications();
  state.notifTimer = window.setInterval(loadNotifications, 60000);
}

function stopNotifications() {
  if (state.notifTimer) window.clearInterval(state.notifTimer);
  state.notifTimer = null;
  state.notifications = [];
}

function applyTheme() {
  try {
    const saved = localStorage.getItem("neu-theme");
    if (saved) document.documentElement.dataset.theme = saved;
  } catch {
    /* bỏ qua */
  }
}

function toggleTheme() {
  const root = document.documentElement;
  const dark = root.dataset.theme
    ? root.dataset.theme === "dark"
    : window.matchMedia("(prefers-color-scheme: dark)").matches;
  root.dataset.theme = dark ? "light" : "dark";
  try {
    localStorage.setItem("neu-theme", root.dataset.theme);
  } catch {
    /* bỏ qua */
  }
}

let confirmHandler = null;
function openConfirm({ title, message, label = "Xóa", onConfirm }) {
  $("#confirm-title").textContent = title;
  $("#confirm-message").textContent = message;
  $("#confirm-ok").textContent = label;
  confirmHandler = onConfirm;
  $("#confirm-backdrop").classList.remove("hidden");
}
function closeConfirm() {
  confirmHandler = null;
  $("#confirm-backdrop").classList.add("hidden");
}

const DELETE_NOTICE =
  "Chức năng xóa chưa được kích hoạt trong phiên bản này. Dữ liệu có lịch sử được bảo toàn; hãy dùng thao tác Ngừng hoạt động hoặc đổi trạng thái công tác.";

function bindNewEvents() {
  const closeMenus = () => {
    $("#notif-panel").classList.add("hidden");
    $("#user-panel").classList.add("hidden");
  };
  const toggleMenu = (panelId) => {
    const panel = $(panelId);
    const willOpen = panel.classList.contains("hidden");
    closeMenus();
    panel.classList.toggle("hidden", !willOpen);
    return willOpen;
  };
  $("#notif-button").addEventListener("click", () => {
    if (toggleMenu("#notif-panel")) loadNotifications();
  });
  $("#user-button").addEventListener("click", () => toggleMenu("#user-panel"));
  document.addEventListener("click", (event) => {
    if (!event.target.closest("#notif-button, #user-button, #notif-panel"))
      closeMenus();
  });
  $("#notif-read").addEventListener("click", () => {
    const seen = seenIds();
    state.notifications.forEach((item) => seen.add(item.id));
    saveSeen(seen);
    drawNotifications();
  });
  $("#scrim").addEventListener("click", () =>
    $("#sidebar").classList.remove("open"),
  );
  $("#theme-fab").addEventListener("click", toggleTheme);

  const closeReset = () => {
    $("#reset-backdrop").classList.add("hidden");
    $("#reset-form").reset();
  };
  $("#reset-close").addEventListener("click", closeReset);
  $("#reset-cancel").addEventListener("click", closeReset);
  $("#reset-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    clearError($("#reset-error"));
    try {
      await api(`/users/${form.elements.user_id.value}/reset-password`, {
        method: "POST",
        body: JSON.stringify({
          new_password: form.elements.new_password.value,
        }),
      });
      resetPasswordToggles(form);
      closeReset();
      showToast("Đã đặt lại mật khẩu. Người dùng cần đăng nhập lại.");
    } catch (error) {
      showError($("#reset-error"), error.message);
    }
  });

  const closeImport = () => {
    $("#import-backdrop").classList.add("hidden");
    $("#import-form").reset();
    $("#import-result").classList.add("hidden");
    clearError($("#import-error"));
  };
  $("#import-close").addEventListener("click", closeImport);
  $("#import-cancel").addEventListener("click", closeImport);
  $("#import-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    clearError($("#import-error"));
    try {
      const result = await api("/teachers/import", {
        method: "POST",
        body: new FormData(form),
      });
      const box = $("#import-result");
      box.replaceChildren(
        makeElement(
          "strong",
          "",
          `Đã nhập ${result.created} giảng viên, bỏ qua ${result.skipped} dòng.`,
        ),
      );
      if (result.errors.length) {
        const list = document.createElement("ul");
        result.errors.forEach((item) =>
          list.append(
            makeElement("li", "", `Dòng ${item.row}: ${item.message}`),
          ),
        );
        box.append(list);
      }
      box.classList.remove("hidden");
      if (result.created) {
        showToast(`Đã nhập ${result.created} giảng viên.`);
        await renderWorkspace();
      }
    } catch (error) {
      showError($("#import-error"), error.message);
    }
  });

  $("#confirm-close").addEventListener("click", closeConfirm);
  $("#confirm-cancel").addEventListener("click", closeConfirm);
  $("#confirm-ok").addEventListener("click", () => {
    const handler = confirmHandler;
    closeConfirm();
    handler?.();
  });

  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    const id = Number(button.dataset.id);
    try {
      switch (button.dataset.action) {
        case "goto":
          navigate(button.dataset.view);
          break;
        case "notif-open": {
          const seen = seenIds();
          seen.add(button.dataset.notif);
          saveSeen(seen);
          drawNotifications();
          closeMenus();
          navigate(button.dataset.view);
          break;
        }
        case "page-prev":
          state.table.page -= 1;
          drawTablePage();
          break;
        case "page-next":
          state.table.page += 1;
          drawTablePage();
          break;
        case "teacher-open":
          state.selectedTeacherId = String(id);
          state.detailTab = "info";
          state.detailEdit = null;
          navigate("teacherDetail");
          break;
        case "detail-back":
          navigate("teachers");
          break;
        case "detail-tab": {
          state.detailTab = button.dataset.tab;
          state.detailEdit = null;
          const teacher = state.teachers.find(
            (item) => String(item.id) === String(state.selectedTeacherId),
          );
          $$(".tab").forEach((tab) =>
            tab.classList.toggle("active", tab.dataset.tab === state.detailTab),
          );
          if (teacher) await drawDetailTab(teacher);
          break;
        }
        case "export-teachers":
          await downloadResponse(
            `/teachers/export.xlsx?${state.teacherQuery}`,
            "danh_sach_giang_vien.xlsx",
          );
          break;
        case "download-template":
          await downloadResponse(
            "/teachers/import-template.xlsx",
            "mau_nhap_giang_vien.xlsx",
          );
          break;
        case "import-teachers":
          $("#import-backdrop").classList.remove("hidden");
          break;
        case "reset-password": {
          const user = state.users.find((entry) => entry.id === id);
          if (!user) throw new Error("Không tìm thấy tài khoản.");
          $("#reset-form").elements.user_id.value = String(id);
          $("#reset-note").textContent =
            `Đặt mật khẩu mới cho tài khoản "${user.username}". Mọi phiên đăng nhập hiện tại của tài khoản này sẽ bị đăng xuất.`;
          clearError($("#reset-error"));
          $("#reset-backdrop").classList.remove("hidden");
          break;
        }
        case "delete-teacher": {
          const teacher = state.teachers.find((item) => item.id === id);
          openConfirm({
            title: "Xóa hồ sơ giảng viên",
            message: `Bạn có chắc muốn xóa hồ sơ ${teacher ? `${teacher.full_name} (${teacher.employee_code})` : "này"}?`,
            onConfirm: () => showToast(DELETE_NOTICE),
          });
          break;
        }
        case "delete-department": {
          const unit = state.departments.find((item) => item.id === id);
          openConfirm({
            title: "Xóa đơn vị",
            message: `Bạn có chắc muốn xóa đơn vị ${unit ? `"${unit.name}"` : "này"}?`,
            onConfirm: () => showToast(DELETE_NOTICE),
          });
          break;
        }
        default:
          break;
      }
    } catch (error) {
      showToast(error.message, true);
    }
  });
}

async function initialize() {
  $("#today-date").textContent = new Date().toLocaleDateString("vi-VN", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  $("#footer-year").textContent = String(new Date().getFullYear());
  $$('input[type="password"]').forEach(addPasswordToggle);
  bindEvents();
  bindNewEvents();
  applyTheme();
  try {
    const user = await api("/auth/session");
    showApp(user);
  } catch {
    showLogin();
  }
}

initialize();

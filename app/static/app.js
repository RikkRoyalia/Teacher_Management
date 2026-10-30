const state = {
  user: null,
  csrfToken: "",
  currentView: "overview",
  teachers: [],
  departments: [],
  users: [],
  selectedTeacherId: "",
  contractWarningDays: 30,
};

const viewTitles = {
  overview: "Tổng quan",
  teachers: "Hồ sơ giảng viên",
  teacherChecklist: "Rà soát checklist hồ sơ",
  departments: "Khoa & bộ môn",
  qualifications: "Bằng cấp & chứng chỉ",
  contracts: "Hợp đồng lao động",
  history: "Quá trình công tác",
  documents: "Tài liệu minh chứng",
  changes: "Yêu cầu thay đổi",
  checklist: "Checklist hồ sơ",
  reports: "Báo cáo nhân sự",
  accounts: "Quản trị hệ thống",
  audit: "Nhật ký hoạt động",
};

const roleLabels = { admin: "Quản trị viên", hr: "Nhân viên nhân sự", manager: "Người quản lý" };
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
    toggle.setAttribute("aria-label", `${showPassword ? "Ẩn" : "Hiện"} mật khẩu`);
    toggle.setAttribute("aria-pressed", String(showPassword));
  });

  field.replaceWith(container);
  control.append(input, toggle);
  container.append(label, control);
}

function resetPasswordToggles(form) {
  $$('[data-password-toggle="true"]', form).forEach((input) => {
    if (input.type === "text") input.type = "password";
    const toggle = input.closest(".password-input-wrap").querySelector("button");
    toggle.textContent = "Hiện";
    toggle.setAttribute("aria-label", "Hiện mật khẩu");
    toggle.setAttribute("aria-pressed", "false");
  });
}

function initials(name = "") {
  return name.trim().split(/\s+/).slice(-2).map((part) => Array.from(part)[0] || "").join("").toLocaleUpperCase("vi");
}

function showToast(message, isError = false) {
  const toast = makeElement("div", `toast${isError ? " toast-error" : ""}`, message);
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
  $$(".nav-link").forEach((link) => {
    const roles = (link.dataset.roles || "").split(",").filter(Boolean);
    link.classList.toggle("hidden", roles.length > 0 && !roles.includes(user.role));
  });
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
  const response = await fetch(path, { ...options, method, headers, credentials: "same-origin" });
  if (response.status === 401 && state.user) showLogin();
  if (!response.ok) {
    let message = `Yêu cầu không thành công (${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((item) => item.msg).join(" ");
    } catch {
      message = `Yêu cầu không thành công (${response.status}).`;
    }
    throw new Error(message);
  }
  if (response.status === 204) return null;
  if (response.headers.get("content-type")?.includes("application/json")) return response.json();
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
    state.user.role === "hr" ? api("/teachers").catch(() => []) : Promise.resolve([]),
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
  if (view === "overview") {
    $("#view-overview").classList.remove("hidden");
    renderOverview();
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
    teacherChecklist: "HR rà soát điều kiện áp dụng theo từng giảng viên; chỉ mục được đánh dấu bắt buộc mới ảnh hưởng trạng thái đầy đủ.",
    departments: "Quản lý cây đơn vị; đơn vị đã tham chiếu được lưu trữ thay vì xóa.",
    qualifications: "Thông tin bằng cấp, chứng chỉ và chuyên môn của giảng viên.",
    contracts: "Theo dõi hợp đồng; cảnh báo không tự gia hạn hay đổi trạng thái.",
    history: "Lịch sử công tác được giữ lại qua các lần thay đổi đã duyệt.",
    documents: "Tệp được lưu riêng, chỉ người có quyền nhân sự mới tải xuống.",
    changes: "Thay đổi quan trọng chỉ cập nhật hồ sơ chính thức sau khi duyệt.",
    checklist: "Checklist có thể cấu hình; tài liệu nhạy cảm không bắt buộc mặc định.",
    reports: "Số liệu thể hiện điều kiện lọc; vai trò quản lý chỉ xem tổng hợp.",
    accounts: "Quản lý tài khoản và vai trò; tài khoản bị khóa được giữ lại để bảo toàn lịch sử và nhật ký.",
    audit: "Nhật ký chỉ đọc, ghi nhận các thao tác quan trọng.",
  };
  return descriptions[view] || "";
}

async function renderOverview() {
  if (state.user.role === "admin") {
    const region = $("#summary-cards");
    region.replaceChildren();
    region.append(makeElement("article", "stat-card", "Quản lý tài khoản và kiểm tra nhật ký trong các mục bên trái."));
    $("#contract-alert-rows").replaceChildren();
    return;
  }
  try {
    const summary = await api("/reports/summary");
    const cards = [
      ["Tổng giảng viên", summary.total_teachers],
      ["Hồ sơ chưa đầy đủ", summary.incomplete_profiles],
      ["Hợp đồng sắp/đã hết hạn", summary.expiring_or_expired_contracts],
      ["Yêu cầu chờ duyệt", summary.change_requests_by_status?.pending || 0],
    ];
    const region = $("#summary-cards");
    region.replaceChildren();
    for (const [label, value] of cards) {
      const card = makeElement("article", "stat-card");
      card.append(makeElement("div", "stat-label", label), makeElement("div", "stat-value", value));
      region.append(card);
    }
    const alertBody = $("#contract-alert-rows");
    alertBody.replaceChildren();
    if (state.user.role === "hr") {
      const alerts = await api("/contracts/alerts");
      for (const alert of alerts) {
        const row = document.createElement("tr");
        [alert.contract_code, alert.teacher_name, alert.ends_on, alert.days_remaining, statusLabels[alert.status] || alert.status]
          .forEach((value) => row.append(makeElement("td", "", value)));
        alertBody.append(row);
      }
    }
    if (!alertBody.children.length) {
      alertBody.append(makeElement("tr", "", ""));
      alertBody.firstElementChild.append(makeElement("td", "", "Không có cảnh báo hoặc bạn không có quyền xem chi tiết."));
    }
  } catch (error) {
    showToast(`Không thể tải tổng quan: ${error.message}`, true);
  }
}

function setTable(headers, rows) {
  const head = $("#workspace-head");
  const body = $("#workspace-rows");
  head.replaceChildren();
  body.replaceChildren();
  const headingRow = document.createElement("tr");
  headers.forEach((header) => headingRow.append(makeElement("th", "", header)));
  head.append(headingRow);
  for (const values of rows) {
    const row = document.createElement("tr");
    values.forEach((value) => {
      const cell = document.createElement("td");
      if (value instanceof Node) cell.append(value);
      else cell.textContent = value === null || value === undefined ? "—" : String(value);
      row.append(cell);
    });
    body.append(row);
  }
  $("#workspace-empty").classList.toggle("hidden", rows.length > 0);
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
    teacherChecklist: renderTeacherChecklist,
    departments: renderDepartments,
    qualifications: renderQualifications,
    contracts: renderContracts,
    history: renderHistory,
    documents: renderDocuments,
    changes: renderChanges,
    checklist: renderChecklist,
    reports: renderReports,
    accounts: renderAccounts,
    audit: renderAudit,
  };
  await renderers[state.currentView]?.();
}

function teacherSelector(onChange, required = true) {
  const label = makeElement("label", "filter-control");
  label.append(makeElement("span", "", "Giảng viên"));
  const select = document.createElement("select");
  select.required = required;
  select.append(new Option("Chọn giảng viên", ""));
  for (const teacher of state.teachers) {
    select.add(new Option(`${teacher.employee_code} — ${teacher.full_name}`, String(teacher.id)));
  }
  select.value = state.selectedTeacherId;
  select.addEventListener("change", () => {
    state.selectedTeacherId = select.value;
    onChange?.();
  });
  label.append(select);
  return select;
}

async function renderTeachers() {
  $("#workspace-actions").append(actionButton("＋ Thêm giảng viên", "add-teacher"));
  const filter = makeElement("input", "workspace-search");
  filter.type = "search";
  filter.placeholder = "Tìm theo tên hoặc mã";
  const departmentFilter = document.createElement("select");
  departmentFilter.append(new Option("Tất cả đơn vị", ""));
  state.departments.forEach((unit) => departmentFilter.add(new Option(unit.name, String(unit.id))));
  const degreeFilter = document.createElement("select");
  degreeFilter.append(new Option("Tất cả trình độ", ""));
  [...new Set(state.teachers.map((teacher) => teacher.academic_degree).filter(Boolean))]
    .sort((left, right) => left.localeCompare(right, "vi"))
    .forEach((degree) => degreeFilter.add(new Option(degree, degree)));
  const statusFilter = document.createElement("select");
  statusFilter.append(new Option("Tất cả trạng thái", ""));
  [["active", "Đang công tác"], ["paused", "Tạm ngừng"], ["ended", "Đã kết thúc"]]
    .forEach(([value, label]) => statusFilter.add(new Option(label, value)));
  $("#workspace-filters").append(filter, departmentFilter, degreeFilter, statusFilter);
  const drawRows = () => {
    const query = filter.value.trim().toLocaleLowerCase("vi");
    const filtered = state.teachers.filter((teacher) =>
      `${teacher.employee_code} ${teacher.full_name}`.toLocaleLowerCase("vi").includes(query) &&
      (!departmentFilter.value || teacher.department_id === Number(departmentFilter.value)) &&
      (!degreeFilter.value || teacher.academic_degree === degreeFilter.value) &&
      (!statusFilter.value || teacher.employment_status === statusFilter.value));
    setTable(
      ["Mã", "Họ tên", "Đơn vị", "Trình độ", "Trạng thái", "Nghiệp vụ", ""],
      filtered.map((teacher) => [
        teacher.employee_code,
        teacher.full_name,
        state.departments.find((item) => item.id === teacher.department_id)?.name || "—",
        teacher.academic_degree || "—",
        statusLabels[teacher.employment_status] || teacher.employment_status,
        actionButton("Bằng cấp", "teacher-detail", teacher.id),
        actionGroup([
          actionButton("Sửa", "edit-teacher", teacher.id),
          actionButton("Checklist", "teacher-checklist", teacher.id),
        ]),
      ]),
    );
  };
  [filter, departmentFilter, degreeFilter, statusFilter].forEach((control) =>
    control.addEventListener("input", drawRows));
  [departmentFilter, degreeFilter, statusFilter].forEach((control) =>
    control.addEventListener("change", drawRows));
  drawRows();
}

async function renderDepartments() {
  if (state.user.role === "hr") {
    $("#workspace-actions").append(actionButton("＋ Thêm đơn vị", "add-department"));
  }
  const rows = state.departments.map((department) => {
    const parent = state.departments.find((item) => item.id === department.parent_id);
    const actions = document.createElement("div");
    if (state.user.role === "hr") {
      actions.append(actionButton("Sửa", "edit-department", department.id));
      if (department.is_active) actions.append(actionButton("Ngừng", "toggle-department", department.id));
      else actions.append(actionButton("Kích hoạt", "toggle-department", department.id));
    }
    return [
      department.code,
      department.name,
      parent?.name || "—",
      department.description || "—",
      department.is_active ? "Đang hoạt động" : "Đã ngừng",
      actions,
    ];
  });
  setTable(["Mã", "Đơn vị", "Đơn vị cha", "Mô tả", "Trạng thái", ""], rows);
}

async function renderQualifications() {
  $("#workspace-filters").append(teacherSelector(() => renderQualifications()));
  const teacherId = state.selectedTeacherId;
  if (!teacherId) return setTable(["Loại", "Tên", "Chuyên ngành", "Cơ sở", "Năm"], []);
  const qualifications = await api(`/teachers/${teacherId}/qualifications`);
  const rows = qualifications.map((item) => [
    item.qualification_type,
    item.title,
    item.specialty || "—",
    item.institution || "—",
    item.issued_year || item.issued_on || "—",
  ]);
  setTable(["Loại", "Tên", "Chuyên ngành", "Cơ sở", "Năm"], rows);
  $("#workspace-form-region").append(buildForm([
    { name: "qualification_type", label: "Loại", type: "select", required: true, options: [["degree", "Bằng cấp"], ["certificate", "Chứng chỉ"], ["research", "Nghiên cứu"], ["other", "Khác"]] },
    { name: "title", label: "Tên văn bằng/chứng chỉ", required: true },
    { name: "specialty", label: "Chuyên ngành" },
    { name: "institution", label: "Cơ sở đào tạo" },
    { name: "issued_year", label: "Năm cấp", type: "number" },
  ], "Thêm bằng cấp hoặc chứng chỉ", async (values) => {
    if (values.issued_year) values.issued_year = Number(values.issued_year);
    await api(`/teachers/${teacherId}/qualifications`, { method: "POST", body: JSON.stringify(values) });
  }));
}

async function renderContracts() {
  $("#workspace-filters").append(teacherSelector(() => renderContracts()));
  state.contractWarningDays = (await api("/settings/contract-warning-days")).days;
  $("#workspace-form-region").append(buildForm([
    { name: "days", label: `Cảnh báo trước bao nhiêu ngày (hiện tại ${state.contractWarningDays})`, type: "number", required: true },
  ], "Cấu hình cảnh báo hợp đồng", async (values) => {
    const days = Number(values.days);
    if (!Number.isInteger(days) || days < 0 || days > 365) throw new Error("Số ngày phải từ 0 đến 365.");
    await api(`/settings/contract-warning-days?days=${days}`, { method: "PUT" });
  }));
  const teacherId = state.selectedTeacherId;
  if (!teacherId) return setTable(["Mã hợp đồng", "Loại", "Bắt đầu", "Kết thúc", "Trạng thái"], []);
  const contracts = await api(`/teachers/${teacherId}/contracts`);
  const rows = contracts.map((item) => [
    item.contract_code,
    item.contract_type,
    item.starts_on,
    item.ends_on || "Không thời hạn",
    statusLabels[item.display_status] || item.display_status,
  ]);
  setTable(["Mã hợp đồng", "Loại", "Bắt đầu", "Kết thúc", "Trạng thái"], rows);
  $("#workspace-form-region").append(buildForm([
    { name: "contract_code", label: "Mã hợp đồng", required: true },
    { name: "contract_type", label: "Loại hợp đồng", required: true },
    { name: "signed_on", label: "Ngày ký", type: "date" },
    { name: "starts_on", label: "Ngày bắt đầu", type: "date", required: true },
    { name: "ends_on", label: "Ngày kết thúc", type: "date" },
  ], "Thêm hợp đồng", async (values) => {
    await api(`/teachers/${teacherId}/contracts`, { method: "POST", body: JSON.stringify(values) });
  }));
}

async function renderHistory() {
  $("#workspace-filters").append(teacherSelector(() => renderHistory()));
  if (!state.selectedTeacherId) return setTable(["Đơn vị", "Chức danh", "Bắt đầu", "Kết thúc", "Lý do"], []);
  const history = await api(`/teachers/${state.selectedTeacherId}/work-history`);
  setTable(
    ["Đơn vị", "Chức danh", "Bắt đầu", "Kết thúc", "Lý do"],
    history.map((item) => [
      state.departments.find((unit) => unit.id === item.department_id)?.name || "—",
      item.position_title || "—",
      item.starts_on,
      item.ends_on || "Hiện tại",
      item.reason || "—",
    ]),
  );
  $("#workspace-form-region").append(buildForm([
    { name: "department_id", label: "Đơn vị", type: "select", required: true, options: state.departments.map((unit) => [String(unit.id), unit.name]) },
    { name: "position_title", label: "Chức danh" },
    { name: "starts_on", label: "Ngày bắt đầu", type: "date", required: true },
    { name: "ends_on", label: "Ngày kết thúc", type: "date" },
    { name: "reason", label: "Lý do" },
  ], "Bổ sung giai đoạn công tác", async (values) => {
    values.department_id = Number(values.department_id);
    await api(`/teachers/${state.selectedTeacherId}/work-history`, {
      method: "POST",
      body: JSON.stringify(values),
    });
  }));
}

async function renderDocuments() {
  $("#workspace-filters").append(teacherSelector(() => renderDocuments()));
  if (!state.selectedTeacherId) return setTable(["Tài liệu", "Dung lượng", "Ngày tải", "Tải xuống"], []);
  const documents = await api(`/teachers/${state.selectedTeacherId}/documents`);
  setTable(
    ["Tài liệu", "Dung lượng", "Ngày tải", "Tải xuống"],
    documents.map((item) => [
      item.original_name,
      `${Math.ceil(item.size_bytes / 1024)} KB`,
      new Date(item.created_at).toLocaleString("vi-VN"),
      actionButton("Tải tệp", "download-document", item.id),
    ]),
  );
  const [checklist, qualifications, contracts] = await Promise.all([
    api("/checklist-items"),
    api(`/teachers/${state.selectedTeacherId}/qualifications`),
    api(`/teachers/${state.selectedTeacherId}/contracts`),
  ]);
  const form = document.createElement("form");
  form.className = "inline-form";
  form.append(makeElement("strong", "", "Tải minh chứng"));
  const file = document.createElement("input");
  file.type = "file";
  file.name = "file";
  file.accept = ".pdf,.png,.jpg,.jpeg";
  file.required = true;
  form.append(file);
  const select = document.createElement("select");
  select.name = "checklist_item_id";
  select.append(new Option("Không gắn checklist", ""));
  checklist.filter((item) => item.is_active).forEach((item) => select.add(new Option(item.label, String(item.id))));
  form.append(select);
  const qualificationSelect = document.createElement("select");
  qualificationSelect.append(new Option("Không gắn bằng cấp", ""));
  qualifications.forEach((item) => qualificationSelect.add(new Option(item.title, String(item.id))));
  const contractSelect = document.createElement("select");
  contractSelect.append(new Option("Không gắn hợp đồng", ""));
  contracts.forEach((item) => contractSelect.add(new Option(item.contract_code, String(item.id))));
  qualificationSelect.addEventListener("change", () => {
    contractSelect.disabled = Boolean(qualificationSelect.value);
  });
  contractSelect.addEventListener("change", () => {
    qualificationSelect.disabled = Boolean(contractSelect.value);
  });
  form.append(qualificationSelect, contractSelect);
  const submit = makeElement("button", "button button-primary", "Tải lên");
  submit.type = "submit";
  form.append(submit);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData();
    data.append("file", file.files[0]);
    if (select.value) data.append("checklist_item_id", select.value);
    if (qualificationSelect.value) data.append("qualification_id", qualificationSelect.value);
    if (contractSelect.value) data.append("contract_id", contractSelect.value);
    try {
      await api(`/teachers/${state.selectedTeacherId}/documents`, { method: "POST", body: data });
      showToast("Đã tải tài liệu lên.");
      await renderDocuments();
    } catch (error) {
      showToast(error.message, true);
    }
  });
  $("#workspace-form-region").append(form);
}

async function renderChanges() {
  const requests = await api("/change-requests");
  setTable(
    ["ID", "Giảng viên", "Loại", "Hiện tại", "Đề xuất", "Lý do", "Trạng thái", "Thao tác"],
    requests.map((item) => {
      const actions = document.createElement("div");
      if (state.user.role === "manager" && item.status === "pending") {
        actions.append(actionButton("Duyệt", "decide-change", item.id));
        actions.append(actionButton("Từ chối", "reject-change", item.id));
        actions.append(actionButton("Yêu cầu bổ sung", "request-info", item.id));
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
        statusLabels[item.status] || item.status,
        actions,
      ];
    }),
  );
  if (state.user.role === "hr") {
    const teacherSelect = document.createElement("select");
    teacherSelect.required = true;
    teacherSelect.append(new Option("Chọn giảng viên", ""));
    state.teachers.forEach((teacher) => teacherSelect.add(new Option(`${teacher.employee_code} — ${teacher.full_name}`, String(teacher.id))));
    const type = inputField({ name: "change_type", label: "Loại thay đổi", required: true });
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
    const proposed = inputField({ name: "proposed", label: "Giá trị đề xuất", required: true });
    const reason = inputField({ name: "reason", label: "Lý do", required: true });
    const effective = inputField({ name: "effective_on", label: "Ngày có hiệu lực", type: "date" });
    const form = document.createElement("form");
    form.className = "inline-form";
    form.append(makeElement("strong", "", "Tạo yêu cầu thay đổi"), teacherSelect, type, field, proposed, reason, effective);
    const submit = makeElement("button", "button button-primary", "Gửi yêu cầu");
    submit.type = "submit";
    form.append(submit);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const fieldName = field.value;
      const value = ["department_id"].includes(fieldName) ? Number(proposed.value) : proposed.value;
      const current = state.teachers.find((teacher) => teacher.id === Number(teacherSelect.value));
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

async function renderChecklist() {
  const items = await api("/checklist-items");
  setTable(
    ["Mã", "Tài liệu", "Nhóm", "Phân loại", "Điều kiện áp dụng", "Nhạy cảm", "Trạng thái", "Thao tác"],
    items.map((item) => [
      item.code,
      item.label,
      item.category,
      checklistClassifications[item.classification] || item.classification,
      item.applicability || "—",
      item.is_sensitive ? "Có" : "Không",
      item.is_active ? "Đang dùng" : "Đã ngừng",
      actionGroup([
        actionButton("Sửa điều kiện", "edit-checklist-item", item.id),
        actionButton(item.is_active ? "Ngừng" : "Kích hoạt", "toggle-checklist-active", item.id),
      ]),
    ]),
  );
  $("#workspace-form-region").append(buildForm([
    { name: "code", label: "Mã mục (chữ thường, số, gạch ngang)", required: true },
    { name: "label", label: "Tên trường/tài liệu", required: true },
    { name: "category", label: "Nhóm", required: true },
    {
      name: "classification",
      label: "Phân loại trong danh mục",
      type: "select",
      required: true,
      options: [["required", "Bắt buộc"], ["conditional", "Có điều kiện"], ["optional", "Tùy chọn"]],
    },
    { name: "applicability", label: "Điều kiện áp dụng (tối đa 500 ký tự)" },
    { name: "is_sensitive", label: "Dữ liệu nhạy cảm", type: "checkbox" },
  ], "Thêm mục checklist", async (values) => {
    values.is_sensitive = Boolean(values.is_sensitive);
    await api("/checklist-items", { method: "POST", body: JSON.stringify(values) });
  }));
}

async function renderTeacherChecklist() {
  const teacherId = Number(state.selectedTeacherId);
  const teacher = state.teachers.find((item) => item.id === teacherId);
  if (!teacher) {
    showToast("Không tìm thấy giảng viên được chọn.", true);
    navigate("teachers");
    return;
  }
  const [requirements, completeness] = await Promise.all([
    api(`/teachers/${teacherId}/checklist-requirements`),
    api(`/teachers/${teacherId}/completeness`),
  ]);
  const summary = makeElement(
    "p",
    "page-subtitle",
    `${teacher.employee_code} — ${teacher.full_name}. ` +
      (completeness.is_complete
        ? "Hồ sơ đầy đủ theo các yêu cầu đã rà soát."
        : `Còn thiếu: ${completeness.missing.join(", ") || "không có"}. ` +
          `Cần rà soát điều kiện: ${completeness.needs_review.join(", ") || "không có"}.`),
  );
  $("#workspace-form-region").append(summary);
  setTable(
    ["Tài liệu", "Nhóm", "Phân loại", "Điều kiện áp dụng", "Yêu cầu với giảng viên", "Minh chứng"],
    requirements.map((item) => {
      const select = document.createElement("select");
      select.dataset.itemId = String(item.item_id);
      for (const [value, label] of Object.entries(checklistRequirementStatuses)) {
        select.add(new Option(label, value));
      }
      select.value = item.status;
      const evidence = makeElement(
        "span",
        "",
        item.status === "required" && completeness.missing.includes(item.label)
          ? "Chưa tải lên"
          : item.status === "required"
            ? "Đã có"
            : "—",
      );
      return [
        item.label,
        item.category,
        checklistClassifications[item.classification] || item.classification,
        item.applicability || "—",
        select,
        evidence,
      ];
    }),
  );
  const backButton = makeElement("button", "row-action", "Quay lại danh sách");
  backButton.type = "button";
  backButton.addEventListener("click", () => navigate("teachers"));
  $("#workspace-actions").append(backButton);
  $$("#workspace-rows select").forEach((select) => {
    select.addEventListener("change", async () => {
      try {
        await api(`/teachers/${teacherId}/checklist-requirements/${select.dataset.itemId}`, {
          method: "PATCH",
          body: JSON.stringify({ status: select.value }),
        });
        await renderTeacherChecklist();
      } catch (error) {
        showToast(error.message, true);
        await renderTeacherChecklist();
      }
    });
  });
}

async function renderReports() {
  const departments = await api("/departments");
  const department = document.createElement("select");
  department.append(new Option("Tất cả đơn vị", ""));
  departments.forEach((item) => department.add(new Option(item.name, String(item.id))));
  const start = inputField({ name: "start_date", label: "Từ ngày", type: "date" });
  const end = inputField({ name: "end_date", label: "Đến ngày", type: "date" });
  const form = document.createElement("form");
  form.className = "inline-form";
  form.append(makeElement("strong", "", "Điều kiện lọc"), department, start, end);
  const run = makeElement("button", "button button-primary", "Tạo báo cáo");
  run.type = "submit";
  const exportButton = makeElement("button", "button button-secondary", "Xuất Excel");
  exportButton.type = "button";
  form.append(run, exportButton);
  const query = () => {
    const params = new URLSearchParams();
    if (department.value) params.set("department_id", department.value);
    if (start.value) params.set("start_date", start.value);
    if (end.value) params.set("end_date", end.value);
    return params.toString();
  };
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const summary = await api(`/reports/summary?${query()}`);
    setTable(
      ["Chỉ số", "Giá trị"],
      [
        ["Tổng giảng viên", summary.total_teachers],
        ["Hồ sơ chưa đầy đủ", summary.incomplete_profiles],
        ["Hợp đồng sắp/đã hết hạn", summary.expiring_or_expired_contracts],
        ["Điều kiện lọc", JSON.stringify(summary.filters)],
        ...Object.entries(summary.teachers_by_department).map(([name, count]) => [`Đơn vị: ${name}`, count]),
        ...Object.entries(summary.teachers_by_degree).map(([name, count]) => [`Trình độ: ${name}`, count]),
        ...Object.entries(summary.teachers_by_status).map(([name, count]) => [`Trạng thái: ${name}`, count]),
      ],
    );
  });
  exportButton.addEventListener("click", async () => {
    try {
      const response = await api(`/reports/export.xlsx?${query()}`);
      const link = document.createElement("a");
      link.href = URL.createObjectURL(await response.blob());
      link.download = "teacher_report.xlsx";
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (error) {
      showToast(error.message, true);
    }
  });
  $("#workspace-filters").append(form);
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
    ["Quản trị viên", activeUsers.filter((user) => user.role === "admin").length],
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
  const username = inputField({ name: "username", label: "Tên tài khoản", required: true });
  username.querySelector("input").maxLength = 80;
  username.querySelector("input").autocomplete = "off";
  const fullName = inputField({ name: "full_name", label: "Họ tên", required: true });
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
  const createButton = makeElement("button", "button button-primary", "Tạo tài khoản");
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
    const filtered = users.filter((user) =>
      `${user.username} ${user.full_name} ${roleLabels[user.role] || user.role}`
        .toLocaleLowerCase("vi")
        .includes(query)
      && (!roleFilter.value || user.role === roleFilter.value)
      && (!statusFilter.value || user.is_active === (statusFilter.value === "active")),
    );
    setTable(
      ["Tên tài khoản", "Họ tên", "Vai trò", "Trạng thái", "Tạo lúc", "Thao tác"],
      filtered.map((user) => [
        user.username,
        user.full_name,
        roleLabels[user.role] || user.role,
        user.is_active ? "Đang hoạt động" : "Đã khóa",
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
  $("#account-modal-title").textContent = `Chỉnh sửa tài khoản ${user.username}`;
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
  return actionGroup([edit, toggle]);
}

async function renderAudit() {
  const actorId = inputField({ name: "actor_id", label: "Tài khoản ID", type: "number" });
  const action = inputField({ name: "action", label: "Thao tác" });
  const start = inputField({ name: "start_date", label: "Từ ngày", type: "date" });
  const end = inputField({ name: "end_date", label: "Đến ngày", type: "date" });
  const form = document.createElement("form");
  form.className = "inline-form";
  form.append(makeElement("strong", "", "Lọc nhật ký"), actorId, action, start, end);
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
        ["Thời gian", "Tài khoản ID", "Thao tác", "Đối tượng", "ID", "Kết quả", "Chi tiết"],
        entries.map((item) => [
          new Date(item.created_at).toLocaleString("vi-VN"),
          item.actor_id || "—",
          item.action,
          item.entity_type,
          item.entity_id || "—",
          item.outcome,
          JSON.stringify(item.details || {}),
        ]),
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
    config.options.forEach(([value, label]) => input.add(new Option(label, value)));
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

function buildForm(fields, title, onSubmit) {
  const form = document.createElement("form");
  form.className = "inline-form";
  form.append(makeElement("strong", "", title));
  const controls = new Map();
  for (const config of fields) {
    const wrapper = inputField(config);
    controls.set(config.name, wrapper.querySelector(`[name="${config.name}"]`));
    form.append(wrapper);
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
  state.departments.filter((item) => item.is_active).forEach((item) => select.add(new Option(item.name, String(item.id))));
  select.value = selectedValue ? String(selectedValue) : "";
}

function openTeacherModal(teacher = null) {
  const form = $("#teacher-form");
  form.reset();
  clearError($("#form-error"));
  const departmentSelect = form.elements.department_id;
  populateDepartmentSelect(departmentSelect, teacher?.department_id);
  $("#modal-title").textContent = teacher ? "Chỉnh sửa hồ sơ" : "Thêm giảng viên";
  $("#teacher-submit").textContent = teacher ? "Lưu thay đổi" : "Lưu hồ sơ";
  form.elements.teacher_id.value = teacher?.id || "";
  if (teacher) {
    for (const [key, value] of Object.entries(teacher)) {
      if (form.elements[key]) form.elements[key].value = value ?? "";
    }
    for (const key of ["department_id", "employment_status", "academic_degree", "academic_title"]) {
      form.elements[key].disabled = true;
    }
    showToast("Đơn vị, trạng thái, trình độ và chức danh chỉ đổi qua yêu cầu phê duyệt.");
  } else {
    for (const key of ["department_id", "employment_status", "academic_degree", "academic_title"]) {
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
  $("#department-modal-title").textContent = department ? "Chỉnh sửa đơn vị" : "Thêm đơn vị";
  const parent = form.elements.parent_id;
  parent.replaceChildren(new Option("Không có", ""));
  state.departments.filter((item) => item.is_active && item.id !== department?.id)
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
        body: JSON.stringify({ username: data.get("username"), password: data.get("password") }),
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
  $$(".nav-link").forEach((button) => button.addEventListener("click", () => navigate(button.dataset.view)));
  $("#mobile-menu").addEventListener("click", () => $("#sidebar").classList.toggle("open"));
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
  $("#department-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const id = data.get("department_id");
    const payload = Object.fromEntries([...data.entries()].filter(([key, value]) => key !== "department_id" && value !== ""));
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
  $("#department-modal-close").addEventListener("click", () => $("#department-backdrop").classList.add("hidden"));
  $("#department-modal-cancel").addEventListener("click", () => $("#department-backdrop").classList.add("hidden"));

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
          await navigate("qualifications");
          break;
        case "teacher-checklist":
          state.selectedTeacherId = String(id);
          await navigate("teacherChecklist");
          break;
        case "teacher-completeness": {
          const result = await api(`/teachers/${id}/completeness`);
          const review = result.needs_review.length
            ? ` Cần rà soát điều kiện: ${result.needs_review.join(", ")}.`
            : "";
          showToast(
            result.is_complete
              ? "Hồ sơ đầy đủ theo các yêu cầu đã rà soát."
              : `Còn thiếu: ${result.missing.join(", ") || "không có"}.${review}`,
            !result.is_complete,
          );
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
              action: button.dataset.action === "reject-change" ? "reject" : "request_info",
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
          const items = await api("/checklist-items");
          const item = items.find((entry) => entry.id === id);
          const classification = window.prompt(
            "Phân loại: required, conditional hoặc optional",
            item?.classification || "conditional",
          );
          if (!classification || !["required", "conditional", "optional"].includes(classification)) break;
          const applicability = window.prompt("Điều kiện áp dụng", item?.applicability || "");
          if (applicability === null) break;
          await api(`/checklist-items/${id}`, {
            method: "PATCH",
            body: JSON.stringify({ classification, applicability }),
          });
          await renderWorkspace();
          break;
        }
        case "toggle-checklist-active": {
          const items = await api("/checklist-items");
          const item = items.find((entry) => entry.id === id);
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
            user.is_active
            && !window.confirm(`Khóa tài khoản "${user.username}"?`)
          ) break;
          await updateAccount(id, { is_active: !user.is_active });
          showToast(user.is_active ? "Đã khóa tài khoản." : "Đã mở khóa tài khoản.");
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

async function initialize() {
  $("#today-date").textContent = new Date().toLocaleDateString("vi-VN", {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  });
  $("#footer-year").textContent = String(new Date().getFullYear());
  $$('input[type="password"]').forEach(addPasswordToggle);
  bindEvents();
  try {
    const user = await api("/auth/session");
    showApp(user);
  } catch {
    showLogin();
  }
}

initialize();

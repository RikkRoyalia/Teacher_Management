const state = {
  teachers: [],
  departments: [],
  currentView: "overview",
  searchTimer: null,
};

const viewTitles = {
  overview: "Tổng quan",
  teachers: "Giảng viên",
  departments: "Khoa & bộ môn",
};

const statusLabels = {
  active: "Đang công tác",
  paused: "Tạm ngừng",
  ended: "Đã kết thúc",
};

const avatarColors = [
  ["#eeeaff", "#6959d2"],
  ["#e8f6f0", "#38896f"],
  ["#eaf2ff", "#4b79c2"],
  ["#fff2e4", "#b27a33"],
  ["#fcecf2", "#b35f7b"],
];

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function initials(name = "") {
  return name
    .trim()
    .split(/\s+/)
    .slice(-2)
    .map((part) => Array.from(part)[0] || "")
    .join("")
    .toLocaleUpperCase("vi");
}

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function departmentName(id) {
  return state.departments.find((department) => department.id === id)?.name || "Chưa xác định";
}

function statusBadge(status) {
  const badge = makeElement("span", `status-badge status-${status}`, statusLabels[status] || status);
  return badge;
}

function teacherIdentity(teacher) {
  const wrapper = makeElement("div", "teacher-cell");
  const avatar = makeElement("span", "teacher-avatar", initials(teacher.full_name));
  const color = avatarColors[teacher.id % avatarColors.length];
  avatar.style.backgroundColor = color[0];
  avatar.style.color = color[1];
  const name = makeElement("span", "teacher-name");
  name.append(makeElement("strong", "", teacher.full_name));
  name.append(makeElement("small", "", teacher.email || teacher.phone || "Chưa cập nhật liên hệ"));
  wrapper.append(avatar, name);
  return wrapper;
}

function tableCell(content) {
  const cell = document.createElement("td");
  if (content instanceof Node) cell.append(content);
  else cell.textContent = content ?? "—";
  return cell;
}

function actionButton(label, action, id) {
  const button = makeElement("button", "row-action", label);
  button.type = "button";
  button.dataset.action = action;
  button.dataset.id = String(id);
  return button;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    let message = `Yêu cầu không thành công (${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) {
        message = body.detail.map((item) => item.msg).join(" ");
      }
    } catch {
      // Keep the HTTP status message when the server does not return JSON.
    }
    throw new Error(message);
  }
  if (response.status === 204) return null;
  return response.json();
}

function showToast(message, isError = false) {
  const toast = makeElement("div", `toast${isError ? " toast-error" : ""}`, message);
  $("#toast-region").append(toast);
  window.setTimeout(() => toast.remove(), 4000);
}

function showError(target, message) {
  target.textContent = message;
  target.classList.remove("hidden");
}

function clearError(target) {
  target.textContent = "";
  target.classList.add("hidden");
}

function navigate(view) {
  if (!viewTitles[view]) return;
  state.currentView = view;
  $$(".view-section").forEach((section) => section.classList.add("hidden"));
  $(`#view-${view}`).classList.remove("hidden");
  $$(".nav-link").forEach((link) => {
    const active = link.dataset.view === view;
    link.classList.toggle("active", active);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  $("#breadcrumb-current").textContent = viewTitles[view];
  $("#sidebar").classList.remove("open");
  if (view === "teachers") renderTeachers();
  if (view === "departments") renderDepartments();
}

function populateDepartmentOptions(keepDepartmentId = null) {
  const filter = $("#filter-department");
  const selectedFilter = filter.value;
  filter.replaceChildren(new Option("Tất cả khoa / bộ môn", ""));
  for (const department of state.departments.filter((item) => item.is_active)) {
    filter.add(new Option(department.name, String(department.id)));
  }
  filter.value = selectedFilter;

  const formSelect = $('#teacher-form select[name="department_id"]');
  const selectedDepartment = formSelect.value;
  formSelect.replaceChildren(new Option("Chọn đơn vị", ""));
  for (const department of state.departments.filter((item) => item.is_active || item.id === keepDepartmentId)) {
    formSelect.add(new Option(`${department.name} (${department.code})`, String(department.id)));
  }
  formSelect.value = selectedDepartment;
}

function populateDegreeOptions() {
  const filter = $("#filter-degree");
  const selected = filter.value;
  const degrees = [...new Set(state.teachers.map((teacher) => teacher.academic_degree).filter(Boolean))]
    .sort((a, b) => a.localeCompare(b, "vi"));
  filter.replaceChildren(new Option("Tất cả trình độ", ""));
  for (const degree of degrees) filter.add(new Option(degree, degree));
  filter.value = selected;
}

function renderOverview() {
  const activeTeachers = state.teachers.filter((teacher) => teacher.employment_status === "active").length;
  const pausedTeachers = state.teachers.filter((teacher) => teacher.employment_status === "paused").length;
  $("#stat-total").textContent = String(state.teachers.length);
  $("#stat-active").textContent = String(activeTeachers);
  $("#stat-paused").textContent = String(pausedTeachers);
  $("#stat-departments").textContent = String(state.departments.filter((item) => item.is_active).length);

  const counts = state.departments
    .filter((department) => department.is_active)
    .map((department) => ({
      name: department.name,
      count: state.teachers.filter((teacher) => teacher.department_id === department.id).length,
    }))
    .sort((left, right) => right.count - left.count || left.name.localeCompare(right.name, "vi"))
    .slice(0, 5);
  const chart = $("#department-chart");
  chart.replaceChildren();
  if (!counts.length) {
    chart.append(makeElement("p", "chart-empty", "Chưa có dữ liệu đơn vị."));
  } else {
    const max = Math.max(...counts.map((item) => item.count), 1);
    for (const item of counts) {
      const row = makeElement("div", "chart-row");
      row.append(makeElement("span", "chart-name", item.name));
      const track = makeElement("span", "chart-track");
      const bar = makeElement("span", "chart-bar");
      bar.style.width = `${Math.max(item.count ? (item.count / max) * 100 : 0, 0)}%`;
      track.append(bar);
      row.append(track, makeElement("span", "chart-count", String(item.count)));
      chart.append(row);
    }
  }

  const body = $("#recent-teachers");
  body.replaceChildren();
  const recent = [...state.teachers].slice(0, 5);
  if (!recent.length) {
    const row = document.createElement("tr");
    row.append(tableCell("Chưa có hồ sơ giảng viên."));
    body.append(row);
    return;
  }
  for (const teacher of recent) {
    const row = document.createElement("tr");
    row.append(tableCell(teacherIdentity(teacher)));
    row.append(tableCell(makeElement("span", "code-pill", teacher.employee_code)));
    row.append(tableCell(departmentName(teacher.department_id)));
    row.append(tableCell(teacher.academic_degree || "—"));
    row.append(tableCell(statusBadge(teacher.employment_status)));
    row.append(tableCell(actionButton("Chi tiết", "edit-teacher", teacher.id)));
    body.append(row);
  }
}

function filteredTeachers() {
  const search = $("#teacher-search").value.trim().toLocaleLowerCase("vi");
  const departmentId = $("#filter-department").value;
  const degree = $("#filter-degree").value;
  const status = $("#filter-status").value;
  return state.teachers.filter((teacher) => {
    const matchesSearch = !search ||
      teacher.full_name.toLocaleLowerCase("vi").includes(search) ||
      teacher.employee_code.toLocaleLowerCase("vi").includes(search);
    return matchesSearch &&
      (!departmentId || teacher.department_id === Number(departmentId)) &&
      (!degree || teacher.academic_degree === degree) &&
      (!status || teacher.employment_status === status);
  });
}

function renderTeachers() {
  const teachers = filteredTeachers();
  const body = $("#teacher-rows");
  body.replaceChildren();
  $("#teacher-count").textContent = `${teachers.length} hồ sơ`;
  $("#teacher-empty").classList.toggle("hidden", teachers.length > 0);
  $(".table-meta").classList.toggle("hidden", teachers.length === 0);
  $(".directory-panel .table-wrap", $("#view-teachers")).classList.toggle("hidden", teachers.length === 0);

  for (const teacher of teachers) {
    const row = document.createElement("tr");
    row.append(tableCell(teacherIdentity(teacher)));
    row.append(tableCell(makeElement("span", "code-pill", teacher.employee_code)));
    row.append(tableCell(departmentName(teacher.department_id)));
    row.append(tableCell(teacher.academic_degree || "—"));
    row.append(tableCell(teacher.phone || teacher.email || "—"));
    row.append(tableCell(statusBadge(teacher.employment_status)));
    row.append(tableCell(actionButton("Chỉnh sửa", "edit-teacher", teacher.id)));
    body.append(row);
  }
}

function renderDepartments() {
  const showInactive = $("#show-inactive").checked;
  const departments = state.departments.filter((department) => showInactive || department.is_active);
  const body = $("#department-rows");
  body.replaceChildren();
  $("#department-empty").classList.toggle("hidden", departments.length > 0);
  $(".directory-panel .table-wrap", $("#view-departments")).classList.toggle("hidden", departments.length === 0);
  for (const department of departments) {
    const teacherCount = state.teachers.filter((teacher) => teacher.department_id === department.id).length;
    const row = document.createElement("tr");
    row.append(tableCell(makeElement("span", "code-pill", department.code)));
    row.append(tableCell(makeElement("strong", "department-name-cell", department.name)));
    row.append(tableCell(department.description || "—"));
    row.append(tableCell(String(teacherCount)));
    row.append(tableCell(makeElement(
      "span",
      `status-badge ${department.is_active ? "status-active" : "status-ended"}`,
      department.is_active ? "Đang hoạt động" : "Đã ngừng",
    )));

    const actions = document.createElement("td");
    actions.append(actionButton("Chỉnh sửa", "edit-department", department.id));
    if (department.is_active) {
      const deactivate = actionButton("Ngừng", "deactivate-department", department.id);
      deactivate.classList.add("subtle-action");
      actions.append(deactivate);
    } else {
      actions.append(actionButton("Kích hoạt", "activate-department", department.id));
    }
    row.append(actions);
    body.append(row);
  }
}

async function refreshData() {
  try {
    const [departments, teachers] = await Promise.all([
      api("/departments?include_inactive=true"),
      api("/teachers"),
    ]);
    state.departments = departments;
    state.teachers = teachers;
    populateDepartmentOptions();
    populateDegreeOptions();
    renderOverview();
    renderTeachers();
    renderDepartments();
  } catch (error) {
    showToast(`Không thể tải dữ liệu: ${error.message}`, true);
    $("#department-chart").replaceChildren(makeElement("p", "chart-empty", "Không thể tải dữ liệu."));
    $("#recent-teachers").replaceChildren();
    $("#teacher-rows").replaceChildren();
    $("#department-rows").replaceChildren();
  }
}

function openTeacherModal(teacher = null) {
  const form = $("#teacher-form");
  form.reset();
  clearError($("#form-error"));
  populateDepartmentOptions(teacher?.department_id ?? null);
  $("#modal-title").textContent = teacher ? "Chỉnh sửa hồ sơ" : "Thêm giảng viên";
  $("#teacher-submit").textContent = teacher ? "Lưu thay đổi" : "Lưu hồ sơ";
  form.elements.teacher_id.value = teacher?.id ?? "";
  if (teacher) {
    for (const [key, value] of Object.entries(teacher)) {
      if (form.elements[key]) form.elements[key].value = value ?? "";
    }
  }
  $("#modal-backdrop").classList.remove("hidden");
  form.elements.employee_code.focus();
}

function closeTeacherModal() {
  $("#modal-backdrop").classList.add("hidden");
}

async function submitTeacher(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const formData = new FormData(form);
  const teacherId = formData.get("teacher_id");
  const payload = {};
  for (const [key, value] of formData.entries()) {
    if (key === "teacher_id") continue;
    if (key === "department_id" && value !== "") {
      payload[key] = Number(value);
    } else {
      payload[key] = value === "" ? null : value;
    }
  }
  const button = $("#teacher-submit");
  button.disabled = true;
  button.textContent = "Đang lưu...";
  clearError($("#form-error"));
  try {
    await api(teacherId ? `/teachers/${teacherId}` : "/teachers", {
      method: teacherId ? "PATCH" : "POST",
      body: JSON.stringify(payload),
    });
    closeTeacherModal();
    await refreshData();
    showToast(teacherId ? "Hồ sơ đã được cập nhật." : "Đã tạo hồ sơ giảng viên.");
  } catch (error) {
    showError($("#form-error"), error.message);
  } finally {
    button.disabled = false;
    button.textContent = teacherId ? "Lưu thay đổi" : "Lưu hồ sơ";
  }
}

function openDepartmentModal(department = null) {
  const form = $("#department-form");
  form.reset();
  clearError($("#department-form-error"));
  $("#department-modal-title").textContent = department ? "Chỉnh sửa đơn vị" : "Thêm đơn vị";
  $("#department-submit").textContent = department ? "Lưu thay đổi" : "Lưu đơn vị";
  form.elements.department_id.value = department?.id ?? "";
  if (department) {
    form.elements.code.value = department.code;
    form.elements.name.value = department.name;
    form.elements.description.value = department.description || "";
  }
  $("#department-backdrop").classList.remove("hidden");
  form.elements.code.focus();
}

function closeDepartmentModal() {
  $("#department-backdrop").classList.add("hidden");
}

async function submitDepartment(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const formData = new FormData(form);
  const departmentId = formData.get("department_id");
  const payload = {
    code: formData.get("code").trim(),
    name: formData.get("name").trim(),
    description: formData.get("description").trim() || null,
  };
  const button = $("#department-submit");
  button.disabled = true;
  button.textContent = "Đang lưu...";
  clearError($("#department-form-error"));
  try {
    await api(departmentId ? `/departments/${departmentId}` : "/departments", {
      method: departmentId ? "PATCH" : "POST",
      body: JSON.stringify(payload),
    });
    closeDepartmentModal();
    await refreshData();
    showToast(departmentId ? "Đơn vị đã được cập nhật." : "Đã tạo đơn vị mới.");
  } catch (error) {
    showError($("#department-form-error"), error.message);
  } finally {
    button.disabled = false;
    button.textContent = departmentId ? "Lưu thay đổi" : "Lưu đơn vị";
  }
}

async function deactivateDepartment(id) {
  const department = state.departments.find((item) => item.id === id);
  if (!department || !window.confirm(`Ngừng hoạt động đơn vị "${department.name}"? Đơn vị vẫn được lưu trong hệ thống.`)) return;
  await setDepartmentStatus(id, false);
}

async function setDepartmentStatus(id, isActive) {
  try {
    await api(`/departments/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive }),
    });
    await refreshData();
    showToast(isActive ? "Đơn vị đã được kích hoạt lại." : "Đơn vị đã được chuyển sang trạng thái ngừng hoạt động.");
  } catch (error) {
    showToast(`Không thể cập nhật đơn vị: ${error.message}`, true);
  }
}

document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-action], [data-navigate]");
  if (!target) return;
  if (target.dataset.view || target.dataset.navigate) {
    navigate(target.dataset.view || target.dataset.navigate);
    return;
  }
  const id = Number(target.dataset.id);
  switch (target.dataset.action) {
    case "add-teacher":
      if (!state.departments.some((department) => department.is_active)) {
        showToast("Hãy thêm ít nhất một đơn vị đang hoạt động trước.", true);
        navigate("departments");
        return;
      }
      openTeacherModal();
      break;
    case "edit-teacher":
      openTeacherModal(state.teachers.find((teacher) => teacher.id === id));
      break;
    case "add-department":
      openDepartmentModal();
      break;
    case "edit-department":
      openDepartmentModal(state.departments.find((department) => department.id === id));
      break;
    case "deactivate-department":
      deactivateDepartment(id);
      break;
    case "activate-department":
      setDepartmentStatus(id, true);
      break;
    default:
      break;
  }
});

$$(".nav-link").forEach((link) => {
  link.addEventListener("click", () => navigate(link.dataset.view));
});

$("#teacher-form").addEventListener("submit", submitTeacher);
$("#department-form").addEventListener("submit", submitDepartment);
$("#modal-close").addEventListener("click", closeTeacherModal);
$("#modal-cancel").addEventListener("click", closeTeacherModal);
$("#department-modal-close").addEventListener("click", closeDepartmentModal);
$("#department-modal-cancel").addEventListener("click", closeDepartmentModal);
$("#modal-backdrop").addEventListener("click", (event) => {
  if (event.target === event.currentTarget) closeTeacherModal();
});
$("#department-backdrop").addEventListener("click", (event) => {
  if (event.target === event.currentTarget) closeDepartmentModal();
});
$("#teacher-search").addEventListener("input", () => {
  window.clearTimeout(state.searchTimer);
  state.searchTimer = window.setTimeout(renderTeachers, 120);
});
["#filter-department", "#filter-degree", "#filter-status"].forEach((selector) => {
  $(selector).addEventListener("change", renderTeachers);
});
$("#clear-filters").addEventListener("click", () => {
  $("#teacher-search").value = "";
  $("#filter-department").value = "";
  $("#filter-degree").value = "";
  $("#filter-status").value = "";
  renderTeachers();
});
$("#show-inactive").addEventListener("change", renderDepartments);
$("#mobile-menu").addEventListener("click", () => $("#sidebar").classList.toggle("open"));
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeTeacherModal();
    closeDepartmentModal();
    $("#sidebar").classList.remove("open");
  }
});

const now = new Date();
$("#today-date").textContent = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
}).format(now);
$("#footer-year").textContent = String(now.getFullYear());

refreshData();

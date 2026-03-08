const resourceDict = {
	zh: {
		title: "资源管理",
		sub: "集中查看教案与习题，可发布给班级或按正确率筛选发布。",
		refresh: "刷新",
		type: "类型",
		typeAll: "全部",
		typeLesson: "教案",
		typeExercise: "习题",
		keyword: "关键词",
		sort: "排序",
		sortNew: "最新优先",
		sortOld: "最早优先",
		apply: "应用",
		listTitle: "历史记录",
		delete: "删除",
		publish: "发布",
		empty: "选择左侧资源查看详情",
		publishTitle: "发布资源",
		class: "班级",
		mode: "发布方式",
		modeAll: "全班",
		modeAcc: "按正确率筛选",
		modeManual: "手动选择",
		modeMixed: "正确率筛选 + 手动调整",
		accuracy: "正确率",
		applyAcc: "筛选",
		students: "学生",
		cancel: "取消",
		confirm: "确认发布",
		noData: "暂无记录",
		deleteConfirm: "确定删除该资源？",
		deleteOk: "已删除",
		publishOk: "已发布",
		publishEmpty: "请选择发布学生",
		loadFail: "加载失败",
		selectClass: "请选择班级"
	},
	en: {
		title: "Resource Manager",
		sub: "View lessons and exercises, publish to classes or by accuracy filters.",
		refresh: "Refresh",
		type: "Type",
		typeAll: "All",
		typeLesson: "Lesson",
		typeExercise: "Exercise",
		keyword: "Keyword",
		sort: "Sort",
		sortNew: "Newest",
		sortOld: "Oldest",
		apply: "Apply",
		listTitle: "History",
		delete: "Delete",
		publish: "Publish",
		empty: "Select a resource to preview",
		publishTitle: "Publish Resource",
		class: "Class",
		mode: "Publish mode",
		modeAll: "All students",
		modeAcc: "By accuracy",
		modeManual: "Manual select",
		modeMixed: "Accuracy + manual",
		accuracy: "Accuracy",
		applyAcc: "Apply",
		students: "Students",
		cancel: "Cancel",
		confirm: "Confirm",
		noData: "No records",
		deleteConfirm: "Delete this resource?",
		deleteOk: "Deleted",
		publishOk: "Published",
		publishEmpty: "Please select students",
		loadFail: "Load failed",
		selectClass: "Please select a class"
	}
};

const API_BASE = "http://127.0.0.1:5000";

const state = {
	list: [],
	filtered: [],
	selected: null,
	classes: [],
	students: [],
	selectedStudentIds: new Set()
};

function getLocale() {
	return localStorage.getItem("locale") || "zh";
}

function t(key) {
	return resourceDict[getLocale()][key] || key;
}

function applyResourceLang() {
	document.querySelectorAll("[data-i18n-page]").forEach(el => {
		const key = el.getAttribute("data-i18n-page");
		if (resourceDict[getLocale()][key]) el.textContent = resourceDict[getLocale()][key];
	});
}

function getToken() {
	return localStorage.getItem("auth_token") || "";
}

function getLoginUser() {
	try {
		return JSON.parse(localStorage.getItem("login_user") || "{}");
	} catch {
		return {};
	}
}

function parseTime(s) {
	const d = new Date(s.replace(/-/g, "/"));
	return isNaN(d.getTime()) ? 0 : d.getTime();
}

function metaForItem(item) {
	if (item.type === "lesson") {
		return [item.grade || "", item.subject || "", item.duration ? `${item.duration}分钟` : ""]
			.filter(Boolean)
			.join(" · ");
	}
	const types = item.types ? (Array.isArray(item.types) ? item.types.join("/") : item.types) : "";
	return [item.grade || "", item.subject || "", types, item.difficulty || "", item.count ? `题量${item.count}` : ""]
		.filter(Boolean)
		.join(" · ");
}

async function apiFetchHistory() {
	const token = getToken();
	if (!token) return [];

	const headers = { "Authorization": `Bearer ${token}` };
	const [lessonResp, exerciseResp] = await Promise.all([
		fetch(`${API_BASE}/api/lesson/history`, { headers }),
		fetch(`${API_BASE}/api/exercise/history`, { headers })
	]);

	if (lessonResp.status === 401 || exerciseResp.status === 401) {
		alert("登录已过期，请重新登录");
		window.location.href = "../login.html";
		return [];
	}

	const [lessonRes, exerciseRes] = await Promise.all([
		lessonResp.json().catch(() => ({})),
		exerciseResp.json().catch(() => ({}))
	]);

	const lessonList = (lessonRes.code === 0 ? lessonRes.data : []) || [];
	const exerciseList = (exerciseRes.code === 0 ? exerciseRes.data : []) || [];

	const lessons = lessonList.map(l => ({
		...l,
		type: "lesson"
	}));
	const exercises = exerciseList.map(e => ({
		...e,
		type: "exercise"
	}));

	return lessons.concat(exercises);
}

function applyFilters() {
	const type = document.getElementById("filterType").value;
	const keyword = (document.getElementById("filterKeyword").value || "").trim().toLowerCase();
	const sort = document.getElementById("filterSort").value;

	let list = [...state.list];
	if (type !== "all") list = list.filter(i => i.type === type);
	if (keyword) {
		list = list.filter(i => (i.title || i.topic || "").toLowerCase().includes(keyword));
	}

	list.sort((a, b) => sort === "new" ? parseTime(b.created_at || "") - parseTime(a.created_at || "") : parseTime(a.created_at || "") - parseTime(b.created_at || ""));
	state.filtered = list;
	renderList();
}

function renderList() {
	const box = document.getElementById("resourceTable");
	const count = document.getElementById("resultCount");
	if (!box || !count) return;

	count.textContent = `${state.filtered.length}`;
	if (!state.filtered.length) {
		box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${t("noData")}</div>`;
		return;
	}

	box.innerHTML = state.filtered.map(item => {
		const title = item.topic || item.title || "-";
		const meta = metaForItem(item);
		const time = (item.created_at || "").slice(0, 19).replace("T", " ");
		const badgeClass = item.type === "exercise" ? "badge exercise" : "badge";
		const badgeText = item.type === "exercise" ? t("typeExercise") : t("typeLesson");
		const active = state.selected && state.selected.type === item.type && state.selected.id === item.id ? "active" : "";
		return `
			<div class="res-row ${active}" data-id="${item.id}" data-type="${item.type}">
				<div class="res-row-top">
					<div class="res-row-title">${title}</div>
					<div class="res-row-meta">${time}</div>
				</div>
				<div class="res-row-sub">${meta || "-"}</div>
				<div class="${badgeClass}">${badgeText}</div>
			</div>
		`;
	}).join("");

	box.querySelectorAll(".res-row").forEach(row => {
		row.addEventListener("click", () => {
			const id = Number(row.getAttribute("data-id"));
			const type = row.getAttribute("data-type");
			const item = state.filtered.find(i => i.id === id && i.type === type);
			if (item) selectItem(item);
		});
	});
}

function selectItem(item) {
	state.selected = item;
	const title = document.getElementById("previewTitle");
	const meta = document.getElementById("previewMeta");
	const body = document.getElementById("previewBody");
	const empty = document.getElementById("previewEmpty");
	if (!title || !meta || !body || !empty) return;

	const text = item.content || "";
	title.textContent = item.topic || item.title || "-";
	meta.textContent = `${item.type === "exercise" ? t("typeExercise") : t("typeLesson")} · ${metaForItem(item) || "-"}`;
	body.textContent = text;
	empty.style.display = text ? "none" : "flex";

	renderList();
}

async function deleteSelected() {
	if (!state.selected) return;
	if (!confirm(t("deleteConfirm"))) return;

	const token = getToken();
	if (!token) return;

	const { type, id } = state.selected;
	const url = type === "lesson" ? `${API_BASE}/api/lesson/${id}` : `${API_BASE}/api/exercise/${id}`;

	const res = await fetch(url, {
		method: "DELETE",
		headers: { "Authorization": `Bearer ${token}` }
	});
	const data = await res.json().catch(() => ({}));
	if (!res.ok || data.code !== 0) {
		alert(data.message || t("loadFail"));
		return;
	}

	state.list = state.list.filter(i => !(i.type === type && i.id === id));
	state.selected = null;
	state.filtered = state.list;
	renderList();
	clearPreview();
	alert(t("deleteOk"));
}

function clearPreview() {
	const title = document.getElementById("previewTitle");
	const meta = document.getElementById("previewMeta");
	const body = document.getElementById("previewBody");
	const empty = document.getElementById("previewEmpty");
	if (!title || !meta || !body || !empty) return;
	title.textContent = "—";
	meta.textContent = "—";
	body.textContent = "";
	empty.style.display = "flex";
}

async function apiListClasses() {
	const user = getLoginUser();
	const headers = { "X-User-Id": user && user.id ? String(user.id) : "" };
	const res = await fetch(`${API_BASE}/api/class/`, { headers });
	const data = await res.json().catch(() => ({}));
	if (!res.ok || data.code !== 0) return [];
	return data.data || [];
}

async function apiGetClass(cid) {
	const user = getLoginUser();
	const headers = { "X-User-Id": user && user.id ? String(user.id) : "" };
	const res = await fetch(`${API_BASE}/api/class/${cid}`, { headers });
	const data = await res.json().catch(() => ({}));
	if (!res.ok || data.code !== 0) return null;
	return data.data || null;
}

function openPublishModal() {
	if (!state.selected) return;
	const modal = document.getElementById("publishModal");
	if (!modal) return;
	modal.classList.add("open");
	modal.setAttribute("aria-hidden", "false");
}

function closePublishModal() {
	const modal = document.getElementById("publishModal");
	if (!modal) return;
	modal.classList.remove("open");
	modal.setAttribute("aria-hidden", "true");
}

function setModeUI(mode) {
	const accuracyRow = document.getElementById("accuracyRow");
	const studentRow = document.getElementById("studentRow");
	if (!accuracyRow || !studentRow) return;

	accuracyRow.style.display = (mode === "accuracy" || mode === "mixed") ? "grid" : "none";
	studentRow.style.display = (mode === "all") ? "none" : "grid";

	renderStudents(mode === "accuracy");
}

function renderStudents(disabled) {
	const box = document.getElementById("studentList");
	if (!box) return;
	if (!state.students.length) {
		box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${t("selectClass")}</div>`;
		return;
	}

	box.innerHTML = state.students.map(s => {
		const checked = state.selectedStudentIds.has(s.id) ? "checked" : "";
		const dis = disabled ? "disabled" : "";
		const accuracy = s.accuracy == null ? "--" : `${s.accuracy}%`;
		return `
			<label class="student-item">
				<div>
					<input type="checkbox" data-id="${s.id}" ${checked} ${dis} />
					${s.name || "-"}
				</div>
				<span>${accuracy}</span>
			</label>
		`;
	}).join("");

	box.querySelectorAll("input[type='checkbox']").forEach(input => {
		input.addEventListener("change", () => {
			const id = Number(input.getAttribute("data-id"));
			if (input.checked) state.selectedStudentIds.add(id);
			else state.selectedStudentIds.delete(id);
		});
	});
}

function applyAccuracySelection() {
	const op = document.getElementById("accuracyOp").value;
	const value = Number(document.getElementById("accuracyValue").value || 0);

	state.selectedStudentIds = new Set(
		state.students
			.filter(s => typeof s.accuracy === "number")
			.filter(s => op === "gte" ? s.accuracy >= value : s.accuracy <= value)
			.map(s => s.id)
	);
	const mode = document.getElementById("publishMode").value;
	renderStudents(mode === "accuracy");
}

async function loadClasses() {
	state.classes = await apiListClasses();
	const select = document.getElementById("publishClass");
	if (!select) return;
	if (!state.classes.length) {
		select.innerHTML = `<option value="">${t("selectClass")}</option>`;
		state.students = [];
		renderStudents(false);
		return;
	}
	select.innerHTML = state.classes.map(c => `<option value="${c.id}">${c.name}</option>`).join("");
	await loadStudents(state.classes[0].id);
}

async function loadStudents(cid) {
	const cls = await apiGetClass(cid);
	state.students = (cls && cls.students) ? cls.students : [];
	state.selectedStudentIds = new Set();

	const mode = document.getElementById("publishMode").value;
	if (mode === "accuracy" || mode === "mixed") {
		applyAccuracySelection();
		return;
	}
	renderStudents(mode === "accuracy");
}

async function publishSelected() {
	if (!state.selected) return;
	const token = getToken();
	if (!token) return;

	const classId = Number(document.getElementById("publishClass").value || 0);
	if (!classId) {
		alert(t("selectClass"));
		return;
	}
	const mode = document.getElementById("publishMode").value;
	const allIds = state.students.map(s => s.id);
	let studentIds = [];

	if (mode === "all") studentIds = allIds;
	else studentIds = Array.from(state.selectedStudentIds);

	if (!studentIds.length) {
		alert(t("publishEmpty"));
		return;
	}

	const payload = {
		resource_type: state.selected.type,
		resource_id: state.selected.id,
		class_id: classId,
		mode,
		student_ids: studentIds,
		accuracy_rule: {
			op: document.getElementById("accuracyOp").value,
			value: Number(document.getElementById("accuracyValue").value || 0)
		}
	};

	const res = await fetch(`${API_BASE}/api/resource/publish`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			"Authorization": `Bearer ${token}`
		},
		body: JSON.stringify(payload)
	});
	const data = await res.json().catch(() => ({}));
	if (!res.ok || data.code !== 0) {
		alert(data.message || t("loadFail"));
		return;
	}
	alert(t("publishOk"));
	closePublishModal();
}

async function refresh() {
	try {
		state.list = await apiFetchHistory();
		state.filtered = state.list;
		state.selected = null;
		renderList();
		clearPreview();
	} catch {
		alert(t("loadFail"));
	}
}

function bindEvents() {
	document.getElementById("btnApply").addEventListener("click", applyFilters);
	document.getElementById("btnRefresh").addEventListener("click", refresh);
	document.getElementById("btnDelete").addEventListener("click", deleteSelected);
	document.getElementById("btnPublish").addEventListener("click", () => {
		openPublishModal();
	});

	document.getElementById("publishClose").addEventListener("click", closePublishModal);
	document.getElementById("publishCloseBtn").addEventListener("click", closePublishModal);
	document.getElementById("publishCancel").addEventListener("click", closePublishModal);
	document.getElementById("publishConfirm").addEventListener("click", publishSelected);

	document.getElementById("publishMode").addEventListener("change", (e) => {
		setModeUI(e.target.value);
	});

	document.getElementById("publishClass").addEventListener("change", (e) => {
		loadStudents(e.target.value);
	});

	document.getElementById("applyAccuracy").addEventListener("click", applyAccuracySelection);
}

document.addEventListener("DOMContentLoaded", async () => {
	applyResourceLang();
	bindEvents();
	await refresh();
	await loadClasses();
	setModeUI(document.getElementById("publishMode").value);
});

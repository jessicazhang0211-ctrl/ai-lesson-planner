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
		keywordPlaceholder: "输入标题/主题",
		sort: "排序",
		sortNew: "最新优先",
		sortOld: "最早优先",
		apply: "应用",
		listTitle: "历史记录",
		delete: "删除",
		publish: "发布",
		empty: "选择左侧资源查看详情",
		pubTitle: "已发布作业",
		pubEmpty: "暂无发布记录",
		pubLessonTitle: "已发布教案",
		pubLessonEmpty: "暂无教案发布记录",
		pubClass: "班级",
		pubDetail: "详情",
		pubRevoke: "撤销",
		pubTypeLesson: "教案",
		pubTypeExercise: "习题",
		pubStudents: "学生数",
		pubMode: "发布方式",
		pubAt: "发布时间",
		statsOverall: "完成率",
		statsAssigned: "已发布",
		statsCompleted: "已完成",
		statsRate: "完成率",
		statsAvg: "平均分",
		statsWrong: "错题数",
		statsAnswered: "作答数",
		statsMax: "满分",
		statsChart: "成绩趋势",
		statsClassLabel: "班级",
		minuteUnit: "分钟",
		questionCountPrefix: "题量",
		publishTitle: "发布资源",
		class: "班级",
		mode: "发布方式",
		modeAll: "全班",
		modeAcc: "按正确率筛选",
		modeManual: "手动选择",
		modeMixed: "正确率筛选 + 手动调整",
		accuracy: "正确率",
		applyAcc: "筛选",
		filterCount: "筛选人数",
		students: "学生",
		cancel: "取消",
		confirm: "确认发布",
		noData: "暂无记录",
		deleteConfirm: "确定删除该资源？",
		deleteOk: "已删除",
		publishOk: "已发布",
		publishEmpty: "请选择发布学生",
		loadFail: "加载失败",
		selectClass: "请选择班级",
		sessionExpired: "登录已过期，请重新登录"
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
		keywordPlaceholder: "Enter title/topic",
		sort: "Sort",
		sortNew: "Newest",
		sortOld: "Oldest",
		apply: "Apply",
		listTitle: "History",
		delete: "Delete",
		publish: "Publish",
		empty: "Select a resource to preview",
		pubTitle: "Published Assignments",
		pubEmpty: "No published items",
		pubLessonTitle: "Published Lessons",
		pubLessonEmpty: "No published lessons",
		pubClass: "Class",
		pubDetail: "Details",
		pubRevoke: "Revoke",
		pubTypeLesson: "Lesson",
		pubTypeExercise: "Exercise",
		pubStudents: "Students",
		pubMode: "Mode",
		pubAt: "Published at",
		statsOverall: "Completion",
		statsAssigned: "Assigned",
		statsCompleted: "Completed",
		statsRate: "Rate",
		statsAvg: "Average",
		statsWrong: "Wrong",
		statsAnswered: "Answered",
		statsMax: "Max",
		statsChart: "Trend",
		statsClassLabel: "Class",
		minuteUnit: "min",
		questionCountPrefix: "Q",
		publishTitle: "Publish Resource",
		class: "Class",
		mode: "Publish mode",
		modeAll: "All students",
		modeAcc: "By accuracy",
		modeManual: "Manual select",
		modeMixed: "Accuracy + manual",
		accuracy: "Accuracy",
		applyAcc: "Apply",
		filterCount: "Filtered",
		students: "Students",
		cancel: "Cancel",
		confirm: "Confirm",
		noData: "No records",
		deleteConfirm: "Delete this resource?",
		deleteOk: "Deleted",
		publishOk: "Published",
		publishEmpty: "Please select students",
		loadFail: "Load failed",
		selectClass: "Please select a class",
		sessionExpired: "Session expired. Please sign in again"
	}
};

const API_BASE = "http://127.0.0.1:5000";

const state = {
	list: [],
	filtered: [],
	selected: null,
	classes: [],
	students: [],
	selectedStudentIds: new Set(),
	published: []
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
	document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
		const key = el.getAttribute("data-i18n-placeholder");
		if (resourceDict[getLocale()][key]) el.placeholder = resourceDict[getLocale()][key];
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
		return [item.grade || "", item.subject || "", item.duration ? `${item.duration}${t("minuteUnit")}` : ""]
			.filter(Boolean)
			.join(" · ");
	}
	const types = item.types ? (Array.isArray(item.types) ? item.types.join("/") : item.types) : "";
	return [item.grade || "", item.subject || "", types, item.difficulty || "", item.count ? `${t("questionCountPrefix")}${item.count}` : ""]
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
		alert(t("sessionExpired"));
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

async function apiFetchPublished() {
	const token = getToken();
	if (!token) return [];
	const res = await fetch(`${API_BASE}/api/resource/publish`, {
		headers: { "Authorization": `Bearer ${token}` }
	});
	const data = await res.json().catch(() => ({}));
	if (!res.ok || data.code !== 0) return [];
	return data.data || [];
}

async function apiRevokePublish(pubId) {
	const token = getToken();
	if (!token) return false;
	const res = await fetch(`${API_BASE}/api/resource/publish/${pubId}/revoke`, {
		method: "POST",
		headers: { "Authorization": `Bearer ${token}` }
	});
	const data = await res.json().catch(() => ({}));
	return res.ok && data.code === 0;
}

async function apiFetchStats(item, classId) {
	const token = getToken();
	if (!token) return null;
	const qs = classId ? `?class_id=${classId}` : "";
	const res = await fetch(`${API_BASE}/api/resource/resource/${item.resource_type}/${item.resource_id}/stats${qs}`, {
		headers: { "Authorization": `Bearer ${token}` }
	});
	const data = await res.json().catch(() => ({}));
	if (!res.ok || data.code !== 0) return null;
	return data.data;
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


function renderPublishedSection(items, listId, emptyId) {
	const list = document.getElementById(listId);
	const empty = document.getElementById(emptyId);
	if (!list || !empty) return;

	if (!items.length) {
		list.innerHTML = "";
		empty.style.display = "flex";
		return;
	}

	empty.style.display = "none";
	list.innerHTML = items.map(item => {
		const title = item.title || "-";
		const typeLabel = item.resource_type === "exercise" ? t("pubTypeExercise") : t("pubTypeLesson");
		const className = item.class_name || "-";
		const studentCount = Array.isArray(item.student_ids) ? item.student_ids.length : 0;
		const createdAt = item.created_at || "";
		return `
			<div class="res-pub-item" data-id="${item.id}">
				<div class="res-pub-top">
					<div class="res-pub-title">${title}</div>
					<div class="res-pub-meta">${createdAt}</div>
				</div>
				<div class="res-pub-tags">
					<span class="tag blue">${typeLabel}</span>
					<span class="tag">${t("pubClass")}: ${className}</span>
					<span class="tag">${t("pubStudents")}: ${studentCount}</span>
					<span class="tag">${t("pubMode")}: ${item.mode || "-"}</span>
				</div>
				<div class="res-pub-actions">
					<button class="btn" data-action="detail">${t("pubDetail")}</button>
					<button class="btn" data-action="revoke">${t("pubRevoke")}</button>
				</div>
			</div>
		`;
	}).join("");

	list.querySelectorAll(".res-pub-item").forEach(row => {
		row.addEventListener("click", async (e) => {
			const action = e.target?.getAttribute("data-action");
			if (!action) return;
			const id = Number(row.getAttribute("data-id"));
			const item = state.published.find(x => x.id === id);
			if (!item) return;
			if (action === "revoke") {
				const ok = await apiRevokePublish(item.id);
				if (ok) {
					await refreshPublished();
				}
				return;
			}
			if (action === "detail") {
				openStatsModal(item);
			}
		});
	});
}

function renderPublishedList() {
	const exercises = state.published.filter(item => item.resource_type === "exercise");
	const lessons = state.published.filter(item => item.resource_type === "lesson");
	renderPublishedSection(exercises, "publishedList", "publishedEmpty");
	renderPublishedSection(lessons, "publishedLessonList", "publishedLessonEmpty");
}

async function refreshPublished() {
	try {
		state.published = await apiFetchPublished();
		renderPublishedList();
	} catch {
		renderPublishedList();
	}
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

function openStatsModal(item) {
	const modal = document.getElementById("statsModal");
	if (!modal) return;
	const title = document.getElementById("statsTitle");
	const summary = document.getElementById("statsSummary");
	const list = document.getElementById("statsList");
	const chart = document.getElementById("statsChart");
	const classSelect = document.getElementById("statsClass");

	if (title) title.textContent = item.title || "—";
	if (summary) summary.textContent = "";
	if (list) list.innerHTML = "";
	if (chart) chart.innerHTML = "";
	if (classSelect) classSelect.innerHTML = "";

	modal.classList.add("open");
	modal.setAttribute("aria-hidden", "false");

	const renderStats = (stats) => {
		if (!stats) return;
		const overall = stats.overall || { assigned: 0, completed: 0, rate: 0 };
		if (summary) {
			summary.textContent = `${t("statsOverall")}：${overall.rate}%  ·  ${t("statsAssigned")}${overall.assigned}  ·  ${t("statsCompleted")}${overall.completed}`;
		}

		if (classSelect) {
			const classes = stats.classes || [];
			const options = [`<option value="">${t("typeAll")}</option>`]
				.concat(classes.map(c => `<option value="${c.class_id}">${c.class_name || "-"}</option>`));
			classSelect.innerHTML = options.join("");
		}

		if (chart) {
			const trend = stats.trend || [];
			if (!trend.length) {
				chart.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${t("noData")}</div>`;
			} else {
				const width = 640;
				const height = 200;
				const padding = 24;
				const maxScore = Math.max(...trend.map(i => i.score ?? 0), 100);
				const minScore = Math.min(...trend.map(i => i.score ?? 0), 0);
				const range = Math.max(1, maxScore - minScore);
				const stepX = (width - padding * 2) / Math.max(1, trend.length - 1);
				const points = trend.map((item, idx) => {
					const x = padding + stepX * idx;
					const y = height - padding - ((item.score - minScore) / range) * (height - padding * 2);
					return { x, y, label: item.label || "" };
				});
				const path = points.map((p, idx) => `${idx === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
				const dots = points.map(p => `<circle class="stats-dot" cx="${p.x}" cy="${p.y}" r="4" />`).join("");
				const labels = points.map(p => `<text class="stats-label" x="${p.x}" y="${height - 6}" text-anchor="middle">${p.label}</text>`).join("");
				chart.innerHTML = `
					<svg viewBox="0 0 ${width} ${height}">
						<path class="stats-line" d="${path}"></path>
						${dots}
						${labels}
					</svg>
				`;
			}
		}

		if (list) {
			const questions = stats.questions || [];
			if (!questions.length) {
				list.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${t("noData")}</div>`;
				return;
			}
			list.innerHTML = questions.map(q => {
				const avg = q.avg_score == null ? "-" : q.avg_score;
				return `
					<div class="stats-item">
						<div>
							<div class="name">${q.stem || "-"}</div>
							<div class="meta">${q.type || ""} · ${t("statsMax")}${q.max_score}</div>
						</div>
						<div class="meta">${t("statsAvg")}${avg} · ${t("statsWrong")}${q.wrong_count} · ${t("statsAnswered")}${q.answer_count}</div>
					</div>
				`;
			}).join("");
		}
	};

	apiFetchStats(item).then(stats => {
		renderStats(stats);
		if (classSelect) {
			classSelect.addEventListener("change", () => {
				const cid = classSelect.value || "";
				apiFetchStats(item, cid).then(renderStats);
			});
		}
	});
}

function closeStatsModal() {
	const modal = document.getElementById("statsModal");
	if (!modal) return;
	modal.classList.remove("open");
	modal.setAttribute("aria-hidden", "true");
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
	const countRow = document.getElementById("accuracyCountRow");
	if (!accuracyRow || !studentRow) return;

	accuracyRow.style.display = (mode === "accuracy" || mode === "mixed") ? "grid" : "none";
	studentRow.style.display = (mode === "all") ? "none" : "grid";
	if (countRow) countRow.style.display = (mode === "accuracy" || mode === "mixed") ? "grid" : "none";

	if (mode === "accuracy" || mode === "mixed") {
		applyAccuracySelection();
		return;
	}

	renderStudents(false);
}

function renderStudents(disabled, listOverride = null) {
	const box = document.getElementById("studentList");
	if (!box) return;
	const countEl = document.getElementById("accuracyCount");
	if (!state.students.length) {
		box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${t("selectClass")}</div>`;
		if (countEl) countEl.textContent = "0";
		return;
	}
	const list = Array.isArray(listOverride) ? listOverride : state.students;
	if (countEl) countEl.textContent = String(list.length);
	if (!list.length) {
		box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${t("noData")}</div>`;
		return;
	}

	box.innerHTML = list.map(s => {
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

function getAccuracyFilteredStudents() {
	const op = document.getElementById("accuracyOp").value;
	const value = Number(document.getElementById("accuracyValue").value || 0);
	return state.students
		.filter(s => typeof s.accuracy === "number")
		.filter(s => op === "gte" ? s.accuracy >= value : s.accuracy <= value);
}

function applyAccuracySelection() {
	const filtered = getAccuracyFilteredStudents();
	state.selectedStudentIds = new Set(filtered.map(s => s.id));
	const mode = document.getElementById("publishMode").value;
	const listOverride = mode === "accuracy" ? filtered : null;
	renderStudents(mode === "accuracy", listOverride);
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
	renderStudents(false);
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
	document.getElementById("btnPubRefresh").addEventListener("click", refreshPublished);
	document.getElementById("btnPubLessonRefresh").addEventListener("click", refreshPublished);
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

	document.getElementById("statsClose").addEventListener("click", closeStatsModal);
	document.getElementById("statsCloseBtn").addEventListener("click", closeStatsModal);
}

document.addEventListener("DOMContentLoaded", async () => {
	applyResourceLang();
	bindEvents();
	await refresh();
	await refreshPublished();
	await loadClasses();
	setModeUI(document.getElementById("publishMode").value);
});

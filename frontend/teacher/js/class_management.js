/* ============================
   Class Management (Frontend Only)
   File: frontend/teacher/js/class_management.js
   Works with: teacher topbar + sidebar integrated class_management.html
   ============================ */

/** ---------- Helpers ---------- */
function $(id) { return document.getElementById(id); }
function safeOn(el, evt, fn) { if (el) el.addEventListener(evt, fn); }
function nowDate() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}
function uuid() {
  return Math.random().toString(16).slice(2) + Date.now().toString(16);
}
function clamp(n, min, max) { return Math.max(min, Math.min(max, n)); }
function getLocale() { return localStorage.getItem("locale") || "zh"; }
function setDocLang() { document.documentElement.lang = getLocale(); }
async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    ta.remove();
    return ok;
  }
}
function downloadFile(filename, text, mime = "application/json;charset=utf-8") {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** ---------- i18n dict ---------- */
const cmDict = {
  zh: {
    classListTitle: "班级列表",
    newClass: "+ 新建班级",
    tipTitle: "小提示",
    tipText: "复制班级码给学生即可加入，或使用“导入名单”。",
    emptyTitle: "请选择一个班级",
    emptySub: "在左侧点击班级后管理学生名单与设置。",

    codeLabel: "班级码：",
    createdLabel: "创建于：",
    copy: "复制",
    reset: "重置",
    import_tpl: "下载模板",
    import: "导入名单",
    export: "导出",
    archive: "归档班级",
    edit: "编辑",
    del: "删除",

    kpiStu: "学生人数",
    kpiStuHint: "本班当前在册",
    kpiHw: "本周作业提交",
    kpiHwHint: "已提交 / 总人数",
    kpiAcc: "平均正确率",
    kpiAccHint: "近 7 天",
    kpiTodo: "待处理",
    kpiTodoHint: "请假 / 转班 / 异常",

    studentListTitle: "学生名单",
    filterLabel: "筛选",
    sortLabel: "排序",
    addStudent: "+ 添加学生",

    thName: "姓名",
    thId: "学号",
    thStatus: "状态",
    thAcc: "正确率",
    thSubmit: "提交率",
    thOp: "操作",

    stuEmptyTitle: "暂无学生",
    stuEmptySub: "点击“添加学生”或“导入名单”。",

    pagePrev: "上一页",
    pageNext: "下一页",
    countText: (n) => `共 ${n} 名学生`,

    settingsTitle: "班级设置",
    setName: "班级名称",
    setStage: "学段",
    setJoin: "允许学生自助加入",
    setNote: "备注",
    saveSettings: "保存设置",

    // Status
    status_active: "进行中",
    status_archived: "已归档",

    stu_joined: "已加入",
    stu_pending: "待审核",
    stu_disabled: "已禁用",

    // Buttons in row
    btn_detail: "详情",
    btn_edit: "编辑",
    btn_remove: "移出",
    btn_reset_pwd: "重置密码",
    btn_approve: "通过",
    btn_reject: "拒绝",
    btn_enable: "启用",
    btn_disable: "禁用",

    // Modals
    classModalTitleNew: "新建班级",
    classModalTitleEdit: "编辑班级",
    mClassName: "班级名称",
    mClassDesc: "描述（可选）",
    cancel: "取消",
    save: "保存",

    stuModalTitleNew: "添加学生",
    stuModalTitleEdit: "编辑学生",
    mStuName: "姓名",
    mStuId: "学号",
    mStuStatus: "状态",
    mParent: "家长电话",
    mAcc: "正确率(%)",
    mSubmit: "提交率(%)",

    drawerTitle: "学生详情",
    drawerEdit: "编辑",
    drawerRemove: "移出",

    // Alerts
    toast_saved: "已保存",
    toast_copied: "已复制",
    toast_deleted: "已删除",
    toast_archived: "已归档",
    toast_restored: "已恢复为进行中",
    toast_code_reset: "班级码已重置",
    toast_pwd_reset: "已重置密码（演示）",
    confirm_delete_class: "确定删除该班级？此操作不可撤销。",
    confirm_archive_class: "确定归档该班级？可在“已归档”中查看。",
    confirm_delete_student: "确定移出该学生？",
    invalid_csv: "CSV 格式不正确（需包含 name,stu_id 或 姓名,学号）"
  },

  en: {
    classListTitle: "Classes",
    newClass: "+ New class",
    tipTitle: "Tip",
    tipText: "Share the class code to let students join, or import a roster.",
    emptyTitle: "Select a class",
    emptySub: "Click a class on the left to manage students and settings.",

    codeLabel: "Code: ",
    createdLabel: "Created: ",
    copy: "Copy",
    reset: "Reset",
    import_tpl: "Download template",
    import: "Import roster",
    export: "Export",
    archive: "Archive",
    edit: "Edit",
    del: "Delete",

    kpiStu: "Students",
    kpiStuHint: "Currently enrolled",
    kpiHw: "Homework (week)",
    kpiHwHint: "Submitted / total",
    kpiAcc: "Avg. accuracy",
    kpiAccHint: "Last 7 days",
    kpiTodo: "Pending",
    kpiTodoHint: "Requests / issues",

    studentListTitle: "Students",
    filterLabel: "Filter",
    sortLabel: "Sort",
    addStudent: "+ Add student",

    thName: "Name",
    thId: "Student ID",
    thStatus: "Status",
    thAcc: "Accuracy",
    thSubmit: "Submission",
    thOp: "Actions",

    stuEmptyTitle: "No students",
    stuEmptySub: "Click “Add student” or “Import roster”.",

    pagePrev: "Prev",
    pageNext: "Next",
    countText: (n) => `${n} students`,

    settingsTitle: "Class settings",
    setName: "Class name",
    setStage: "Stage",
    setJoin: "Allow self-join",
    setNote: "Note",
    saveSettings: "Save settings",

    status_active: "Active",
    status_archived: "Archived",

    stu_joined: "Joined",
    stu_pending: "Pending",
    stu_disabled: "Disabled",

    btn_detail: "Details",
    btn_edit: "Edit",
    btn_remove: "Remove",
    btn_reset_pwd: "Reset password",
    btn_approve: "Approve",
    btn_reject: "Reject",
    btn_enable: "Enable",
    btn_disable: "Disable",

    classModalTitleNew: "New class",
    classModalTitleEdit: "Edit class",
    mClassName: "Class name",
    mClassDesc: "Description (optional)",
    cancel: "Cancel",
    save: "Save",

    stuModalTitleNew: "Add student",
    stuModalTitleEdit: "Edit student",
    mStuName: "Name",
    mStuId: "Student ID",
    mStuStatus: "Status",
    mParent: "Parent phone",
    mAcc: "Accuracy(%)",
    mSubmit: "Submission(%)",

    drawerTitle: "Student details",
    drawerEdit: "Edit",
    drawerRemove: "Remove",

    toast_saved: "Saved",
    toast_copied: "Copied",
    toast_deleted: "Deleted",
    toast_archived: "Archived",
    toast_restored: "Restored to active",
    toast_code_reset: "Code reset",
    toast_pwd_reset: "Password reset (demo)",
    confirm_delete_class: "Delete this class? This cannot be undone.",
    confirm_archive_class: "Archive this class? You can find it under “Archived”.",
    confirm_delete_student: "Remove this student?",
    invalid_csv: "Invalid CSV (needs name,stu_id or 姓名,学号)"
  }
};

function t(key) {
  const lang = getLocale();
  const dict = cmDict[lang] || cmDict.zh;
  const v = dict[key];
  return typeof v === "function" ? v : (v ?? key);
}

/** ---------- Storage ---------- */
const STORE_KEY = "cm_store_v1";

function loadStore() {
  const raw = localStorage.getItem(STORE_KEY);
  if (raw) {
    try { return JSON.parse(raw); } catch {}
  }
  // If logged in, try to load from backend
  const loginRaw = localStorage.getItem('login_user');
  if (loginRaw) {
    try {
      const user = JSON.parse(loginRaw);
      // fetch classes synchronously is not possible here; return empty shell and caller will populate
      return { classes: [] };
    } catch {}
  }
  // default demo data
  const demo = {
    classes: [
      {
        id: "c1",
        name: "一年级（1）班",
        desc: "数学基础",
        status: "active",
        code: "A1B2C3",
        created_at: "2026-02-01",
        stage: "primary",
        allow_join: true,
        note: "",
        students: [
          { id: "s1", name: "林小雨", stu_id: "202601001", status: "joined", parent_phone: "138****8801", accuracy: 86, submit: 92 },
          { id: "s2", name: "周子涵", stu_id: "202601002", status: "pending", parent_phone: "137****2109", accuracy: null, submit: null },
          { id: "s3", name: "王一鸣", stu_id: "202601003", status: "disabled", parent_phone: "139****5510", accuracy: 71, submit: 44 }
        ]
      },
      { id: "c2", name: "一年级（2）班", desc: "", status: "active", code: "K9P1Q7", created_at: "2026-02-02", stage: "primary", allow_join: true, note: "", students: [] },
      { id: "c3", name: "二年级（3）班", desc: "", status: "archived", code: "Z3H8M2", created_at: "2026-01-15", stage: "primary", allow_join: false, note: "已结束", students: [] }
    ]
  };
  localStorage.setItem(STORE_KEY, JSON.stringify(demo));
  return demo;
}

function saveStore(store) {
  localStorage.setItem(STORE_KEY, JSON.stringify(store));
}

/** ---------- State ---------- */
const state = {
  store: loadStore(),
  classFilter: "all",   // all | active | archived
  selectedClassId: null,
  stuFilter: "all",     // all | joined | pending | disabled
  stuSort: "name",      // name | stu_id | accuracy | submit
  page: 1,
  pageSize: 8,
  editingClassId: null,
  editingStudentId: null,
  drawerStudentId: null
};

/** ---------- UI Apply Text ---------- */
function applyText() {
  setDocLang();

  if ($("classListTitle")) $("classListTitle").textContent = t("classListTitle");
  if ($("newClassBtn")) $("newClassBtn").textContent = t("newClass");
  if ($("tipTitle")) $("tipTitle").textContent = t("tipTitle");
  if ($("tipText")) $("tipText").textContent = t("tipText");
  if ($("emptyTitle")) $("emptyTitle").textContent = t("emptyTitle");
  if ($("emptySub")) $("emptySub").textContent = t("emptySub");

  if ($("codeLabel")) $("codeLabel").textContent = t("codeLabel");
  if ($("createdLabel")) $("createdLabel").textContent = t("createdLabel");

  if ($("copyCodeBtn")) $("copyCodeBtn").textContent = t("copy");
  if ($("resetCodeBtn")) $("resetCodeBtn").textContent = t("reset");
  if ($("downloadTemplateBtn")) $("downloadTemplateBtn").textContent = t("import_tpl");

  if ($("importBtnText")) $("importBtnText").textContent = t("import");
  if ($("exportBtn")) $("exportBtn").textContent = t("export");
  if ($("archiveBtn")) $("archiveBtn").textContent = t("archive");
  if ($("editClassBtn")) $("editClassBtn").textContent = t("edit");
  if ($("deleteClassBtn")) $("deleteClassBtn").textContent = t("del");

  if ($("kpiStu")) $("kpiStu").textContent = t("kpiStu");
  if ($("kpiStuHint")) $("kpiStuHint").textContent = t("kpiStuHint");
  if ($("kpiHw")) $("kpiHw").textContent = t("kpiHw");
  if ($("kpiHwHint")) $("kpiHwHint").textContent = t("kpiHwHint");
  if ($("kpiAcc")) $("kpiAcc").textContent = t("kpiAcc");
  if ($("kpiAccHint")) $("kpiAccHint").textContent = t("kpiAccHint");
  if ($("kpiTodo")) $("kpiTodo").textContent = t("kpiTodo");
  if ($("kpiTodoHint")) $("kpiTodoHint").textContent = t("kpiTodoHint");

  if ($("studentListTitle")) $("studentListTitle").textContent = t("studentListTitle");
  if ($("filterLabel")) $("filterLabel").textContent = t("filterLabel");
  if ($("sortLabel")) $("sortLabel").textContent = t("sortLabel");
  if ($("addStudentBtn")) $("addStudentBtn").textContent = t("addStudent");

  if ($("thName")) $("thName").textContent = t("thName");
  if ($("thId")) $("thId").textContent = t("thId");
  if ($("thStatus")) $("thStatus").textContent = t("thStatus");
  if ($("thAcc")) $("thAcc").textContent = t("thAcc");
  if ($("thSubmit")) $("thSubmit").textContent = t("thSubmit");
  if ($("thOp")) $("thOp").textContent = t("thOp");

  if ($("stuEmptyTitle")) $("stuEmptyTitle").textContent = t("stuEmptyTitle");
  if ($("stuEmptySub")) $("stuEmptySub").textContent = t("stuEmptySub");

  if ($("prevPage")) $("prevPage").textContent = t("pagePrev");
  if ($("nextPage")) $("nextPage").textContent = t("pageNext");

  if ($("settingsTitle")) $("settingsTitle").textContent = t("settingsTitle");
  if ($("setNameLabel")) $("setNameLabel").textContent = t("setName");
  if ($("setStageLabel")) $("setStageLabel").textContent = t("setStage");
  if ($("setJoinLabel")) $("setJoinLabel").textContent = t("setJoin");
  if ($("setNoteLabel")) $("setNoteLabel").textContent = t("setNote");
  if ($("saveSettingsBtn")) $("saveSettingsBtn").textContent = t("saveSettings");

  // modals
  if ($("mClassNameLabel")) $("mClassNameLabel").textContent = t("mClassName");
  if ($("mClassDescLabel")) $("mClassDescLabel").textContent = t("mClassDesc");
  if ($("cancelClassModal")) $("cancelClassModal").textContent = t("cancel");
  if ($("saveClassModal")) $("saveClassModal").textContent = t("save");

  if ($("mStuNameLabel")) $("mStuNameLabel").textContent = t("mStuName");
  if ($("mStuIdLabel")) $("mStuIdLabel").textContent = t("mStuId");
  if ($("mStuStatusLabel")) $("mStuStatusLabel").textContent = t("mStuStatus");
  if ($("mParentLabel")) $("mParentLabel").textContent = t("mParent");
  if ($("mAccLabel")) $("mAccLabel").textContent = t("mAcc");
  if ($("mSubmitLabel")) $("mSubmitLabel").textContent = t("mSubmit");
  if ($("cancelStuModal")) $("cancelStuModal").textContent = t("cancel");
  if ($("saveStuModal")) $("saveStuModal").textContent = t("save");

  if ($("drawerTitle")) $("drawerTitle").textContent = t("drawerTitle");
  if ($("drawerEdit")) $("drawerEdit").textContent = t("drawerEdit");
  if ($("drawerRemove")) $("drawerRemove").textContent = t("drawerRemove");

  // options text for select
  if ($("stuStatusSelect")) {
    const sel = $("stuStatusSelect");
    const map = { all: getLocale()==="zh"?"全部":"All", joined: t("stu_joined"), pending: t("stu_pending"), disabled: t("stu_disabled") };
    [...sel.options].forEach(op => { if (map[op.value]) op.textContent = map[op.value]; });
  }
  if ($("stuSortSelect")) {
    const sel = $("stuSortSelect");
    const map = {
      name: getLocale()==="zh" ? "按姓名" : "By name",
      stu_id: getLocale()==="zh" ? "按学号" : "By ID",
      accuracy: getLocale()==="zh" ? "按正确率" : "By accuracy",
      submit: getLocale()==="zh" ? "按提交率" : "By submission"
    };
    [...sel.options].forEach(op => { if (map[op.value]) op.textContent = map[op.value]; });
  }

  // stage options
  if ($("setStage")) {
    const map = {
      primary: getLocale()==="zh" ? "小学" : "Primary",
      junior: getLocale()==="zh" ? "初中" : "Middle",
      senior: getLocale()==="zh" ? "高中" : "High"
    };
    [...$("setStage").options].forEach(op => { if (map[op.value]) op.textContent = map[op.value]; });
  }
  if ($("mStuStatus")) {
    const map = { joined: t("stu_joined"), pending: t("stu_pending"), disabled: t("stu_disabled") };
    [...$("mStuStatus").options].forEach(op => { if (map[op.value]) op.textContent = map[op.value]; });
  }
}

/** ---------- Render ---------- */
function classStatusLabel(status) {
  if (status === "archived") return t("status_archived");
  return t("status_active");
}
function studentStatusPill(status) {
  if (status === "pending") return { cls: "cm-pill--warn", text: t("stu_pending") };
  if (status === "disabled") return { cls: "cm-pill--muted", text: t("stu_disabled") };
  return { cls: "cm-pill--ok", text: t("stu_joined") };
}

function getClassesFiltered() {
  const all = state.store.classes.slice();
  if (state.classFilter === "active") return all.filter(c => c.status === "active");
  if (state.classFilter === "archived") return all.filter(c => c.status === "archived");
  return all;
}

function renderClassList() {
  const list = $("classList");
  if (!list) return;

  const classes = getClassesFiltered();
  list.innerHTML = "";

  classes.forEach(c => {
    const btn = document.createElement("button");
    btn.className = "cm-classitem" + (c.id === state.selectedClassId ? " cm-classitem--active" : "");
    btn.type = "button";

    const badgeCls = c.status === "active" ? "cm-badge cm-badge--green" : "cm-badge";
    const badgeText = classStatusLabel(c.status);

    btn.innerHTML = `
      <div class="cm-classitem__title">
        <span>${escapeHtml(c.name)}</span>
        <span class="${badgeCls}">${badgeText}</span>
      </div>
      <div class="cm-classitem__meta">
        <span>${getLocale()==="zh"?"班级码":"Code"}：${escapeHtml(c.code)}</span>
        <span>${getLocale()==="zh"?"学生":"Students"}：${(c.students||[]).length}</span>
      </div>
    `;
    btn.addEventListener("click", async () => {
      state.selectedClassId = c.id;
      state.page = 1;
      // If this class is server-backed (numeric id) and students not loaded, fetch detail
      try {
        if (typeof c.id === 'number' && (!c.students || c.students.length === 0)) {
          const detail = await apiFetch(`/api/class/${c.id}`, { method: 'GET' });
          // apiFetch returns the 'data' payload of class (with students)
          // Merge into existing class object
          Object.assign(c, detail);
        }
      } catch (e) {
        console.warn('fetch class detail failed', e);
      }
      renderAll();
    });
    list.appendChild(btn);
  });

  // 如果当前选择的班级被过滤掉了，清空选择
  if (state.selectedClassId && !state.store.classes.some(c => c.id === state.selectedClassId)) {
    state.selectedClassId = null;
  }
  if (state.selectedClassId && !classes.some(c => c.id === state.selectedClassId)) {
    state.selectedClassId = null;
  }
}

function renderRightPanel() {
  const empty = $("emptyRight");
  const panel = $("rightPanel");
  if (!empty || !panel) return;

  const cls = state.store.classes.find(c => c.id === state.selectedClassId);
  if (!cls) {
    empty.classList.remove("hidden");
    panel.classList.add("hidden");
    return;
  }
  empty.classList.add("hidden");
  panel.classList.remove("hidden");

  if ($("classTitle")) $("classTitle").textContent = cls.name;
  if ($("classCode")) $("classCode").textContent = cls.code;
  if ($("createdAt")) $("createdAt").textContent = cls.created_at || nowDate();

  // KPIs
  const stuCount = (cls.students || []).length;
  if ($("kpiStuVal")) $("kpiStuVal").textContent = String(stuCount);

  const submitted = Math.max(0, Math.min(stuCount, Math.round(stuCount * 0.8)));
  if ($("kpiHwVal")) $("kpiHwVal").textContent = `${submitted}`;

  const accList = (cls.students || []).map(s => (typeof s.accuracy === "number" ? s.accuracy : null)).filter(v => v !== null);
  const avgAcc = accList.length ? Math.round(accList.reduce((a,b)=>a+b,0)/accList.length) : null;
  if ($("kpiAccVal")) $("kpiAccVal").textContent = avgAcc === null ? "—" : `${avgAcc}%`;

  const pendingCount = (cls.students || []).filter(s => s.status === "pending").length;
  if ($("kpiTodoVal")) $("kpiTodoVal").textContent = String(pendingCount);

  // settings fields
  if ($("setName")) $("setName").value = cls.name || "";
  if ($("setStage")) $("setStage").value = cls.stage || "primary";
  if ($("joinSwitch")) $("joinSwitch").checked = !!cls.allow_join;
  if ($("setNote")) $("setNote").value = cls.note || "";

  renderStudentTable();
}

function getStudentsView(cls) {
  let arr = (cls.students || []).slice();

  // filter
  if (state.stuFilter !== "all") {
    arr = arr.filter(s => s.status === state.stuFilter);
  }

  // sort
  const by = state.stuSort;
  const dir = 1;
  arr.sort((a,b) => {
    if (by === "name") return (a.name || "").localeCompare(b.name || "");
    if (by === "stu_id") return (a.stu_id || "").localeCompare(b.stu_id || "");
    if (by === "accuracy") return ((b.accuracy ?? -1) - (a.accuracy ?? -1)) * dir;
    if (by === "submit") return ((b.submit ?? -1) - (a.submit ?? -1)) * dir;
    return 0;
  });

  return arr;
}

function renderStudentTable() {
  const tbody = $("stuTbody");
  const emptyBox = $("stuEmpty");
  const countText = $("countText");
  const pageText = $("pageText");
  if (!tbody || !emptyBox || !countText || !pageText) return;

  const cls = state.store.classes.find(c => c.id === state.selectedClassId);
  if (!cls) return;

  const allView = getStudentsView(cls);
  const total = allView.length;

  // pagination
  const totalPages = Math.max(1, Math.ceil(total / state.pageSize));
  state.page = clamp(state.page, 1, totalPages);

  const start = (state.page - 1) * state.pageSize;
  const pageItems = allView.slice(start, start + state.pageSize);

  tbody.innerHTML = "";

  if (total === 0) {
    emptyBox.classList.remove("hidden");
  } else {
    emptyBox.classList.add("hidden");
  }

  pageItems.forEach((s, idx) => {
    const n = start + idx + 1;
    const pill = studentStatusPill(s.status);
    const acc = (typeof s.accuracy === "number") ? `${s.accuracy}%` : "—";
    const sub = (typeof s.submit === "number") ? `${s.submit}%` : "—";
    const parent = maskPhone(s.parent_phone || "");

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${String(n).padStart(2,"0")}</td>
      <td>
        <div class="cm-stu">
          <div class="cm-stu__av">${escapeHtml((s.name||"").slice(0,1) || "S")}</div>
          <div class="cm-stu__info">
            <div class="cm-stu__name">${escapeHtml(s.name || "—")}</div>
            <div class="cm-stu__sub">${getLocale()==="zh"?"家长：":"Parent: "}${escapeHtml(parent)}</div>
          </div>
        </div>
      </td>
      <td class="cm-mono">${escapeHtml(s.stu_id || "—")}</td>
      <td><span class="cm-pill ${pill.cls}">${pill.text}</span></td>
      <td>${acc}</td>
      <td>${sub}</td>
      <td>
        <div class="cm-rowbtns" data-stu-id="${s.id}">
          ${renderStudentActions(s)}
        </div>
      </td>
    `;

    // action handlers via event delegation on row container
    tbody.appendChild(tr);
  });

  countText.textContent = t("countText")(total);
  pageText.textContent = `${state.page} / ${Math.max(1, Math.ceil(total / state.pageSize))}`;

  // attach handlers (delegate)
  safeOn(tbody, "click", onStudentActionClick);
}

function renderStudentActions(s) {
  // different action sets by status
  const lang = getLocale();
  const detail = `<button class="cm-btn cm-btn--sm" data-action="detail">${t("btn_detail")}</button>`;
  const edit = `<button class="cm-btn cm-btn--sm" data-action="edit">${t("btn_edit")}</button>`;
  const remove = `<button class="cm-btn cm-btn--sm cm-btn--ghost" data-action="remove">${t("btn_remove")}</button>`;

  if (s.status === "pending") {
    return `
      <button class="cm-btn cm-btn--sm cm-btn--primary" data-action="approve">${t("btn_approve")}</button>
      <button class="cm-btn cm-btn--sm" data-action="reject">${t("btn_reject")}</button>
      ${detail}
    `;
  }

  if (s.status === "disabled") {
    return `
      <button class="cm-btn cm-btn--sm" data-action="enable">${t("btn_enable")}</button>
      ${detail}
      ${remove}
    `;
  }

  // joined
  return `
    ${detail}
    <button class="cm-btn cm-btn--sm" data-action="resetpwd">${t("btn_reset_pwd")}</button>
    <button class="cm-btn cm-btn--sm" data-action="disable">${t("btn_disable")}</button>
    ${remove}
  `;
}

function onStudentActionClick(e) {
  const btn = e.target.closest("button");
  if (!btn) return;

  const row = e.target.closest(".cm-rowbtns");
  const stuId = row?.getAttribute("data-stu-id");
  const cls = state.store.classes.find(c => c.id === state.selectedClassId);
  if (!cls || !stuId) return;
  const s = (cls.students || []).find(x => String(x.id) === String(stuId));
  if (!s) return;

  const action = btn.getAttribute("data-action") || "";

  // detail
  if (action === "detail") { openDrawer(s.id); return; }

  // edit
  if (action === "edit") { openStuModal("edit", s.id); return; }

  if (action === "resetpwd") {
    if (typeof s.id === 'number' && typeof cls.id === 'number') {
      apiFetch(`/api/class/${cls.id}/students/${s.id}/reset-password`, { method: 'POST', body: JSON.stringify({}) })
        .then(d => { alert(`${t('toast_pwd_reset')}: ${d.new_password}`); })
        .catch(() => { alert('重置密码失败'); });
      return;
    }
    alert(t("toast_pwd_reset"));
    return;
  }

  if (action === "approve") {
    if (typeof s.id === 'number' && typeof cls.id === 'number') {
      apiFetch(`/api/class/${cls.id}/students/${s.id}/status`, { method: 'POST', body: JSON.stringify({ action: 'enable' }) })
        .then(d => { s.status = d.status; saveStore(state.store); renderAll(); alert(t('toast_saved')); })
        .catch(() => { alert('操作失败'); });
      return;
    }
    s.status = "joined"; persistAndRender(t("toast_saved")); return;
  }

  if (action === "reject") {
    if (typeof s.id === 'number' && typeof cls.id === 'number') {
      apiFetch(`/api/class/${cls.id}/students/${s.id}`, { method: 'DELETE' })
        .then(() => { cls.students = (cls.students || []).filter(x => x.id !== s.id); saveStore(state.store); renderAll(); alert(t('toast_deleted')); })
        .catch(() => { alert('操作失败'); });
      return;
    }
    cls.students = (cls.students || []).filter(x => x.id !== s.id);
    persistAndRender(t("toast_deleted"));
    return;
  }

  if (action === "enable") {
    if (typeof s.id === 'number' && typeof cls.id === 'number') {
      apiFetch(`/api/class/${cls.id}/students/${s.id}/status`, { method: 'POST', body: JSON.stringify({ action: 'enable' }) })
        .then(d => { s.status = d.status; saveStore(state.store); renderAll(); alert(t('toast_saved')); })
        .catch(() => { alert('操作失败'); });
      return;
    }
    s.status = "joined"; persistAndRender(t("toast_saved")); return;
  }

  if (action === "disable") {
    if (typeof s.id === 'number' && typeof cls.id === 'number') {
      apiFetch(`/api/class/${cls.id}/students/${s.id}/status`, { method: 'POST', body: JSON.stringify({ action: 'disable' }) })
        .then(d => { s.status = d.status; saveStore(state.store); renderAll(); alert(t('toast_saved')); })
        .catch(() => { alert('操作失败'); });
      return;
    }
    s.status = "disabled"; persistAndRender(t("toast_saved")); return;
  }

  if (action === "remove") {
    if (!confirm(t("confirm_delete_student"))) return;
    if (typeof s.id === 'number' && typeof cls.id === 'number') {
      apiFetch(`/api/class/${cls.id}/students/${s.id}`, { method: 'DELETE' })
        .then(() => { cls.students = (cls.students || []).filter(x => x.id !== s.id); saveStore(state.store); renderAll(); alert(t('toast_deleted')); })
        .catch(() => { alert('操作失败'); });
      return;
    }
    cls.students = (cls.students || []).filter(x => x.id !== s.id);
    persistAndRender(t("toast_deleted"));
    return;
  }
}

/** ---------- Drawer ---------- */
function openDrawer(studentId) {
  const drawer = $("drawer");
  const body = $("drawerBody");
  if (!drawer || !body) return;

  const cls = state.store.classes.find(c => c.id === state.selectedClassId);
  if (!cls) return;
  const local = (cls.students || []).find(x => String(x.id) === String(studentId));
  if (local && typeof local.id === 'number' && typeof cls.id === 'number') {
    // fetch latest from server
    apiFetch(`/api/class/${cls.id}/students/${local.id}`, { method: 'GET' })
      .then(d => { renderDrawerStudent(d); drawer.classList.remove('hidden'); state.drawerStudentId = local.id; })
      .catch(() => { alert('获取学生详情失败'); });
    return;
  }

  if (!local) return;
  state.drawerStudentId = studentId;
  renderDrawerStudent(local);
  drawer.classList.remove("hidden");
}


function renderDrawerStudent(s) {
  const drawer = $("drawer");
  const body = $("drawerBody");
  if (!drawer || !body) return;
  const pill = studentStatusPill(s.status);
  body.innerHTML = `
    <div class="cm-kv">
      <div class="cm-kv__row"><div class="cm-kv__k">${t("thName")}</div><div class="cm-kv__v">${escapeHtml(s.name || "—")}</div></div>
      <div class="cm-kv__row"><div class="cm-kv__k">${t("thId")}</div><div class="cm-kv__v cm-mono">${escapeHtml(s.stu_id || "—")}</div></div>
      <div class="cm-kv__row"><div class="cm-kv__k">${t("thStatus")}</div><div class="cm-kv__v"><span class="cm-pill ${pill.cls}">${pill.text}</span></div></div>
      <div class="cm-kv__row"><div class="cm-kv__k">${t("mParent")}</div><div class="cm-kv__v">${escapeHtml(s.parent_phone || "—")}</div></div>
      <div class="cm-kv__row"><div class="cm-kv__k">${t("thAcc")}</div><div class="cm-kv__v">${typeof s.accuracy==="number" ? s.accuracy+"%" : "—"}</div></div>
      <div class="cm-kv__row"><div class="cm-kv__k">${t("thSubmit")}</div><div class="cm-kv__v">${typeof s.submit==="number" ? s.submit+"%" : "—"}</div></div>
    </div>
  `;
}

function closeDrawer() {
  const drawer = $("drawer");
  if (drawer) drawer.classList.add("hidden");
  state.drawerStudentId = null;
}

/** ---------- Modals ---------- */
function openClassModal(mode) {
  const modal = $("classModal");
  if (!modal) return;

  state.editingClassId = null;
  if ($("classModalTitle")) $("classModalTitle").textContent = (mode === "edit") ? t("classModalTitleEdit") : t("classModalTitleNew");
  if ($("mClassName")) $("mClassName").value = "";
  if ($("mClassDesc")) $("mClassDesc").value = "";

  if (mode === "edit") {
    const cls = state.store.classes.find(c => c.id === state.selectedClassId);
    if (!cls) return;
    state.editingClassId = cls.id;
    if ($("mClassName")) $("mClassName").value = cls.name || "";
    if ($("mClassDesc")) $("mClassDesc").value = cls.desc || "";
    if ($("classModalTitle")) $("classModalTitle").textContent = t("classModalTitleEdit");
  }

  modal.classList.remove("hidden");
}

function closeClassModal() {
  const modal = $("classModal");
  if (modal) modal.classList.add("hidden");
  state.editingClassId = null;
}

function saveClassModal() {
  const name = ($("mClassName")?.value || "").trim();
  const desc = ($("mClassDesc")?.value || "").trim();
  if (!name) return;

  const user = getLoginUser();
  if (state.editingClassId) {
    const cls = state.store.classes.find(c => c.id === state.editingClassId);
    if (!cls) return;
    // if class has numeric id -> server-backed
    if (user && typeof cls.id === 'number') {
      // PATCH
      apiFetch(`/api/class/${cls.id}`, { method: 'PATCH', body: JSON.stringify({ name, desc }) })
        .then((d) => { Object.assign(cls, d); saveStore(state.store); renderAll(); alert(t('toast_saved')); closeClassModal(); })
        .catch(() => { alert('保存失败'); });
      return;
    }
    // local fallback
    cls.name = name;
    cls.desc = desc;
    persistAndRender(t('toast_saved'));
    closeClassModal();
    return;
  }

  // create
  if (user && user.id) {
    apiFetch('/api/class/', { method: 'POST', body: JSON.stringify({ name, desc }) })
      .then(d => {
        // server returns class object
        state.store.classes.unshift(d);
        state.selectedClassId = d.id;
        state.page = 1;
        saveStore(state.store);
        renderAll();
        alert(t('toast_saved'));
        closeClassModal();
      })
      .catch(e => { console.warn(e); alert('创建班级失败'); });
    return;
  }

  // local fallback if not logged in
  const newClass = {
    id: uuid(),
    name,
    desc,
    status: 'active',
    code: randomCode(),
    created_at: nowDate(),
    stage: 'primary',
    allow_join: true,
    note: '',
    students: []
  };
  state.store.classes.unshift(newClass);
  state.selectedClassId = newClass.id;
  state.page = 1;
  persistAndRender(t('toast_saved'));
  closeClassModal();
}

function openStuModal(mode, studentId = null) {
  const modal = $("stuModal");
  if (!modal) return;

  state.editingStudentId = null;

  if ($("stuModalTitle")) $("stuModalTitle").textContent = (mode === "edit") ? t("stuModalTitleEdit") : t("stuModalTitleNew");

  // clear
  if ($("mStuName")) $("mStuName").value = "";
  if ($("mStuId")) $("mStuId").value = "";
  if ($("mStuStatus")) $("mStuStatus").value = "joined";
  if ($("mParentPhone")) $("mParentPhone").value = "";
  if ($("mAccuracy")) $("mAccuracy").value = "";
  if ($("mSubmit")) $("mSubmit").value = "";

  if (mode === "edit") {
    const cls = state.store.classes.find(c => c.id === state.selectedClassId);
    if (!cls) return;
    const s = (cls.students || []).find(x => x.id === studentId);
    if (!s) return;

    state.editingStudentId = s.id;
    if ($("mStuName")) $("mStuName").value = s.name || "";
    if ($("mStuId")) $("mStuId").value = s.stu_id || "";
    if ($("mStuStatus")) $("mStuStatus").value = s.status || "joined";
    if ($("mParentPhone")) $("mParentPhone").value = (s.parent_phone || "").replace(/\*/g,"");
    if ($("mAccuracy")) $("mAccuracy").value = (typeof s.accuracy==="number") ? String(s.accuracy) : "";
    if ($("mSubmit")) $("mSubmit").value = (typeof s.submit==="number") ? String(s.submit) : "";
  }

  modal.classList.remove("hidden");
}

function closeStuModal() {
  const modal = $("stuModal");
  if (modal) modal.classList.add("hidden");
  state.editingStudentId = null;
}

function saveStuModal() {
  const cls = state.store.classes.find(c => c.id === state.selectedClassId);
  if (!cls) return;

  const name = ($("mStuName")?.value || "").trim();
  const stu_id = ($("mStuId")?.value || "").trim();
  const status = $("mStuStatus")?.value || "joined";
  const parent_phone_raw = ($("mParentPhone")?.value || "").trim();
  const accuracy_raw = ($("mAccuracy")?.value || "").trim();
  const submit_raw = ($("mSubmit")?.value || "").trim();

  if (!name || !stu_id) return;

  const accuracy = accuracy_raw === "" ? null : clamp(parseInt(accuracy_raw, 10) || 0, 0, 100);
  const submit = submit_raw === "" ? null : clamp(parseInt(submit_raw, 10) || 0, 0, 100);
  const parent_phone = parent_phone_raw;

  if (state.editingStudentId) {
    const s = (cls.students || []).find(x => x.id === state.editingStudentId);
    if (s) {
      s.name = name;
      s.stu_id = stu_id;
      s.status = status;
      s.parent_phone = parent_phone;
      s.accuracy = accuracy;
      s.submit = submit;
    }
    // if student has numeric id -> update on server
    if (typeof s.id === 'number') {
      apiFetch(`/api/class/${cls.id}/students/${s.id}`, { method: 'PATCH', body: JSON.stringify({ name, stu_id, status, parent_phone, accuracy, submit }) })
        .then(d => { Object.assign(s, d); saveStore(state.store); renderAll(); alert(t('toast_saved')); closeStuModal(); })
        .catch(() => { alert('更新学生失败'); });
      return;
    }

    persistAndRender(t('toast_saved'));
    closeStuModal();
    return;
  }

  cls.students = cls.students || [];
  // if class is server-backed -> POST to server
  if (typeof cls.id === 'number') {
    apiFetch(`/api/class/${cls.id}/students`, { method: 'POST', body: JSON.stringify({ name, stu_id, status, parent_phone, accuracy, submit }) })
      .then(d => {
        cls.students.unshift(d);
        state.page = 1;
        saveStore(state.store);
        renderAll();
        alert(t('toast_saved'));
        closeStuModal();
      })
      .catch(() => { alert('添加学生失败'); });
    return;
  }

  cls.students.unshift({
    id: uuid(),
    name,
    stu_id,
    status,
    parent_phone,
    accuracy,
    submit
  });

  state.page = 1;
  persistAndRender(t('toast_saved'));
  closeStuModal();
}

/** ---------- Class actions ---------- */
function randomCode() {
  const chars = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";
  let out = "";
  for (let i = 0; i < 6; i++) out += chars[Math.floor(Math.random() * chars.length)];
  return out;
}
function maskPhone(phone) {
  if (!phone) return "—";
  const digits = String(phone).replace(/[^\d]/g,"");
  if (digits.length < 7) return phone;
  return digits.slice(0,3) + "****" + digits.slice(-4);
}

function archiveSelected() {
  const cls = state.store.classes.find(c => c.id === state.selectedClassId);
  if (!cls) return;
  if (!confirm(t("confirm_archive_class"))) return;
  if (typeof cls.id === 'number') {
    apiFetch(`/api/class/${cls.id}/archive`, { method: 'POST', body: JSON.stringify({ action: 'archive' }) })
      .then(d => { cls.status = d.status; saveStore(state.store); renderAll(); alert(t('toast_archived')); })
      .catch(() => { alert('操作失败'); });
    return;
  }
  cls.status = "archived";
  persistAndRender(t("toast_archived"));
}

function deleteSelected() {
  const cls = state.store.classes.find(c => c.id === state.selectedClassId);
  if (!cls) return;
  if (!confirm(t("confirm_delete_class"))) return;
  if (typeof cls.id === 'number') {
    apiFetch(`/api/class/${cls.id}`, { method: 'DELETE' })
      .then(() => { state.store.classes = state.store.classes.filter(c => c.id !== cls.id); state.selectedClassId = null; saveStore(state.store); renderAll(); alert(t('toast_deleted')); })
      .catch(() => { alert('删除班级失败'); });
    return;
  }
  state.store.classes = state.store.classes.filter(c => c.id !== cls.id);
  state.selectedClassId = null;
  persistAndRender(t('toast_deleted'));
}

function editSelectedClass() {
  const cls = state.store.classes.find(c => c.id === state.selectedClassId);
  if (!cls) return;
  openClassModal("edit");
}

async function copySelectedCode() {
  const cls = state.store.classes.find(c => c.id === state.selectedClassId);
  if (!cls) return;
  const ok = await copyText(cls.code);
  if (ok) alert(t("toast_copied"));
}

function resetSelectedCode() {
  const cls = state.store.classes.find(c => c.id === state.selectedClassId);
  if (!cls) return;
  if (typeof cls.id === 'number') {
    apiFetch(`/api/class/${cls.id}/reset-code`, { method: 'POST' })
      .then(d => { cls.code = d.code; saveStore(state.store); renderAll(); alert(t('toast_code_reset')); })
      .catch(() => { alert('重置班级码失败'); });
    return;
  }
  cls.code = randomCode();
  persistAndRender(t("toast_code_reset"));
}

function saveClassSettings() {
  const cls = state.store.classes.find(c => c.id === state.selectedClassId);
  if (!cls) return;

  cls.name = ($("setName")?.value || "").trim() || cls.name;
  cls.stage = $("setStage")?.value || cls.stage;
  cls.allow_join = !!$("joinSwitch")?.checked;
  cls.note = ($("setNote")?.value || "").trim();

  persistAndRender(t("toast_saved"));
}

/** ---------- Import/Export ---------- */
function exportClass() {
  const cls = state.store.classes.find(c => c.id === state.selectedClassId);
  if (!cls) return;
  // If this is a persisted class (numeric id), request server Excel export
  if (typeof cls.id === 'number') {
    const API_BASE = 'http://127.0.0.1:5000';
    const user = getLoginUser();
    const headers = { 'X-User-Id': user && user.id ? String(user.id) : '' };
    const url = `${API_BASE}/api/class/${cls.id}/export?format=xlsx`;
    fetch(url, { method: 'GET', headers })
      .then(async (res) => {
        if (!res.ok) throw new Error('export failed');
        const blob = await res.blob();
        const disp = res.headers.get('Content-Disposition') || '';
        let filename = `class_${(cls.name || 'class').replace(/[\\/:*?"<>|]/g,'_')}.xlsx`;
        const m = disp.match(/filename\*=UTF-8''(.+)$|filename="?([^";]+)"?/i);
        if (m) filename = decodeURIComponent(m[1] || m[2] || filename);
        const u = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = u;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(u);
      })
      .catch(() => { alert('导出失败'); });
    return;
  }

  const file = `class_${(cls.name || "class").replace(/[\\/:*?"<>|]/g,"_")}.json`;
  downloadFile(file, JSON.stringify(cls, null, 2));
}

function parseCSV(text) {
  // 支持逗号或制表符分隔（兼容我们提供的 .xls 模板）
  const lines = text.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  if (!lines.length) return [];

  const detectDelimiter = (firstLine) => {
    const commaCnt = (firstLine.match(/,/g) || []).length;
    const tabCnt = (firstLine.match(/\t/g) || []).length;
    if (tabCnt > commaCnt) return "\t";
    return ",";
  };

  const delimiter = detectDelimiter(lines[0]);
  const splitLine = (line) => line.split(delimiter).map(h => h.trim());

  const header = splitLine(lines[0]).map(h => h.toLowerCase());

  // allow chinese headers
  const idxName = header.indexOf("name") !== -1 ? header.indexOf("name") : header.indexOf("姓名");
  const idxId = header.indexOf("stu_id") !== -1 ? header.indexOf("stu_id") : header.indexOf("学号");
  const idxPhone = header.indexOf("parent_phone") !== -1 ? header.indexOf("parent_phone") : header.indexOf("家长电话");
  const idxStatus = header.indexOf("status") !== -1 ? header.indexOf("status") : header.indexOf("状态");
  const idxAcc = header.indexOf("accuracy") !== -1 ? header.indexOf("accuracy") : header.indexOf("正确率");
  const idxSub = header.indexOf("submit") !== -1 ? header.indexOf("submit") : header.indexOf("提交率");

  if (idxName === -1 || idxId === -1) return null;

  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const cols = splitLine(lines[i]);
    const name = cols[idxName] || "";
    const sid = cols[idxId] || "";
    if (!name || !sid) continue;

    const statusRaw = (idxStatus !== -1 ? cols[idxStatus] : "") || "joined";
    const status = normalizeStuStatus(statusRaw);

    const phone = idxPhone !== -1 ? cols[idxPhone] : "";
    const acc = idxAcc !== -1 ? cols[idxAcc] : "";
    const sub = idxSub !== -1 ? cols[idxSub] : "";

    rows.push({
      id: uuid(),
      name,
      stu_id: sid,
      status,
      parent_phone: phone,
      accuracy: acc === "" ? null : clamp(parseInt(acc, 10) || 0, 0, 100),
      submit: sub === "" ? null : clamp(parseInt(sub, 10) || 0, 0, 100)
    });
  }
  return rows;
}

function normalizeStuStatus(v) {
  const s = String(v || "").toLowerCase();
  if (["pending","待审核","审核","wait"].some(x => s.includes(String(x).toLowerCase()))) return "pending";
  if (["disabled","禁用","停用","ban"].some(x => s.includes(String(x).toLowerCase()))) return "disabled";
  if (["joined","已加入","在册","ok","active"].some(x => s.includes(String(x).toLowerCase()))) return "joined";
  return "joined";
}

function downloadRosterTemplate() {
  // XLS (兼容 Excel)：制表符分隔，保存为 .xls 方便直接打开
  const header = ["name", "stu_id", "parent_phone", "status", "accuracy", "submit"].join("\t");
  const rows = [
    ["李雷", "202601001", "13800000000", "已加入", "90", "95"].join("\t"),
    ["韩梅梅", "202601002", "13700000000", "待审核", "", ""].join("\t"),
    ["王一博", "202601003", "13600000000", "已禁用", "70", "60"].join("\t")
  ];
  const content = [header, ...rows].join("\n");
  downloadFile("class_roster_template.xls", content, "application/vnd.ms-excel;charset=utf-8");
}

function importCSVFile(file) {
  const cls = state.store.classes.find(c => c.id === state.selectedClassId);
  if (!cls) return;

   // If Excel file, directly send to backend to avoid text parsing errors
   const lower = (file?.name || '').toLowerCase();
   const isExcel = lower.endsWith('.xls') || lower.endsWith('.xlsx');
   if (isExcel && typeof cls.id === 'number') {
     const form = new FormData();
     form.append('file', file, file.name);
     apiFetchRaw(`/api/class/${cls.id}/import`, { method: 'POST', body: form })
       .then(d => {
         if (d && d.class) {
           const idx = state.store.classes.findIndex(x => x.id === d.class.id);
           if (idx !== -1) state.store.classes[idx] = d.class;
           else state.store.classes.push(d.class);
           saveStore(state.store);
           renderAll();
           alert(t('toast_saved'));
         } else {
           alert(t('toast_saved'));
           fetchAndLoadClasses();
         }
       })
       .catch((err) => {
         const detail = err?.parsed_header ? `\n解析到的表头: ${JSON.stringify(err.parsed_header)}` : '';
         alert(`导入失败: ${err.message || err}${detail}`);
       });
     return;
   }

  const reader = new FileReader();
  reader.onload = () => {
    const text = String(reader.result || "");
    const rows = parseCSV(text);
    if (!rows) {
      alert(t("invalid_csv"));
      return;
    }
    cls.students = cls.students || [];

    // merge: 仅追加，不覆盖已有学生（按 stu_id 去重）
    // If class persisted, upload file to backend (supports csv/xlsx)
    if (typeof cls.id === 'number') {
      const form = new FormData();
      form.append('file', file, file.name);
      apiFetchRaw(`/api/class/${cls.id}/import`, { method: 'POST', body: form })
        .then(d => {
          if (d && d.class) {
            const idx = state.store.classes.findIndex(x => x.id === d.class.id);
            if (idx !== -1) state.store.classes[idx] = d.class;
            else state.store.classes.push(d.class);
            saveStore(state.store);
            renderAll();
            alert(t('toast_saved'));
          } else {
            alert(t('toast_saved'));
            fetchAndLoadClasses();
          }
        })
        .catch((err) => {
          const detail = err?.parsed_header ? `\n解析到的表头: ${JSON.stringify(err.parsed_header)}` : '';
          alert(`导入失败: ${err.message || err}${detail}`);
        });
      return;
    }

    // local demo: append new students only
    rows.forEach(r => {
      const exist = cls.students.find(x => String(x.stu_id) === String(r.stu_id));
      if (exist) return;
      cls.students.push(r);
    });

    state.page = 1;
    persistAndRender(t("toast_saved"));
  };
  reader.readAsText(file, "utf-8");
}

// helper to call backend endpoints with raw body (no JSON header)
async function apiFetchRaw(path, opts = {}) {
  const API_BASE = 'http://127.0.0.1:5000';
  const user = getLoginUser();
  const headers = (opts.headers || {});
  if (user && user.id) headers['X-User-Id'] = String(user.id);
  const url = path.startsWith('http') ? path : (API_BASE + path);
  const res = await fetch(url, Object.assign({}, opts, { headers }));
  let data = null;
  try {
    data = await res.json();
  } catch (e) {
    const txt = await res.text();
    // throw clearer error when server returned non-JSON (e.g., HTML)
    const err = new Error('Non-JSON response from server: ' + (txt ? txt.slice(0,200) : '[empty]'));
    err.rawText = txt;
    throw err;
  }
  if (!res.ok || data.code !== 0) {
    const msg = (data && data.message) ? data.message : ('HTTP ' + res.status);
    const err = new Error(msg || 'api error');
    // attach parsed_header when backend provided it for debugging
    if (data && data.data && data.data.parsed_header) err.parsed_header = data.data.parsed_header;
    throw err;
  }
  return data.data;
}

/** ---------- Persist & Render ---------- */
function persistAndRender(msg) {
  saveStore(state.store);
  renderAll();
  if (msg) {
    // simple toast via alert for now (you can replace with nicer toast later)
    // Keep it non-blocking? We'll use a small top message if you want later.
    alert(msg);
  }
}

function renderAll() {
  applyText();
  renderClassList();
  renderRightPanel();
  // keep filter chips active
  syncFilterChips();
  syncSelects();
}

/** ---------- Sync UI Controls ---------- */
function syncFilterChips() {
  const wrap = $("classStatusFilter");
  if (!wrap) return;
  wrap.querySelectorAll(".cm-chip").forEach(btn => {
    const s = btn.getAttribute("data-status");
    if (s === state.classFilter) btn.classList.add("cm-chip--active");
    else btn.classList.remove("cm-chip--active");
  });
}

function syncSelects() {
  if ($("stuStatusSelect")) $("stuStatusSelect").value = state.stuFilter;
  if ($("stuSortSelect")) $("stuSortSelect").value = state.stuSort;
}

/** ---------- Bind Events ---------- */
function bindEvents() {
  // filter chips
  const filter = $("classStatusFilter");
  safeOn(filter, "click", (e) => {
    const btn = e.target.closest(".cm-chip");
    if (!btn) return;
    const v = btn.getAttribute("data-status") || "all";
    state.classFilter = v;
    // if selected class not in filtered list -> unselect
    const classes = getClassesFiltered();
    if (state.selectedClassId && !classes.some(c => c.id === state.selectedClassId)) {
      state.selectedClassId = null;
    }
    renderAll();
  });

  // new class
  safeOn($("newClassBtn"), "click", () => openClassModal("new"));
  safeOn($("closeClassModal"), "click", closeClassModal);
  safeOn($("cancelClassModal"), "click", closeClassModal);
  safeOn($("saveClassModal"), "click", saveClassModal);

  // right actions
  safeOn($("copyCodeBtn"), "click", (e) => { e.preventDefault(); copySelectedCode(); });
  safeOn($("resetCodeBtn"), "click", (e) => { e.preventDefault(); resetSelectedCode(); });
  safeOn($("downloadTemplateBtn"), "click", (e) => { e.preventDefault(); downloadRosterTemplate(); });
  safeOn($("exportBtn"), "click", (e) => { e.preventDefault(); exportClass(); });
  safeOn($("archiveBtn"), "click", (e) => { e.preventDefault(); archiveSelected(); });
  safeOn($("editClassBtn"), "click", (e) => { e.preventDefault(); editSelectedClass(); });
  safeOn($("deleteClassBtn"), "click", (e) => { e.preventDefault(); deleteSelected(); });

  // csv import
  safeOn($("csvInput"), "change", (e) => {
    const file = e.target.files?.[0];
    if (file) importCSVFile(file);
    e.target.value = "";
  });

  // student controls
  safeOn($("stuStatusSelect"), "change", (e) => {
    state.stuFilter = e.target.value || "all";
    state.page = 1;
    renderAll();
  });
  safeOn($("stuSortSelect"), "change", (e) => {
    state.stuSort = e.target.value || "name";
    renderAll();
  });
  safeOn($("addStudentBtn"), "click", (e) => { e.preventDefault(); openStuModal("new"); });

  safeOn($("closeStuModal"), "click", closeStuModal);
  safeOn($("cancelStuModal"), "click", closeStuModal);
  safeOn($("saveStuModal"), "click", saveStuModal);

  // pagination
  safeOn($("prevPage"), "click", (e) => {
    e.preventDefault();
    state.page = Math.max(1, state.page - 1);
    renderAll();
  });
  safeOn($("nextPage"), "click", (e) => {
    e.preventDefault();
    state.page += 1;
    renderAll();
  });

  // class settings save
  safeOn($("saveSettingsBtn"), "click", (e) => { e.preventDefault(); saveClassSettings(); });

  // drawer
  safeOn($("closeDrawer"), "click", closeDrawer);
  safeOn($("drawer"), "click", (e) => {
    // click backdrop closes
    if (e.target && e.target.id === "drawer") closeDrawer();
  });
  safeOn($("drawerEdit"), "click", () => {
    const cls = state.store.classes.find(c => c.id === state.selectedClassId);
    if (!cls) return;
    const s = (cls.students || []).find(x => x.id === state.drawerStudentId);
    if (!s) return;
    closeDrawer();
    openStuModal("edit", s.id);
  });
  safeOn($("drawerRemove"), "click", () => {
    const cls = state.store.classes.find(c => c.id === state.selectedClassId);
    if (!cls) return;
    const s = (cls.students || []).find(x => x.id === state.drawerStudentId);
    if (!s) return;
    if (!confirm(t("confirm_delete_student"))) return;
    if (typeof s.id === 'number' && typeof cls.id === 'number') {
      apiFetch(`/api/class/${cls.id}/students/${s.id}`, { method: 'DELETE' })
        .then(() => { cls.students = (cls.students || []).filter(x => x.id !== s.id); closeDrawer(); saveStore(state.store); renderAll(); alert(t('toast_deleted')); })
        .catch(() => { alert('删除学生失败'); });
      return;
    }
    cls.students = (cls.students || []).filter(x => x.id !== s.id);
    closeDrawer();
    persistAndRender(t('toast_deleted'));
  });

  // close modals when click backdrop
  safeOn($("classModal"), "click", (e) => { if (e.target && e.target.id === "classModal") closeClassModal(); });
  safeOn($("stuModal"), "click", (e) => { if (e.target && e.target.id === "stuModal") closeStuModal(); });

  // listen locale changes from settings page (if you update localStorage then come back)
  window.addEventListener("storage", (e) => {
    if (e.key === "locale") renderAll();
  });

  // optional: when user changes locale in same tab, some pages dispatch custom event
  window.addEventListener("cm_locale_changed", () => renderAll());
}

/** ---------- Escape HTML (security for demo) ---------- */
function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

/** ---------- Init ---------- */
function getLoginUser() {
  try { return JSON.parse(localStorage.getItem('login_user') || 'null'); } catch { return null; }
}

async function apiFetch(path, opts = {}) {
  const API_BASE = 'http://127.0.0.1:5000';
  const user = getLoginUser();
  const headers = (opts.headers || {});
  headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  if (user && user.id) headers['X-User-Id'] = String(user.id);
  const url = path.startsWith('http') ? path : (API_BASE + path);
  const res = await fetch(url, Object.assign({}, opts, { headers }));
  const data = await res.json();
  if (!res.ok || data.code !== 0) throw new Error(data.message || 'api error');
  return data.data;
}

async function fetchAndLoadClasses() {
  const user = getLoginUser();
  if (!user || !user.id) return;
  try {
    const data = await apiFetch('/api/class/?status=all', { method: 'GET' });
    // data is an array
    state.store.classes = data.map(c => Object.assign({}, c));
    // ensure selected class stays valid
    const prefer = state.store.classes.find(c => c.status === 'active');
    state.selectedClassId = prefer ? prefer.id : (state.store.classes[0]?.id || null);
    saveStore(state.store);
    renderAll();
  } catch (e) {
    console.warn('fetch classes failed', e);
  }
}
function init() {
  // If teacher.js does login check, fine. We won't duplicate.
  // Choose first active class by default
  const candidates = getClassesFiltered();
  const prefer = state.store.classes.find(c => c.status === "active");
  state.selectedClassId = prefer ? prefer.id : (candidates[0]?.id || null);

  // initial selects
  if ($("stuStatusSelect")) $("stuStatusSelect").value = state.stuFilter;
  if ($("stuSortSelect")) $("stuSortSelect").value = state.stuSort;

  bindEvents();
  renderAll();
  // if logged in, fetch classes from backend
  const user = getLoginUser();
  if (user && user.id) fetchAndLoadClasses();
}

document.addEventListener("DOMContentLoaded", init);

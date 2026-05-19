import { createContext, useContext, useEffect, useMemo, useState } from "react";

const dictionaries = {
  zh: {
    appName: "AI 辅助备课系统",
    teacherPortal: "教师端",
    studentPortal: "学生端",
    signIn: "登录",
    signUp: "注册",
    signOut: "退出登录",
    email: "邮箱",
    password: "密码",
    confirmPassword: "确认密码",
    name: "姓名",
    studentId: "学号",
    rememberMe: "记住我",
    forgotPassword: "忘记密码？",
    goToLogin: "去登录",
    goToRegister: "创建账号",
    language: "语言",
    required: "请填写完整信息",
    invalidEmail: "请输入有效邮箱",
    passwordMismatch: "两次密码不一致",
    passwordTooShort: "密码至少 6 位",
    loginFailed: "登录失败，请检查账号或密码",
    registerSuccess: "注册成功，请登录",
    networkError: "无法连接后端服务",
    studentSignupDisabled: "学生账号由教师分配，请联系教师获取学号和初始密码。",
    dashboard: "学习分析",
    lesson: "教案生成",
    ppt: "PPT 生成",
    exercise: "习题设计",
    resource: "资源管理",
    review: "作业批改",
    knowledge: "知识库",
    validation: "验证日志",
    classManagement: "班级管理",
    settings: "设置",
    overview: "学习概览",
    practice: "练习",
    lessons: "教案资源",
    scores: "成绩与学情",
    refresh: "刷新",
    exportOverview: "导出概览",
    loading: "加载中",
    noData: "暂无数据",
    loadFailed: "加载失败",
    students: "学生数",
    activeStudents: "活跃学生",
    submissionRate: "提交率",
    accuracy: "正确率",
    pending: "待处理",
    classOverview: "班级概览",
    aiAdvice: "AI 教学建议",
    rewardList: "奖励名单",
    monthlyTrend: "月趋势",
    weeklyTrend: "周趋势",
    todoAssignments: "待完成作业",
    practiceThisWeek: "本周练习",
    latestScore: "最近成绩",
    learningInsights: "个人学情分析",
    weakSpot: "薄弱知识点",
    studyState: "学习状态",
    suggestion: "建议",
    start: "开始",
    save: "保存",
    upload: "上传",
    changePassword: "修改密码",
    currentPassword: "当前密码",
    newPassword: "新密码",
    fontSize: "字号",
    small: "小",
    medium: "中",
    large: "大",
    saved: "已保存"
  },
  en: {
    appName: "AI Lesson Planner",
    teacherPortal: "Teacher",
    studentPortal: "Student",
    signIn: "Sign in",
    signUp: "Sign up",
    signOut: "Sign out",
    email: "Email",
    password: "Password",
    confirmPassword: "Confirm password",
    name: "Name",
    studentId: "Student ID",
    rememberMe: "Remember me",
    forgotPassword: "Forgot password?",
    goToLogin: "Go to sign in",
    goToRegister: "Create account",
    language: "Language",
    required: "Please complete all fields",
    invalidEmail: "Please enter a valid email",
    passwordMismatch: "Passwords do not match",
    passwordTooShort: "Password must be at least 6 characters",
    loginFailed: "Login failed. Check your account or password.",
    registerSuccess: "Account created. Please sign in.",
    networkError: "Backend service is not reachable",
    studentSignupDisabled: "Student accounts are assigned by teachers. Ask your teacher for your student ID and initial password.",
    dashboard: "Learning Analytics",
    lesson: "Lesson Planner",
    ppt: "PPT Generator",
    exercise: "Exercise Builder",
    resource: "Resource Manager",
    review: "Review",
    knowledge: "Knowledge Base",
    validation: "Validation Logs",
    classManagement: "Class Management",
    settings: "Settings",
    overview: "Overview",
    practice: "Practice",
    lessons: "Lessons",
    scores: "Scores & Insights",
    refresh: "Refresh",
    exportOverview: "Export Overview",
    loading: "Loading",
    noData: "No data",
    loadFailed: "Load failed",
    students: "Students",
    activeStudents: "Active",
    submissionRate: "Submission",
    accuracy: "Accuracy",
    pending: "Pending",
    classOverview: "Class Overview",
    aiAdvice: "AI Advice",
    rewardList: "Reward List",
    monthlyTrend: "Monthly Trend",
    weeklyTrend: "Weekly Trend",
    todoAssignments: "Pending Assignments",
    practiceThisWeek: "Practice This Week",
    latestScore: "Latest Score",
    learningInsights: "Learning Insights",
    weakSpot: "Weak Point",
    studyState: "Study State",
    suggestion: "Suggestion",
    start: "Start",
    save: "Save",
    upload: "Upload",
    changePassword: "Change Password",
    currentPassword: "Current password",
    newPassword: "New password",
    fontSize: "Font size",
    small: "Small",
    medium: "Medium",
    large: "Large",
    saved: "Saved"
  }
};

const I18nContext = createContext(null);

function normalize(locale) {
  return String(locale || "zh").toLowerCase().startsWith("en") ? "en" : "zh";
}

export function I18nProvider({ children }) {
  const [locale, setLocaleState] = useState(() => normalize(localStorage.getItem("locale")));

  useEffect(() => {
    document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
    document.documentElement.dataset.font = localStorage.getItem("font_size") || "medium";
  }, [locale]);

  const value = useMemo(() => ({
    locale,
    setLocale(next) {
      const normalized = normalize(next);
      localStorage.setItem("locale", normalized);
      document.documentElement.lang = normalized === "zh" ? "zh-CN" : "en";
      setLocaleState(normalized);
    },
    t(key) {
      return dictionaries[locale]?.[key] || dictionaries.zh[key] || key;
    }
  }), [locale]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) throw new Error("useI18n must be used inside I18nProvider");
  return context;
}

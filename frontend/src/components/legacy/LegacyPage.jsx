import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const routeMap = {
  "login.html": "/login",
  "register.html": "/register",
  "teacher/index.html": "/teacher",
  "teacher/lesson.html": "/teacher/lesson",
  "teacher/ppt.html": "/teacher/ppt",
  "teacher/exercise.html": "/teacher/exercise",
  "teacher/resource.html": "/teacher/resource",
  "teacher/review.html": "/teacher/review",
  "teacher/knowledge.html": "/teacher/knowledge",
  "teacher/validation.html": "/teacher/validation",
  "teacher/class_management.html": "/teacher/class",
  "teacher/settings.html": "/teacher/settings",
  "student/login.html": "/student/login",
  "student/register.html": "/student/register",
  "student/index.html": "/student",
  "student/practice.html": "/student/practice",
  "student/practice_do.html": "/student/practice-do",
  "student/review.html": "/student/review",
  "student/lessons.html": "/student/lessons",
  "student/scores.html": "/student/scores",
  "student/settings.html": "/student/settings",
  "student/exam.html": "/student/exam"
};

const teacherRoutes = {
  "./index.html": "/teacher",
  "./lesson.html": "/teacher/lesson",
  "./ppt.html": "/teacher/ppt",
  "./exercise.html": "/teacher/exercise",
  "./resource.html": "/teacher/resource",
  "./review.html": "/teacher/review",
  "./knowledge.html": "/teacher/knowledge",
  "./validation.html": "/teacher/validation",
  "./class_management.html": "/teacher/class",
  "./settings.html": "/teacher/settings",
  "../login.html": "/login"
};

const studentRoutes = {
  "./index.html": "/student",
  "./practice.html": "/student/practice",
  "./practice_do.html": "/student/practice-do",
  "./review.html": "/student/review",
  "./lessons.html": "/student/lessons",
  "./scores.html": "/student/scores",
  "./settings.html": "/student/settings",
  "./login.html": "/student/login",
  "./register.html": "/student/register",
  "./exam.html": "/student/exam",
  "../login.html": "/login"
};

const rootRoutes = {
  "./login.html": "/login",
  "./register.html": "/register",
  "./teacher/index.html": "/teacher",
  "./student/login.html": "/student/login"
};

function normalizeLegacyPath(value, pageSrc) {
  if (!value || value.startsWith("#") || value.startsWith("mailto:") || value.startsWith("tel:")) {
    return null;
  }

  const url = new URL(value, new URL(pageSrc, window.location.origin));
  if (url.origin !== window.location.origin) return null;

  const key = url.pathname.replace(/^\/+/, "");
  const route = routeMap[key];
  return route ? `${route}${url.search}${url.hash}` : null;
}

function replaceAll(value, replacements) {
  let next = value;
  Object.entries(replacements).forEach(([from, to]) => {
    next = next.split(from).join(to);
  });
  return next;
}

function rewriteLegacyText(value, pageSrc) {
  const scopedRoutes = pageSrc.startsWith("/teacher/")
    ? teacherRoutes
    : pageSrc.startsWith("/student/")
      ? studentRoutes
      : rootRoutes;

  return replaceAll(replaceAll(value, rootRoutes), scopedRoutes);
}

function absoluteAssetUrl(value, pageSrc) {
  return new URL(value, new URL(pageSrc, window.location.origin)).pathname;
}

export default function LegacyPage({ src, title }) {
  const containerRef = useRef(null);
  const location = useLocation();
  const navigate = useNavigate();
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    const cleanupNodes = [];
    const pageSrc = src.startsWith("/") ? src : `/${src}`;

    async function runScript(script) {
      const originalSrc = script.getAttribute("src");
      let code = script.textContent || "";

      if (originalSrc) {
        const scriptUrl = absoluteAssetUrl(originalSrc, pageSrc);
        const response = await fetch(scriptUrl);
        if (!response.ok) throw new Error(`Failed to load ${scriptUrl}`);
        code = await response.text();
      }

      const executable = document.createElement("script");
      executable.textContent = rewriteLegacyText(code, pageSrc);
      document.body.appendChild(executable);
      cleanupNodes.push(executable);
    }

    async function loadPage() {
      setError("");
      const response = await fetch(`${pageSrc}${location.search || ""}`);
      if (!response.ok) throw new Error(`Failed to load ${pageSrc}`);
      const html = await response.text();
      if (cancelled) return;

      const parser = new DOMParser();
      const doc = parser.parseFromString(html, "text/html");
      document.title = doc.querySelector("title")?.textContent || title || "AI Lesson Planner";

      doc.querySelectorAll("link[rel='stylesheet']").forEach((link) => {
        const href = link.getAttribute("href");
        if (!href) return;
        const styleLink = document.createElement("link");
        styleLink.rel = "stylesheet";
        styleLink.href = absoluteAssetUrl(href, pageSrc);
        styleLink.dataset.reactLegacy = pageSrc;
        document.head.appendChild(styleLink);
        cleanupNodes.push(styleLink);
      });

      const scripts = Array.from(doc.querySelectorAll("script"));
      scripts.forEach((script) => script.remove());

      if (containerRef.current) {
        containerRef.current.innerHTML = rewriteLegacyText(doc.body.innerHTML, pageSrc);
      }

      for (const script of scripts) {
        if (cancelled) return;
        await runScript(script);
      }

      document.dispatchEvent(new Event("DOMContentLoaded", { bubbles: true }));
      window.dispatchEvent(new Event("load"));
    }

    loadPage().catch((err) => {
      if (!cancelled) setError(err.message || "Page load failed");
    });

    return () => {
      cancelled = true;
      cleanupNodes.forEach((node) => node.remove());
      if (containerRef.current) containerRef.current.innerHTML = "";
    };
  }, [src, title, location.search]);

  function handleClick(event) {
    const anchor = event.target.closest?.("a[href]");
    if (!anchor) return;

    const nextRoute = normalizeLegacyPath(anchor.getAttribute("href"), src);
    if (!nextRoute) return;

    event.preventDefault();
    navigate(nextRoute);
  }

  return (
    <div className="react-legacy-page">
      {error ? <div className="react-legacy-error">{error}</div> : null}
      <div ref={containerRef} onClick={handleClick} />
    </div>
  );
}

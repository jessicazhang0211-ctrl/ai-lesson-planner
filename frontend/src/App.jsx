import { Navigate, Route, Routes } from "react-router-dom";
import LegacyPage from "./components/legacy/LegacyPage.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<LegacyPage src="/login.html" title="Teacher Login" />} />
      <Route path="/register" element={<LegacyPage src="/register.html" title="Teacher Register" />} />

      <Route path="/teacher" element={<LegacyPage src="/teacher/index.html" title="Teacher Dashboard" />} />
      <Route path="/teacher/lesson" element={<LegacyPage src="/teacher/lesson.html" title="Lesson Planner" />} />
      <Route path="/teacher/ppt" element={<LegacyPage src="/teacher/ppt.html" title="PPT Generator" />} />
      <Route path="/teacher/exercise" element={<LegacyPage src="/teacher/exercise.html" title="Exercise Builder" />} />
      <Route path="/teacher/resource" element={<LegacyPage src="/teacher/resource.html" title="Resource Manager" />} />
      <Route path="/teacher/review" element={<LegacyPage src="/teacher/review.html" title="Review" />} />
      <Route path="/teacher/knowledge" element={<LegacyPage src="/teacher/knowledge.html" title="Knowledge Base" />} />
      <Route path="/teacher/validation" element={<LegacyPage src="/teacher/validation.html" title="Validation Logs" />} />
      <Route path="/teacher/class" element={<LegacyPage src="/teacher/class_management.html" title="Class Management" />} />
      <Route path="/teacher/settings" element={<LegacyPage src="/teacher/settings.html" title="Teacher Settings" />} />

      <Route path="/student/login" element={<LegacyPage src="/student/login.html" title="Student Login" />} />
      <Route path="/student/register" element={<LegacyPage src="/student/register.html" title="Student Register" />} />
      <Route path="/student" element={<LegacyPage src="/student/index.html" title="Student Dashboard" />} />
      <Route path="/student/practice" element={<LegacyPage src="/student/practice.html" title="Student Practice" />} />
      <Route path="/student/practice-do" element={<LegacyPage src="/student/practice_do.html" title="Practice" />} />
      <Route path="/student/review" element={<LegacyPage src="/student/review.html" title="Student Review" />} />
      <Route path="/student/lessons" element={<LegacyPage src="/student/lessons.html" title="Student Lessons" />} />
      <Route path="/student/scores" element={<LegacyPage src="/student/scores.html" title="Student Scores" />} />
      <Route path="/student/settings" element={<LegacyPage src="/student/settings.html" title="Student Settings" />} />
      <Route path="/student/exam" element={<LegacyPage src="/student/exam.html" title="Student Exam" />} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

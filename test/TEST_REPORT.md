# 自动化测试报告

- 执行时间：2026-03-15 08:27:21
- 测试地址：http://127.0.0.1:5000
- 总用例数：17
- 通过：17
- 失败：0

## 关键上下文

- 教师测试账号：teacher_62bzov@example.test
- 学生测试学号：2026009001
- 测试班级ID：9

## 用例结果

1. health_check - PASS - 40.14 ms
   - detail: health ok
2. teacher_register - PASS - 164.89 ms
   - detail: uid=56
3. teacher_login - PASS - 166.57 ms
   - detail: token ok
4. student_self_register_blocked - PASS - 27.03 ms
   - detail: blocked as expected
5. create_class - PASS - 20.74 ms
   - detail: class_id=9
6. list_classes - PASS - 27.21 ms
   - detail: total=1
7. get_class_detail - PASS - 16.55 ms
   - detail: detail ok
8. list_public_classes - PASS - 14.21 ms
   - detail: public_count=8
9. teacher_overview - PASS - 17.24 ms
   - detail: overview ok
10. import_students_json - PASS - 174.92 ms
   - detail: stu_id=2026009001
11. student_login - PASS - 293.87 ms
   - detail: student login ok (must change password)
12. student_assignments - PASS - 168.44 ms
   - detail: blocked before password change
13. student_change_password - PASS - 616.0 ms
   - detail: student password changed and relogin ok
14. student_assignments_after_change - PASS - 152.26 ms
   - detail: assignments=0
15. get_me - PASS - 23.29 ms
   - detail: get me ok
16. update_me - PASS - 22.01 ms
   - detail: update me ok
17. change_password_and_relogin - PASS - 465.95 ms
   - detail: password changed and relogin ok

## 结论

本轮自动化测试全部通过，核心业务链路可用。
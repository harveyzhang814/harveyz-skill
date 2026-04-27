# 用户 API

## 创建用户

`POST /api/users`

参数：
- `username`: 用户名
- `email`: 邮箱
- `password`: 密码
- `role`: 角色（可选）

返回创建成功的用户对象。

## 获取用户

`GET /api/users/:id`

通过 ID 获取用户信息。

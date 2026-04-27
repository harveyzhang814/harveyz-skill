# API 端点参考

## POST /api/users

创建新用户。

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `username` | string | 是 | 用户名，3-32 个字符，仅限字母数字和下划线 |
| `email` | string | 是 | 有效的电子邮件地址 |
| `password` | string | 是 | 密码，至少 8 个字符 |
| `role` | string | 否 | 用户角色，可选值：`user`（默认）、`admin`、`moderator` |

### 响应

**成功（201 Created）**
```json
{
  "id": "usr_abc123",
  "username": "johndoe",
  "email": "john@example.com",
  "role": "user",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**失败（400 Bad Request）**
```json
{
  "error": "validation_failed",
  "message": "email already exists"
}
```

### 错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| `validation_failed` | 400 | 请求参数验证失败 |
| `email_exists` | 409 | 邮箱已被注册 |
| `username_exists` | 409 | 用户名已被使用 |

---

## GET /api/users/:id

获取指定用户信息。

### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | string | 用户 ID，格式为 `usr_` 前缀加 6 位字母数字 |

### 响应

**成功（200 OK）**
```json
{
  "id": "usr_abc123",
  "username": "johndoe",
  "email": "john@example.com",
  "role": "user",
  "created_at": "2024-01-15T10:30:00Z",
  "last_login": "2024-01-20T08:15:00Z"
}
```

**失败（404 Not Found）**
```json
{
  "error": "not_found",
  "message": "user not found"
}
```

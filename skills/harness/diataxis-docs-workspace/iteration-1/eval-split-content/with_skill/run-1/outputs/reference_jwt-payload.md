# JWT Payload 字段参考

本系统签发的 JWT token 包含以下 payload 字段。

## 标准字段（RFC 7519）

| 字段 | 类型 | 说明 |
|------|------|------|
| `sub` | string | Subject — 用户 ID |
| `iat` | number | Issued At — 签发时间（Unix 时间戳） |
| `exp` | number | Expiration Time — 过期时间（Unix 时间戳） |

## 自定义字段

| 字段 | 类型 | 可能的值 | 说明 |
|------|------|----------|------|
| `role` | string | `user` \| `admin` \| `moderator` | 用户角色，用于权限控制 |
| `scope` | string[] | `read` \| `write` \| `delete` | 授权范围（可选，默认 `["read"]`） |

## 示例 Payload

```json
{
  "sub": "usr_abc123",
  "role": "admin",
  "scope": ["read", "write"],
  "iat": 1705312200,
  "exp": 1705917000
}
```

## 注意事项

- Payload 不加密，仅签名验证完整性。不应存储密码等敏感信息。
- `exp` 默认为签发后 7 天，可通过 `JWT_EXPIRES_IN` 环境变量配置。

> 配置步骤参见 [如何配置 JWT 认证](../how-to/configure-jwt-auth.md)。

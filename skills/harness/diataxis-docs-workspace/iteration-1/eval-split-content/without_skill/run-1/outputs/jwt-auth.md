# JWT 认证

## 配置步骤

1. 安装 `jsonwebtoken`：`npm install jsonwebtoken`
2. 设置 `.env`：`JWT_SECRET=your-key`
3. 生成 token：`jwt.sign({ sub: userId }, secret, { expiresIn: '7d' })`
4. 验证 token：`jwt.verify(token, secret)`

## Payload 字段

| 字段 | 说明 |
|------|------|
| `sub` | 用户 ID |
| `role` | 用户角色（user/admin） |
| `iat` | 签发时间 |
| `exp` | 过期时间 |

不要在 payload 中存储敏感信息，payload 仅签名不加密。

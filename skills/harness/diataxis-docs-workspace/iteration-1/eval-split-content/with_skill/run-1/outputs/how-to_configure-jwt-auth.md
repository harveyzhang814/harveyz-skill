# 如何配置 JWT 认证

## 前提条件

- 已安装 `jsonwebtoken` 包：`npm install jsonwebtoken`
- 已有用户数据库

## 步骤

### 1. 配置密钥

在 `.env` 中设置：

```
JWT_SECRET=your-secret-key-here
JWT_EXPIRES_IN=7d
```

### 2. 生成 Token

```js
const jwt = require('jsonwebtoken');

function generateToken(userId, role) {
  return jwt.sign(
    { sub: userId, role },
    process.env.JWT_SECRET,
    { expiresIn: process.env.JWT_EXPIRES_IN }
  );
}
```

### 3. 验证中间件

```js
function requireAuth(req, res, next) {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) return res.status(401).json({ error: 'unauthorized' });

  try {
    req.user = jwt.verify(token, process.env.JWT_SECRET);
    next();
  } catch {
    res.status(401).json({ error: 'invalid_token' });
  }
}
```

### 4. 应用到路由

```js
app.get('/api/profile', requireAuth, (req, res) => {
  res.json({ userId: req.user.sub });
});
```

## 常见问题

**Token 过期** — 客户端需捕获 401 响应并重新登录获取新 token。

> 参见 [JWT Payload 字段参考](../reference/jwt-payload.md) 了解 payload 结构。

# 如何集成支付功能

## 前提条件

- 已有 Stripe 账号和 API 密钥
- Node.js 项目已完成基础配置

## 步骤

### 1. 安装 Stripe SDK

```bash
npm install stripe
```

### 2. 配置环境变量

在 `.env` 中添加：

```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
```

### 3. 创建支付意图

```js
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);

async function createPaymentIntent(amount, currency = 'usd') {
  const paymentIntent = await stripe.paymentIntents.create({
    amount: amount * 100, // 单位：分
    currency,
  });
  return paymentIntent.client_secret;
}
```

### 4. 前端集成

在 HTML 中引入 Stripe.js 并使用 `client_secret` 完成支付确认。

## 常见问题

**支付失败** — 检查 API 密钥是否正确，确认使用 test 密钥进行测试。

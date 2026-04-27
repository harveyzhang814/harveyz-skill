# 集成支付功能

安装 Stripe SDK：

```bash
npm install stripe
```

配置环境变量后创建支付意图：

```js
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
const intent = await stripe.paymentIntents.create({ amount: 1000, currency: 'usd' });
```

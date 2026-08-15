# QM 的横切件：一行代码的防线，和四个小目录

> 关联文档：
> - [[qm-overview]]（产品目标、八条哲学、十组模块分解）
> - [[qm-memory-layer]]（记忆层的逐文件深入分析）
> - [[qm-execution-layer]]（执行环境层深入分析，不含 skills）
> - [[qm-skills-layer]]（技能层深入分析——注册表、Pack 导入、物化、权限）
> - [[qm-resolution-layer]]（解析层深入分析——`Resolution` 对象、分层配置、audience floor、prompt 协议）
> - [[qm-turn-slice]]（纵切面——一条 Slack 消息从进入到回复送出，十九道闸门）
> - [[qm-harness-layer]]（Harness 层——四适配器一套接口、tape 事件溯源、上下文压缩、冷启动重放）
> - [[qm-run-lifecycle]]（执行内核的运行时——租约、排空、回收、中断重入）
> - [[qm-authz-layer]]（授权与安全层——身份、能力令牌、ACL、命令策略、安全姿态）
> - [[qm-credentials-layer]]（凭证层——借还协议、OAuth、加密盒、连接器状态缓存）
> - [[qm-autonomy-layer]]（自主工作层——cron、monitor、触发器主干、无人在场的回合）
> - [[qm-publish-layer]]（发布层——`publish` 把工作区目录变成持久内部 Web 应用）
> - [[qm-surface-mirror]]（镜像层——`surface-cache/` 不是缓存；ambient 决定何时主动开口）
> - [[qm-assembly-layer]]（装配层——两个手写 ReDoS 分析器的对照；`orgId()` 全局与多租户预留缝）
> - [[qm-synthesis]]（综述——本篇的 `shq` 与 `swallow` 进入「只出现一次但值得单拎」，并附本次重数的覆盖率）
> - [[qm-surface-layer]]（表面层——反向代理头的第三种强度：请求侧允许名单 vs 响应侧删除名单）
>
> 调研对象：`yc-software/qm`（YC 出品的开源多人 agent harness）
> 本地路径：`~/Repositories/qm`
> 调研时间：2026-08-15
> 仓库版本：`main` @ `0f0e0ad`
>
> 阅读范围：`src/util/`（13 文件 357 行）、`src/projects/`（1 文件 236 行）、
> `src/audit/`（1 文件 44 行）、`src/onboarding/`（1 文件 75 行），共 16 个文件 712 行；
> 另核对 `src/admin/scoped-event-sink.ts` 的事件汇工厂、
> `src/resolution/scope-membership.ts` 里 `managedGroups` 的消费点
>
> **本篇是收尾。** 这些目录小到没进过 [[qm-overview]] 的 A–J 分组，但其中几个
> 文件被全仓引用近百次——它们是别的篇章一直在用却从没打开过的零件。

---

## 一、这一篇在收什么尾

前十三篇按模块切分，剩下这四个目录切不进任何一组，因为它们**横切**所有组。
`util/` 平均每个文件 27 行，最长 67 行；`errors.ts` 只有 14 行，却被 88 个文件
import——是全仓引用最广的模块。

小不等于不重要。这一篇挑出真正有内容的部分：**几处只有一两行但承担了整个仓库
某一类安全责任的代码**，以及三个各自只有一个文件、却各自表达了一个完整想法的
小目录。

---

## 二、一行代码的防线

### 2.1 `shq`：整个仓库的命令注入防线

```ts
export const shq = (s: string): string => `'${s.replace(/'/g, `'\\''`)}'`;
```

`src/util/shell.ts` 全文就这一行，被 15 个文件引用。

POSIX 单引号内除了单引号本身之外一切都是字面量，所以只需要处理单引号：闭合、
插一个转义的单引号、再重新开引号（`'` → `'\''`）。这是唯一正确且完整的
POSIX shell 转义。

这一层的重要性怎么强调都不过分：[[qm-execution-layer]] 讲的 `execute` 工具、
[[qm-publish-layer]] §5.3 里 AWS provider 往 microVM 里写的那些 shell 脚本、
凭证注入时的 `export K=v`——**所有把变量拼进 shell 命令的地方，正确性都压在
这一行上**。

值得学的是它的形态：不是一个「shell 工具类」，是一个导出的箭头函数。
**一个安全原语如果足够小，就该小到没有人想绕过它。**

### 2.2 `hashId`：用 NUL 当分隔符

```ts
export function hashId(parts: readonly string[], len = 16): string {
  return createHash("sha256").update(parts.join("\0")).digest("hex").slice(0, len);
}
export const shortHash = (s: string): string => hashId([s], 6);
```

分隔符是 `\0` 而不是 `:` 或 `|`。因为后者可能出现在被拼接的内容里，于是
`["a:b", "c"]` 和 `["a", "b:c"]` 会哈希成同一个值——**拼接歧义**。
NUL 在几乎所有文本内容里都不合法，所以它是这里唯一安全的分隔符。

这个函数是 [[qm-autonomy-layer]] §4.3 里 cron 内容去重 id 和 fire threadRef
的来源。cron 的去重 id 由 owner、schedule、action、message、destination、
runAs、members、title 八段拼成——如果分隔符可以出现在内容里，两个不同的 cron
就可能被判成同一个而静默合并。

顺带一个对照：同一个字节在 `text.ts` 里是**被禁止的**——

```ts
export function jsonbSafeStringify(value: unknown): string {
  return JSON.stringify(value, (_k, v) => (typeof v === "string" ? v.replace(/\u0000/g, "") : v));
}
```

Postgres 的 `jsonb` 不接受 NUL。**同一个字节，在哈希里是分隔符，在存储里是
禁忌**——这不是矛盾，而是「它不会出现在合法内容里」这个同一性质的两种用法。

### 2.3 `constantTimeEqual`：先比长度

```ts
export function constantTimeEqual(a: string, b: string): boolean {
  const ab = Buffer.from(a);
  const bb = Buffer.from(b);
  return ab.length === bb.length && timingSafeEqual(ab, bb);
}
```

`timingSafeEqual` 在长度不等时**会抛异常**，所以必须先比长度再调它。
短路的 `&&` 保证了这个顺序。[[qm-publish-layer]] §9.2 里 `viewer-session.ts`
手写了同样的两步。同一个正确性要点在仓库里出现两次，一次做成了工具函数、
一次是内联的——后者是因为它比较的是 base64url 字符串而不是任意串。

---

## 三、同一个威胁，两种答案

`util/safe-regex.ts`（67 行）是 `util/` 里唯一有真算法的文件。

```ts
if (/\\[1-9]|\\k<|\(\?[=!<]/.test(pattern)) throw new Error("backreferences and lookarounds are not supported");
```

先一刀砍掉反向引用和前后瞻——这两类本身就能造出指数级回溯。然后是一个手写的
字符扫描器，维护四个状态：是否在转义中、是否在字符类里、一个分组栈
（每个分组记 `{quantified, alternation}`）、以及「上一个字符是不是量词」。

核心判据只有一行：

```ts
const quantifier = ch === "*" || ch === "+" || (ch === "?" && pattern[i - 1] !== "(") || ch === "{";
if (quantifier) {
  if (previousQuantifier || (closed && (closed.quantified || closed.alternation))) {
    throw new Error("nested or ambiguous repetition is not supported");
  }
  ...
```

三种被拒的形状：

| 形状 | 例子 | 判据 |
| --- | --- | --- |
| 相邻量词 | `a**`、`a+*` | `previousQuantifier` |
| 量词套量词 | `(a+)+` | 刚闭合的分组 `quantified` |
| 量词套交替 | `(a\|b)+` | 刚闭合的分组 `alternation` |

`(ch === "?" && pattern[i - 1] !== "(")` 是个必要的例外：`(?:` `(?<` 里的 `?`
不是量词。

**它不度量复杂度，只拒绝两三种已知会爆炸的语法形状。** 保守、便宜、
不需要任何回溯分析。代价是会误伤一些良性的正则（`(ab)+` 明明是安全的），
但对「管理员偶尔写一条命令策略规则」这个用途来说完全可接受。

它只服务一个调用点：`policy/command-policy.ts` 里用户可配置的命令规则
（[[qm-authz-layer]] §6）。

### 3.1 和 monitor pattern 的对照

[[qm-autonomy-layer]] §9.5 里 `compileMonitorPattern` 面对**同一个威胁**，
给的答案完全不同——**禁掉所有正则元字符**，只留字面量、`|`、`^`、`$`，
四种匹配全部落到 `===` / `startsWith` / `endsWith` / `includes`。

两个选择的差别不在技术上，在**谁写这个模式、它对着什么跑**：

| | `compileSafeRegex` | `compileMonitorPattern` |
| --- | --- | --- |
| 谁写 | 管理员，在后台配置命令策略 | **模型**，在一次工具调用里 |
| 对着什么跑 | 一条命令字符串 | **无界的日志流，每 10 秒一遍** |
| 写错的代价 | 一条规则不生效 | 轮询器挂死 |
| 答案 | 保留正则，砍掉危险形状 | 砍掉整个正则 |

**同一个仓库里对同一类风险给出两种强度的答案，判据是输入源的可信度和失败的
爆炸半径。** 这比统一用最严的那套更好——命令策略如果也只能写字面量，
管理员就表达不了他要表达的规则了。

---

## 四、把 CIDR 判定交给标准库

```ts
import { BlockList, isIP } from "node:net";
const PRIVATE_NETWORKS = new BlockList();
for (const [network, prefix] of [
  ["0.0.0.0", 8], ["10.0.0.0", 8], ["100.64.0.0", 10], ["127.0.0.0", 8],
  ["169.254.0.0", 16], ["172.16.0.0", 12], ["192.0.0.0", 24], ["192.0.2.0", 24],
  ["192.168.0.0", 16], ["198.18.0.0", 15], ["198.51.100.0", 24], ["203.0.113.0", 24],
  ["224.0.0.0", 4], ["240.0.0.0", 4],
] as const) PRIVATE_NETWORKS.addSubnet(network, prefix, "ipv4");
```

14 个 v4 段加 8 个 v6 段，覆盖到了 CGNAT（`100.64/10`）、基准测试网段
（`198.18/15`）、三个文档网段、NAT64 本地段（`64:ff9b:1::/48`）——比常见的
「私网三段加 localhost」完整得多。

真正的收益在这一行：

```ts
return PRIVATE_NETWORKS.check(value, isIP(value) === 4 ? "ipv4" : "ipv6");
```

用 `node:net` 的 `BlockList` 而不是手写位运算，**IPv4-mapped IPv6 地址被免费
处理掉了**。我实测确认：`::ffff:10.0.0.1` 以 `ipv6` 类型去 check，
会命中 `10.0.0.0/8` 这条 **v4** 规则并返回 `true`。手写 CIDR 匹配几乎必然漏掉
这一条——而 `http://[::ffff:169.254.169.254]/` 正是绕过 SSRF 检查的经典写法。

**用标准库做地址判定，不只是省代码，是省掉一整类你想不到的边界情况。**

`normalizedIp` 还做了两件小事：剥掉 v6 的方括号，和剥掉 zone id（`%eth0`）。
非 IP 输入返回 `false`——所以这个函数只判 IP，主机名必须由调用方先解析。
这个契约很重要：调用方拿到域名时**必须先解析再判**，而解析和连接之间的
TOCTOU 窗口是另一层要处理的问题。

这个函数的两个调用点是 `skills/pack-fetcher.ts` 和出网授权服务。

---

## 五、字符串的三种边界

### 5.1 代理对

```ts
export function headSlice(s: string, n: number): string {
  if (n <= 0) return "";
  if (s.length <= n) return s;
  const cut = s.slice(0, n);
  return /[\uD800-\uDBFF]$/.test(cut) ? cut.slice(0, -1) : cut;
}
export function tailSlice(s: string, n: number): string {
  ...
  return /^[\uDC00-\uDFFF]/.test(cut) ? cut.slice(1) : cut;
}
```

JS 的 `length` 和 `slice` 按 UTF-16 码元算，一个 emoji 占两个。在第 n 个码元
处硬切，有一半概率把一个代理对劈开，留下一个孤立代理——它不是合法的 Unicode
标量值，会在 JSON 序列化、数据库写入、以及送给模型时以不同方式炸掉。

`headSlice` 检查末尾是不是高位代理，是就再退一格；`tailSlice` 检查开头是不是
低位代理。两行代码，把「截断」这个到处都要做的操作变成安全的。

配套的 `hasLoneSurrogate` 用前后瞻检测已经存在的孤立代理——它是校验器，
上面两个是生成器。

### 5.2 NUL 与 jsonb

见 §2.2。写这篇文档的过程中我自己踩到了同一类问题的另一面：把
`/[\u0000-\u001f]/` 这个正则原样写进 markdown 时，转义序列被解释成了真实的
控制字节，导致文件里出现一个 NUL，`grep` 从此把它当二进制文件而静默失配。
**NUL 会把文本工具链的行为整个改掉，而且不报错。**

### 5.3 token 数是估算值

```ts
const CHUNK_CHARS = 4_000;
const SAMPLE_CAP_CHARS = 64_000;

export function countTokens(text: string): number {
  tokenizer ??= getTokenizer();
  const sample = text.length > SAMPLE_CAP_CHARS ? text.slice(0, SAMPLE_CAP_CHARS) : text;
  let n = 0;
  for (let i = 0; i < sample.length; i += CHUNK_CHARS) {
    n += tokenizer.encode(sample.slice(i, i + CHUNK_CHARS).normalize("NFKC"), "all").length;
  }
  return sample.length === text.length ? n : Math.ceil((n * text.length) / sample.length);
}
```

四个决定叠在一起：

1. **懒加载** tokenizer（`??=`）——它是个不小的 WASM/表，不用就不加载。
2. **只采样前 64KB**。
3. **4000 字符一块**——tokenizer 对超长字符串会慢得不成比例。
4. **线性外推**：`Math.ceil(n * text.length / sample.length)`。

最后一行是一个坦白：**超过 64KB 的文本，这个数字是估的**。它服务于
[[qm-harness-layer]] 的上下文压缩决策——那里需要的是「大概多少 token，
该不该压缩了」，不是精确账单。为一个阈值判断去精确 tokenize 一兆文本不划算。

`normalize("NFKC")` 在每块上做——如果不归一化，同一段视觉上相同的文本会因为
编码形式不同得出不同的 token 数。

---

## 六、把「吞掉异常」变成一个必须命名的动作

```ts
export function errMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}
export function swallow(context: string, e: unknown): void {
  console.warn(`[swallowed] ${context}: ${errMessage(e)}`);
}
export function swallowAs<T>(context: string, fallback: T): (e: unknown) => T {
  return (e) => {
    swallow(context, e);
    return fallback;
  };
}
```

14 行，88 个文件 import，其中 59 个用了 `swallow` / `swallowAs`，
合计 235 个调用点（其余只用 `errMessage`）。这是全仓最重要的一条约定。

`swallow` 的第一个参数是**必填的 context 字符串**。所以几乎不存在
「一个空的 `catch {}`」——全仓 `src/` 只数出 4 个，其余每一处被吞掉的异常都
带着一句人写的、说明这是哪里的话。前面十三篇里反复出现的
`swallow("leader-lease: unlock failed", e)`、
`swallow("aws-deploy: hydrate-fail terminate", e2)`、
`swallow("slack: surface-cache ingest", e)`，都是这个约定的实例。

`swallowAs(context, fallback)` 返回一个 `catch` 处理器，于是可以写成
`.catch(swallowAs("orchestrator: eager provision", undefined))`——**把「吞掉并
返回默认值」压缩成一个表达式**，比 `.catch(e => { log(e); return undefined })`
短，也比 `.catch(() => undefined)` 多留了痕迹。

前十三篇里我多次把 `.catch(() => undefined)` 当作问题指出
（[[qm-surface-mirror]] §6 的物化视图刷新、[[qm-publish-layer]] 里的若干处）。
现在可以把话说完整：**这个仓库有一个正确的吞异常工具，而那些出问题的地方
恰恰是没有用它的地方。** 约定存在但不强制，于是它的覆盖率就成了代码质量的
一个可测量指标。

**这个指标我在写 [[qm-synthesis]] 时补数了：** `src/` 里 235 处走约定，
另有 **111 处**裸写的 `.catch(() => x)` 绕过它，覆盖率约 68%。抽样 14 处，
全部落在 `swallowAs` 的适用范围内——也就是说这 111 处不是「另有用途」，
是纯粹的漏网。其中 `src/resolution/scope-membership.ts:61` 的
`.catch(() => false)` 值得单看：目录查询失败被静默地当成「不是成员」。
失败方向是安全的，但它塌掉了 [[qm-resolution-layer]] §4.1 那个三态判定——
`boolean | undefined` 存在的全部意义，就是让「答不上来」不等于「否」，
而一个 `.catch(() => false)` 把这两者又合并回去了。

---

## 七、代理头：静态表不够，还要读 `Connection:`

```ts
const HOP_BY_HOP = new Set([
  "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
  "proxy-connection", "te", "trailer", "trailers", "transfer-encoding", "upgrade",
]);

export function proxyHeaders<T extends string | string[]>(
  headers: Record<string, T | undefined>,
  extra: Iterable<string> = [],
): Record<string, T> {
  const dropped = new Set([...HOP_BY_HOP, ...[...extra].map((name) => name.toLowerCase())]);
  const connection = Object.entries(headers).find(([name]) => name.toLowerCase() === "connection")?.[1];
  let connectionList = "";
  if (typeof connection === "string") connectionList = connection;
  else if (Array.isArray(connection)) connectionList = connection.join(",");
  for (const name of connectionList.split(",")) {
    if (name.trim()) dropped.add(name.trim().toLowerCase());
  }
  ...
```

绝大多数反向代理实现只有那张静态表。但 RFC 7230 规定
**`Connection:` 头里列出的头名也全都是 hop-by-hop**——发送方可以声明
「这几个头只在这一跳有效」。不解析它，那些头就会被转发到下一跳。

`extra` 参数是给调用方追加的，[[qm-publish-layer]] §9.4 里
`GATEWAY_AUTH_HEADERS`（`x-signature`、`x-as-principal`、portal identity 令牌）
就是通过它被剥掉的，确保用户自己写的应用永远看不到调用方的身份断言。

**协议里有「可扩展的黑名单」这种机制时，静态表只是起点。**

---

## 八、`projects/`：一个伪装成 scope 的托管群组

`projects/project-store.ts` 236 行，回答的是：Web 端手工建的「项目」怎么接入
一个只认 scope 的权限系统。

答案是**前缀约定**：

```ts
const PROJECT_GROUP_PREFIX = "web-project-";
export function projectGroupRef(id: string): string { return `${PROJECT_GROUP_PREFIX}${id}`; }
export function projectScopeId(id: string): ScopeId { return scopeId("group", projectGroupRef(id)); }
```

一个 project 就是 `group:web-project-<uuid>` 这个 scope。于是它自动获得了
group scope 的全部待遇——记忆、文件、沙箱、cron、ACL，一样不缺
（[[qm-overview]] §2.1）。

接入点在 `resolution/scope-membership.ts`：`deps.managedGroups?.recognizes(ref)`
命中时**直接短路 directory 查询**。也就是说 project 是 scope 成员判定的
第一优先级来源——它的名单是自己说了算的，不问 Slack。

`projects/` 是 `managedGroups` 接口的唯一实现。

### 8.1 两处对照

**它对 `DurableMap.update` 的态度和 cron-store 相反。**

```ts
if (!backing.update) throw new Error("project store requires DurableMap.update");
```

[[qm-autonomy-layer]] §12 存疑 1 记过：`cron-store.ts` 的 `claimSlot` /
`unclaimSlot` / `recordFire` 都写成「有 `update` 走 CAS，没有就退回
`get` + `merge`」，而那个回退分支**没有原子性**。project-store 面对同一个
可选接口方法，选择了**直接抛**。

同一个仓库、同一个接口、两种相反的处理。project-store 的做法明显更对：
一个需要 CAS 才能保证正确性的操作，不应该在缺少 CAS 时静默降级成不正确的版本。
这也说明 cron-store 那三段回退不是深思熟虑的兼容设计，更像是没删干净。

**双层锁的写法和 deploy-service 一模一样：**

```ts
const queue = createKeyedQueue<string>();
const withLock = <T>(id: string, fn: () => Promise<T>): Promise<T> =>
  queue(id, () => advisoryLock.withLock(`project:${id}`, fn));
```

对照 [[qm-publish-layer]] §4：`deployQueue(id, () => advisoryLock.withLock(\`deploy:${id}\`, fn))`。
**两处独立写出了同一个模式**（进程内 keyed queue 包在分布式 advisory lock 外面），
而且都用了 `<域>:<id>` 的键前缀约定。没有被提取成公共函数，但形状一致——
这种「重复三次以上才抽象」的克制在这个仓库里是常态。

### 8.2 结果通道

`DurableMap.update` 的回调签名是 `(value: T) => T`——只能返回新值，
**没有地方返回错误码**。于是：

```ts
const outcome: { status: ProjectMutation["status"] } = { status: "not_found" };
let changed = false;
const updated = await backing.update(id, (project) => {
  const canChangeRoster = add
    ? project.memberIds.some((member) => samePerson(member, actorId))
    : samePerson(project.ownerId, actorId);
  if (!canChangeRoster || !isActiveMember(project.ownerId) || !isActiveMember(actorId)) {
    outcome.status = "forbidden";
    return project;              // 原样返回 = 不改
  }
  ...
  outcome.status = "ok";
  ...
  changed = true;
  return { ...project, memberIds, updatedAt: Math.max(now(), project.updatedAt + 1) };
});
```

闭包外的 `outcome` 对象承接状态，回调里「拒绝」表达为**原样返回**。
这是在一个只能表达「新值」的接口上表达「为什么没变」的标准手法。

`changed` 是第二个通道，区分「操作合法但结果没变」（重复加同一个人）和
「真的改了」——供 `effect` 回调决定要不要发通知。**「成功」和「有变化」是两件
不同的事**，很多 API 把它们混成一个布尔。

### 8.3 三个细节

**非对称权限。** 加人：任意成员都可以（`memberIds.some(samePerson)`）。
踢人和改名：只有 owner（`samePerson(project.ownerId, actorId)`）。
邀请是低风险的、可撤销的；移除不是。

**owner 离职则项目冻结。** `isActiveMember(project.ownerId) && isActiveMember(actorId)`
——两个都要在职。owner 走了之后**谁都改不动名单**，包括现有成员。
这和 [[qm-autonomy-layer]] §5.2 里 `scopeFloor` cron「owner 走了就换个人继续跑」
是相反的选择。差别在于 cron 是一个任务（可以换人执行），project 是一份**归属**
（换人就是改变归属，那必须是一个显式的管理动作）。

**`updatedAt` 兼任乐观锁版本号。**

```ts
updatedAt: Math.max(now(), project.updatedAt + 1)
```

`Math.max` 保证即使系统时钟回拨，版本号也严格递增。`version(groupRef)` 直接
返回 `String(updatedAt)`，供 API 层做 CAS。**一个字段同时是「最后修改时间」
和「版本号」**——省了一列，代价是这个时间戳不再是真实时间（时钟回拨时会
比真实时间大）。这个取舍在文档里没写。

同一个 `Math.max` 保护手法在 [[qm-credentials-layer]] §4.2 也出现过
（`Math.max(refreshMargin, skew)`），那里防的是配置错误，这里防的是时钟回拨——
**都是在「两个值的关系必须成立」时，与其校验不如直接钳制**。

---

## 九、`audit/`：接口在这里，实现在别处

`src/audit/audit-log.ts` 只有 44 行，定义接口加一个内存兜底：

```ts
export interface AuditLog {
  record(e: AuditEvent): void;
  recordOnce?(key: string, e: AuditEvent): Promise<void>;
  events(): Promise<readonly AuditEvent[]>;
  tail(opts: { limit: number; scopeLabel?: ScopeId; action?: string; since?: number }): Promise<readonly AuditEvent[]>;
}
```

生产实现在 `admin/postgres-audit-log.ts`，装配处二选一：

```ts
const auditLog = config.databaseUrl ? createPostgresAuditLog(config.databaseUrl) : createAuditLog();
```

### 9.1 `record()` 返回 `void`，不是 `Promise`

这是这个接口最重要的一个决定。返回 `void` 意味着**调用方在类型层面就无法
await 它**，于是审计永远不会阻塞被审计的操作，也永远不会因为审计失败而让
操作失败。

Postgres 实现里对应的是：

```ts
void q(insertSql, values).catch((err) => console.error(cfg.persistErrorMessage, err));
```

即发即忘。代价说清楚：**一次数据库抖动会静默丢掉若干条审计记录**，而且没有
任何补偿。对一个记录了 `deploy`、`keychain.materialize`、
`deployment_layer.updated` 的日志来说，这是一个真实的权衡——它选择了
「审计不能拖累业务」，代价是「审计不完整」。

`recordOnce` 是可选方法：内存版用一个**无界增长**的 `Set` 去重，
Postgres 版落在 `audit_log.idempotency_key` 的部分唯一索引上。
两种实现的语义强度不同——前者进程重启就忘了。

### 9.2 内存版是个环形缓冲

```ts
const MAX = 50000;
...
record(input) {
  events.push(opts.stamp(input));
  if (events.length > opts.max) events.splice(0, events.length - opts.max);
},
```

`admin/scoped-event-sink.ts` 提供的 `createScopedEventSink`。5 万条上限，
超出从头砍。`tail()` 的实现是「先拉满 5 万条再在 JS 里按 action/since 过滤，
最后 slice(limit)」——O(MAX) 而不是 O(limit)。无数据库形态下这不要紧，
但接口的形状允许调用方以为它是廉价的。

### 9.3 一个把审计日志当消息队列用的地方

`insights/reach-denied-notifier.ts` 按 `action: "deployment.reach_denied"`
加一个 `since` 游标轮询审计流，把它当事件源。

**这是一个值得警惕的用法。** 审计日志的写入是即发即忘的（§9.1），
所以这个消费者读到的事件流**本身就是有损的**。用一个明确不保证送达的存储
当队列，意味着「有人被拒绝访问但没收到通知」是一个正常会发生的情况。
如果这只是一个提醒类通知，可以接受；如果有人依赖它做安全响应，就不行了。

### 9.4 通用事件汇工厂

`admin/scoped-event-sink.ts`（179 行）里的 `createPostgresEventSink` 用一个
五元组列规格生成整套 CRUD：

```ts
export type EventColumn<F extends string = string> = readonly [string, F, string, ColumnKind, boolean?];
//                                                              db列   js字段  SQL类型  运行时类型 必填?
```

由它生成 `CREATE TABLE`、`INSERT`、`SELECT`、行到对象的映射器，以及两个标准
索引（`_by_ts`、`_by_scope_ts`）。一百来行的微型 ORM。

有意思的是**这个抽象存在，但 [[qm-surface-mirror]] §9.4 里那两个几乎一模一样
的账本 store 没有用它**——它们各自手写了全套 SQL。同一个仓库里，
「抽象出通用事件汇」和「两个近乎同构的 store 各写一遍」并存。
前者在 `admin/` 下，后者在 `surface-cache/` 下，跨目录的复用没有发生。

---

## 十、`onboarding/`：状态编码在一行 markdown 里

75 行，没有表、没有 store。新用户引导的状态**唯一的真相源是用户 memory 里的
一行 markdown**：

```
- Onboarding: completed v2 on 2026-08-15.
```

```ts
const ONBOARDING_VERSION = "v2";

function markerRe(state: "completed" | "dismissed" | "pending", version: string): RegExp {
  return new RegExp(
    `(?:^|\\n)\\s*[-*]?\\s*(?:\\(\\d{4}-\\d\\d-\\d\\d\\)\\s*)?Onboarding:\\s*${state}\\s+${escapeRegExp(version)}\\b`,
    "i",
  );
}
```

### 10.1 版本号是这个设计的全部收益

四种状态 `completed | dismissed | pending | not_started`，而 `not_started`
不是被存下来的，是**没匹配到任何标记**的结果。

标记里带版本号意味着：**把 `ONBOARDING_VERSION` 从 `v2` 改成 `v3`，所有老用户
的标记立刻失配，全体重新走一遍引导。** 不需要迁移脚本、不需要批量写库、
不需要一张 `onboarding_state` 表加一个 `version` 列。

代价是这个状态和用户的 memory 绑在一起——用户（或 agent）可以手动编辑掉它。
但这恰恰也是设计意图：`renderPendingOnboardingPrompt` 里明确写着
「Use the `memory` tool as the source of truth」。**引导状态被有意做成用户
可见、可改的数据，而不是系统的隐藏状态。**

### 10.2 一个幂等的 markdown 原地编辑器

```ts
const base = memory
  .replace(markerLineRe(version), "")     // 删掉同版本的旧标记行
  .replace(/[ \t]+$/gm, "")               // 清行尾空白
  .replace(/\n{3,}/g, "\n\n")             // 折叠三个以上连续换行
  .replace(/\s+$/, "");                   // 去尾部空白
if (status === "not_started") return base ? base + "\n" : "";
const line = status === "pending"
  ? `- Onboarding: pending ${version} since ${today}.`
  : `- Onboarding: ${status} ${version} on ${today}.`;
return (base ? `${base}\n${line}` : line) + "\n";
```

四步清洗再追加。删旧行会留下空行，所以要折叠；反复调用不会累积空白，
所以是幂等的。**在一份人也会编辑的自由文本里维护一行结构化状态，
必须连带做格式清理，否则几次读写之后文件就花了。**

### 10.3 开场白里明确禁止三件事

```
The user just opened the app for the first time and hasn't typed anything yet.
You already know who they are from their sign-in ... open the conversation
yourself: greet them by name as their AI teammate, briefly say what you can do,
and start onboarding by walking them through connecting their accounts.
Don't ask their name or role, and don't research them in this opening turn —
the hello is just a hello; you'll learn their role from connected tools and the
people directory later, once their accounts are connecting.
```

三条禁令：别问名字（已经知道了）、别问角色、别在开场白里做调研。

最后半句给出了替代方案——「以后会从已连接的工具和人员目录里知道」。
**禁止一个行为时同时说明正确的时机在哪，比单纯禁止有效得多**：模型不会
因为「不许调研」而认为永远不该了解用户。

`renderPendingOnboardingPrompt` 里还有一句针对具体失败模式的话：

```
Onboarding is a high-priority setup task; already knowing who they are is no
reason to skip it.
...do not confuse a greeting or existing profile data with completion.
```

「打过招呼」不等于「引导完成」——这显然是从实际行为里观察到的错误。
[[qm-autonomy-layer]] §7 里那些运行时说明书也是这个路子：**提示词里最有价值
的部分，往往是对一个已经观察到的具体错误的针对性纠正**，而不是对正确行为的
一般性描述。

---

## 十一、存疑

1. **`cron-store` 与 `project-store` 对 `DurableMap.update` 的处理相反**（§8.1）。
   后者 `throw`，前者静默退回无原子性的读-改-写。至少有一处是错的，
   而根据两者的用途（都需要 CAS），错的是 cron-store。
   根治办法是把 `update` 从可选改成必选。

2. **审计写入即发即忘，却被当作事件源消费**（§9.3）。
   `reach-denied-notifier` 轮询审计流做通知。写入失败只 `console.error`，
   于是「访问被拒但通知没发」是一个正常会发生的情况。没有任何地方承认这个
   取舍。

3. **`updatedAt` 兼任版本号使它不再是真实时间**（§8.3）。
   `Math.max(now(), updatedAt + 1)` 在时钟回拨时会产生一个未来的时间戳。
   任何按 `updatedAt` 做时间范围查询或展示「最后修改于」的地方都会看到它。
   没有注释说明这个字段有双重身份。

4. **`scopeStorageKey` 的碰撞面没有被论证。**

   ```ts
   export function scopeStorageKey(scopeId: string): string {
     const legacy = scopeId.replace(/[^a-zA-Z0-9_.-]/g, "__");
     const ref = scopeId.slice(scopeId.indexOf(":") + 1);
     return /^[a-zA-Z0-9_.-]+$/.test(ref) ? legacy : `${legacy}--${hashId([scopeId], 12)}`;
   }
   ```

   ref 是安全字符时返回 `legacy`（可读、向后兼容），否则追加 12 位哈希。
   问题在于两类结果共存于同一个命名空间：一个 ref 恰好长成
   `something--0123456789ab` 形式的安全 scope，会和某个不安全 scope 的
   哈希形式撞上。概率极低，但这是一个**可构造**的碰撞而不是随机碰撞——
   ref 有一部分是用户可控的（比如频道名）。

5. **`countTokens` 的线性外推在结构不均匀的长文本上会偏。**
   前 64KB 如果是散文而后面是 base64 或代码，token 密度差别很大。
   它服务于压缩阈值判断，偏一点不致命，但没有任何地方标注这个数字是估计值——
   接口返回一个 `number`，看起来和精确计数没有区别。

---

## 十二、可迁移做法

**关于小到不该被绕过的安全原语**

1. shell 转义做成一个导出的单行函数，不要做成「shell 工具类」。
   **一个安全原语如果足够小，就没有人想绕过它。**
2. 拼接后哈希时用 `\0` 当分隔符——任何可能出现在内容里的分隔符都会造成
   拼接歧义，让两个不同的输入哈希成同一个值。
3. `timingSafeEqual` 之前必须先比长度（它在长度不等时抛）。用 `&&` 短路
   保证顺序。
4. 地址/CIDR 判定交给标准库（`node:net` 的 `BlockList`），不要手写位运算——
   IPv4-mapped IPv6 这类边界情况会被免费处理掉。
5. 判 IP 的函数就只判 IP，主机名必须由调用方先解析。把「解析」和「判定」
   分开，TOCTOU 才有地方处理。

**关于同一个威胁的不同强度**

6. 同一类风险（ReDoS）可以在同一个系统里有两种强度的答案，判据是
   **谁写这个输入、它对着什么跑、写错的爆炸半径多大**。
   管理员写的命令规则可以保留正则减去危险形状；模型写的、对着无界日志流
   每 10 秒跑一遍的模式，就该禁掉整个正则。
7. ReDoS 防护不必度量复杂度，拒绝两三种已知会爆炸的语法形状就够——
   相邻量词、量词套量词、量词套交替。保守、便宜、不需要回溯分析。

**关于字符串边界**

8. 按码元截断字符串时要检查断口上的代理对，否则会产生孤立代理，
   在 JSON、数据库、模型输入三处以不同方式炸掉。
9. 写进 Postgres `jsonb` 之前剥掉 `\u0000`。
10. token 计数是估算就要在实现里承认（采样 + 外推），并且在归一化之后计数。
    但接口最好能让调用方知道它是估算。

**关于错误处理约定**

11. 把「吞掉异常」做成一个**必须传 context 的函数**，这样不存在空的
    `catch {}`，每一处被吞的异常都带着一句人写的说明。
12. 再提供一个 `swallowAs(context, fallback)` 返回 catch 处理器的变体，
    让「吞掉并返回默认值」能压缩成一个表达式——降低使用成本，覆盖率才上得去。
13. 约定存在但不强制时，它的覆盖率就是一个可测量的代码质量指标：
    `.catch(() => undefined)` 出现在哪里，问题通常就在哪里。
    这个仓库的实测值是 235 处走约定 / 111 处绕过，约 68%——
    **这个数字本身应该进 CI，而不是等人来数。**

**关于反向代理**

14. hop-by-hop 头的静态表只是起点，还要解析 `Connection:` 头里列出的头名——
    协议允许发送方动态扩展这张表。
15. 给调用方一个 `extra` 参数追加要剥掉的头，网关自己的鉴权头通过它移除。

**关于把新概念接进已有的模型**

16. 一个新实体如果能用「已有类型 + 前缀约定」表达，就不要新增一种类型——
    `project` 只是 `group:web-project-<uuid>`，于是自动获得 group scope 的
    全部待遇。
17. 在一个只能返回新值的更新接口上表达「为什么没改」：用闭包外的结果通道
    对象，回调里「拒绝」表达为原样返回。
18. 「成功」和「有变化」是两件不同的事，用两个通道分别表达，
    调用方才能决定要不要发通知。
19. 「两个值的关系必须成立」时，与其校验不如直接钳制（`Math.max`）。
    但要意识到被钳制的字段从此不再是它字面上的含义。
20. 非对称权限：邀请是低风险可撤销的，移除不是——加人放宽，踢人收紧。
21. 「归属」和「任务」在所有者离职时应有相反的处理：任务换个人继续跑，
    归属冻结等待显式的管理动作。

**关于版本化的用户状态**

22. 把「这个用户完成过引导吗」编码成一行带版本号的文本，改版本号就等于
    让所有人重来——不需要迁移脚本，不需要额外的表。
23. 在一份人也会编辑的自由文本里维护结构化状态，写回时必须连带做格式清理
    （删旧行、折叠空行、去尾部空白），否则几次读写之后文件就花了。
24. 引导状态放在用户可见可改的地方，而不是系统的隐藏状态。

**关于给模型的禁令**

25. 禁止一个行为时同时说明**正确的时机在哪**（「以后会从已连接的工具里
    知道」），否则模型会把「现在别做」理解成「永远别做」。
26. 提示词里最有价值的部分往往是对一个**已观察到的具体错误**的针对性纠正
    （「打过招呼不等于引导完成」），而不是对正确行为的一般性描述。

**关于审计**

27. `record()` 返回 `void` 而不是 `Promise`，从类型上保证审计不阻塞业务。
    但要明说代价：审计会丢，而且没有补偿。
28. **不要把一个即发即忘的审计日志当事件源消费。** 如果要拿它当队列，
    先给它一条可靠的写入路径。

---

## 十三、与其他篇的连接

**与 [[qm-autonomy-layer]]**：`createKeyedQueue`、`sweeper`、`hashId` 三个
零件都在那篇里被大量使用，本篇是它们的实现。§8.1 那条对照
（`cron-store` 静默降级 vs `project-store` 直接抛）是对那篇 §12 存疑 1 的
补完——现在可以确定哪一种是对的。

**与 [[qm-publish-layer]]**：`shq`、`proxyHeaders`、双层锁模式三处都在那篇里
出现。`proxyHeaders` 的 `extra` 参数正是那篇 §9.4 里剥掉网关鉴权头的机制。

**与 [[qm-authz-layer]]**：`compileSafeRegex` 服务的唯一调用点是那篇 §6 的
命令策略；`constantTimeEqual` 和 `hashId` 是那篇令牌校验的底层件。

**与 [[qm-surface-mirror]]**：§9.4 指出 `admin/scoped-event-sink.ts` 已经有一个
通用事件汇工厂，而那篇 §9.4 里两个近乎同构的账本 store 没有用它——
跨目录的复用没有发生。

**与 [[qm-harness-layer]]**：`countTokens` 服务于那篇的上下文压缩阈值判断；
`message-tag.ts` 的 `<message from="human|agent" overheard trigger>` 是那篇
tape 里消息渲染的格式，也是「标注出身」这条方法论在最底层的一次落点。

**与 [[qm-resolution-layer]]**：`projects/` 是 `managedGroups` 接口的唯一实现，
在那篇的 scope 成员判定里享有第一优先级——命中即短路 directory 查询。

**与 [[qm-credentials-layer]]**：`Math.max` 钳制手法在两处出现，
那里防配置错误，这里防时钟回拨。

**与 [[qm-overview]]**：本篇覆盖 `util/`、`projects/`、`audit/`、`onboarding/`
四个从未进入 A–J 分组的目录。全仓只剩五个顶层文件（`wiring.ts`、`config.ts`、
`types.ts`、`egress-authz-main.ts`、`index.ts`）和 `deployment/` 一个目录。

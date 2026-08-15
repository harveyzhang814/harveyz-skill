# QM 是怎么被立起来的：装配、配置、装机层，和第二个进程

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
> - [[qm-crosscutting]]（横切件——`util/`、`projects/`、`audit/`、`onboarding/`）
> - [[qm-synthesis]]（综述——本篇的缺失三分类构成「这个能力可能不在」的下半）
> - [[qm-surface-layer]]（表面层——启动期校验在插件侧的同构：攒齐全部问题再一次性报）
>
> 调研对象：`yc-software/qm`（YC 出品的开源多人 agent harness）
> 本地路径：`~/Repositories/qm`
> 调研时间：2026-08-15
> 仓库版本：`main` @ `0f0e0ad`
>
> 阅读范围：五个顶层文件——`src/wiring.ts`（1490）、`src/config.ts`（859）、
> `src/types.ts`（488）、`src/egress-authz-main.ts`（251）、`src/index.ts`（147）——
> 加上 `src/deployment/`（5 文件 1647 行），共 10 个文件约 4882 行；
> 另核对 `deploy/egress-proxy/` 的 Envoy 配置与启动脚本、
> `src/api/deps.ts` 的 `ServerDeps`、`src/runs/drain.ts`
>
> **这批文件从未出现在 [[qm-overview]] 的 A–J 分组里**，是本次调研最大的一处
> 遗漏。它们回答的是一个前十四篇都没问过的问题：**这套东西是怎么被立起来的。**

---

## 一、这一篇在讲什么

前面十四篇讲的都是「某个子系统怎么工作」。这一篇讲四件别的事：

| | 文件 | 问题 |
| --- | --- | --- |
| **词汇** | `types.ts` | 这个系统用哪些名词思考 |
| **旋钮** | `config.ts` | 一个装机可以调什么，调错了会怎样 |
| **接线** | `wiring.ts` + `index.ts` | 哪些部件、怎么选、按什么顺序装上、怎么拆 |
| **交付** | `deployment/` | 一家公司拿到这套代码之后往上加什么 |
| **执法** | `egress-authz-main.ts` | 沙箱能访问哪些外网——由**第二个进程**说了算 |

最后一个是真正的盲区：`egress-authz-main.ts` 不在 `package.json` 的任何脚本里，
它由 `deploy/egress-proxy/start.sh` 用 `node ... &` 拉起，和一个 Envoy 进程
组成一个独立的容器。[[qm-authz-layer]] 讲了出网策略是**怎么算出来的**，
这一篇讲它**在哪里被执行**。

---

## 二、`types.ts`：42% 的导入是同一个概念

488 行，约 50 个导出。按主题分：

| 主题 | 主要类型 |
| --- | --- |
| scope 与主体 | `PrincipalType`、`Principal`、`ScopeKind`、`ScopeId`、`scopeId()`、`personalScope()`、`parseScopeId()`、`isManageableCreationScope()`、`isSharedScope()` |
| 会话 | `ConversationKind`、`Conversation`、`SessionType`、`Session`、`EntryType`（11 种）、`SessionEntry` |
| 工作区与解析 | `WorkspaceLayer`、`Resolution`、`Permission`、`Grant`、`GrantedHandle` |
| 触发器 | `TriggerBase`、`CronSchedule`、`Cron`、`Monitor`、`RecipientConsent` |
| 投递 | `Destination`、`DeliveryProvenance`、`Delivery` |
| 策略 | `EgressPolicy`、`CommandDecision`、`CommandRule`、`CommandPolicy` |
| 回合 | `TurnOrigin`（四态联合）、`TurnRequest`（**53 个字段**）、`TurnResult` |
| 审批 | `PendingApproval`、`PendingApprovalRecord`、`ApprovalGrantModes` |

全仓从 `types.ts` 一共 733 次具名导入，前几名：

| 名字 | 次数 |
| --- | --- |
| `scopeId()` | 170 |
| `ScopeId` | 101 |
| `TurnRequest` | 57 |
| `Principal` | 50 |
| `parseScopeId()` | 36 |

**`scopeId` + `ScopeId` + `parseScopeId` 合计 307 次，占全部导入的 42%。**
比「回合」本身还高。[[qm-overview]] §2.1 说「scope 是第一性的」，这个数字是
它最直接的证据——不是设计文档里的宣称，是导入统计。

### 2.1 `ScopeId` 只是 `string`

```ts
const SCOPE_KINDS = ["personal", "channel", "team", "org", "group"] as const;
export type ScopeKind = (typeof SCOPE_KINDS)[number];
export type ScopeId = string;

export function scopeId(kind: ScopeKind, ref: string): ScopeId { return `${kind}:${ref}`; }
export function parseScopeId(id: ScopeId): { kind: ScopeKind | null; ref: string } {
  const sep = id.indexOf(":");
  if (sep < 0) return { kind: null, ref: "" };
  const raw = id.slice(0, sep);
  return { kind: isScopeKind(raw) ? raw : null, ref: id.slice(sep + 1) };
}
```

**不是模板字面量类型，不是品牌类型，就是 `string`。** 所以任何字符串都能传到
要 `ScopeId` 的地方，编译器不管。代价在 `wiring.ts` 里看得见——
`(e.scopeLabel ?? "unknown") as ScopeId`、`scopeId as ScopeId` 这类断言。

对一个 42% 导入率的核心概念，这是个可以质疑的选择。TypeScript 里
`type ScopeId = \`${ScopeKind}:${string}\`` 是可行的，代价是每个从数据库读出的
字符串都要过一次断言或校验。这里选了完全不设防，靠 `scopeId()` / `parseScopeId()`
这一对函数当纪律。（见 §10 存疑 1。）

`parseScopeId` 用 `indexOf(":")` 取**第一个**冒号，所以 ref 自己可以带冒号——
Slack 的某些 ref 需要这个。解析永不抛错：前缀不认识就 `kind: null` 但 ref 照给，
完全没有分隔符则 `{kind: null, ref: ""}`。

### 2.2 五种 scope，三种切分

```ts
export function isManageableCreationScope(id) { const {kind} = parseScopeId(id); return kind === "channel" || kind === "team"; }
export function isSharedScope(id)            { const {kind} = parseScopeId(id); return kind === "channel" || kind === "group"; }
```

| | personal | channel | team | org | group |
| --- | --- | --- | --- | --- | --- |
| 单一所有者 | ✓ | | | | |
| 可管理的创建域 | | ✓ | ✓ | | |
| 共享受众 | | ✓ | | | ✓ |

三条切分线互不重合，而且 **`org` 一条都不在**——它是那个永远以只读方式挂在
`global/` 的根（[[qm-resolution-layer]] §1）。

不对称之处值得记：**`team` 可管理但不共享，`group` 共享但不可管理。**
前者是因为 team 有一份行政意义上的名单（可以在它下面建 artifact 并说清归谁），
后者是因为群聊是临时凑起来的（有受众，但没有归属）。
[[qm-publish-layer]] §6 里 `createdInScope` 只认 `isManageableCreationScope`，
[[qm-resolution-layer]] §3 的 audience floor 只对 `isSharedScope` 生效——
两个谓词各自服务一处，没有被混用。

---

## 三、`config.ts`：165 个旋钮，和「什么该崩」

`Config` 有 **116 个顶层字段**，加上四个嵌套的环境块
（`AwsSandboxEnv` 19、`AwsDeployEnv` 20、`LocalSandboxEnv` 5、`SpritesSandboxEnv` 5）
共 **165 个旋钮**。

`loadConfig()` 305 行分成两半：前 130 行是校验与派生，后 172 行是一个巨大的
对象字面量——**没有中间变量的反复赋值**，构造完就是最终形态。

### 3.1 打错的环境变量是启动崩溃

文件里有两组解析辅助：

```ts
export function boolEnv(name, value) { ... }   // 宽松，解析不了返回 undefined
export function numEnv(name, value)  { ... }

function boolEnvStrict(name: string, value: string | undefined) { ... throw ... }
function numEnvStrict(name: string, value: string | undefined)  { ... throw ... }
```

**实际到处用的是 `Strict` 那一对**，它们在输入是垃圾时抛错，错误消息带上
环境变量名和修复提示。同样的模式还有六个按枚举定制的版本
（`harnessEnvStrict`、`sandboxBackendEnvStrict`、`securityPostureEnvStrict`……），
每个都在报错里列出合法取值。

这是个值得抄的决定：**`WORKERS=sixteen` 应该让进程起不来，而不是静默变成默认的
16。** 一个被静默忽略的配置项，会让运维在几周后对着一个「明明配了却没生效」的
系统排查。

默认值集中在一张冻结的表里：

```ts
const CONFIG_DEFAULTS = { execTimeoutDefaultSec: ..., ... } as const;
```

命名上有个细节：以秒为单位的默认值保留 `Sec` 后缀，在使用处乘 1000。
**环境变量的界面是秒，`Config` 的界面是毫秒**，两套单位由后缀区分，不混。

### 3.2 什么该崩、什么该警告

这是本节的重点。硬失败（throw）大约二十处，软降级（warn）**只有三处**。

**警告的全部三条：**

1. `NODE_ENV=production` 但 `HARNESS` 是 mock 或没设 ——
   「this deployment answers every message with canned text and calls no model provider」
2. `SANDBOX_BACKEND=sprites` 但没配 `SPRITES_EGRESS_PROXY_URL` ——
   「sandboxes run with **NO egress enforcement** (fail-open)」
3. `DEPLOY_PROVIDER=aws` 但解析不到数据桶 ——
   「deployed apps have **NO durable /data**」

三条的共同形状：**输入是可解释的、自洽的，产生一个能跑但功能残缺的系统**，
而且三种残缺都是开发环境里可能真的想要的。三条警告都明说了「哪个能力会
悄悄不存在」。

**崩溃的判据是：输入不可解释，或者自相矛盾。** 包括拼错的枚举值、
非数字的数字、已被移除的选项（`SESSION_STORE=sqlite`）、
必须成对出现却只给了一个（`DEPLOY_APPS_SESSION_SECRET` 与
`DEPLOY_APPS_LOGIN_URL`）、以及缺失或过弱的密钥。

最能说明这条线的是一组对照：

> **`SECURITY_SCREEN_BACKEND=proxy` 但没给全四个 `SECURITY_SCREEN_PROXY_*` → 崩。**
> **`SECURITY_SCREEN_PROXY_*` 配了但 backend 是 `model` → 也崩。**
> 而**根本没配出网代理 → 只是警告。**

**一个装了一半的安全控制是致命的，一个没装的可选安全控制不是。** 前者会让人
以为防线在，后者至少诚实。第二条（反方向的配置也崩）尤其对：配了代理参数却
没启用代理，说明操作者以为它生效了——这种「以为生效」正是最危险的状态。

同一条线在 §9 还会出现一次：出网授权服务里缺 `CAPABILITY_SECRET` **只警告**，
因为那个服务降级成全部拒绝而不是全部放行——**降级方向是安全的，所以可以不崩。**

### 3.3 密钥闸门是一张谓词表

密钥校验不在 `config.ts` 里，而在 `deployment/secret-schema.ts`：

```ts
type SecretGate = "production" | "codex" | "postgres" | "sprites" | "fly-sandbox"
  | "fly-deploy" | "aws-deploy-gate" | "google-oauth" | "dropbox-oauth" | "linear-oauth"
  | "model-anthropic" | "model-openai" | "model-openrouter";

export interface RuntimeSecretSpec {
  name: string;
  requiredWhen: SecretGate | readonly SecretGate[];
}
```

13 个 gate 不是分类也不是级别，是 **13 个谓词的名字**，每个对应一个
`(env) => boolean`。`requiredWhen` 是数组时取**或**——例如 `OPENAI_API_KEY`
在 `["codex", "model-openai"]` 下必需。

「缺失」的定义包括「是垃圾」：

```ts
// 空白、以及字面量 replace-me | placeholder | changeme | todo 一律算缺
// 三个签名密钥还要额外过 isStrongSigningSecret
```

**把「需要哪个密钥」从代码里的散落 `if` 提炼成一张
`(密钥, 条件谓词)` 的表**，好处是这张表可以被文档漂移测试盯住——
仓库里确实有一个 `secret-schema-drift.test.ts`。

有意思的是这张表里有两个**永远不会触发**的 gate：`fly-sandbox` 和 `fly-deploy`
判的是 `SANDBOX_BACKEND === "fly"` / `DEPLOY_PROVIDER === "fly"`，
而 `sandboxBackendEnvStrict` 只接受 `aws | local | sprites`——`fly` 会先在
枚举校验那里崩掉。声明式表格的典型代价：**表项不会因为对应的代码路径消失而
自动失效。**（见 §10 存疑 2。）

### 3.4 全局 `orgId()`，和一个预留的多租户缝

```ts
const DEFAULT_ORG_ID = "default-org";
export function orgId(): string { return process.env.ORG_ID ?? DEFAULT_ORG_ID; }
export function orgScope(): string { return `org:${orgId()}`; }
```

直接读 `process.env`，绕开 `Config`——尽管 `Config.orgId` 存在且取值完全一样。
**32 个文件 import 它**，全是叶子模块：各种 store、sandbox 实现、
capability token、以及大半个 API 层。把 `orgId` 一路穿参下去意味着给几百个
函数签名加参数，所以它被做成了环境变量。

最有意思的是 `api/routes/shared.ts`：

```ts
export const orgScope = (_deps?: unknown): string => configOrgScope();
```

**它接受一个 deps 参数然后忽略它。** 调用处写的是 `orgScope(ctx.deps)`——
一个长得像「按请求取组织」的 API，底下是个进程全局。这是多租户的**预留缝**：
形状已经摆好，线还没接。

`wiring.ts` 自己从不调这两个全局，一律用 `scopeId("org", config.orgId)`。
**所以 `buildApp` 在技术上是多组织可行的，叶子不是。**

---

## 四、`wiring.ts`：三条切换轴，不是一条

[[qm-overview]] §2.5 说「每个 store 都成对存在，生产实现通过一个
`wiring.ts` 换进来」。读完发现这个描述漏了一层——切换有**三条轴**，
而其中一条才是让这个文件不至于失控的关键。

### 4.1 第一条：显式三元，20 处

```ts
const auditLog = config.databaseUrl ? createPostgresAuditLog(config.databaseUrl) : createAuditLog();
```

`acl`、`auditLog`、`rateLimiter`、`files`、`memory`、`errors`、`tasks`、
`processes`、`replayDedupe`、`metrics`、`credentialUsage`、`egressAudit`、
`sessionStateBus`、`directory`、`environments`、`deliveries`、
以及 surface-cache 那四个（[[qm-surface-mirror]]）——各写一行。

### 4.2 第二条：`artifactMap` 间接层，一行覆盖三十个 store

```ts
const pgArtifactMap = config.databaseUrl ? createPostgresMapFactory(config.databaseUrl) : null;
const artifactMap = <T>(table: string): DurableMap<T> =>
  pgArtifactMap ? pgArtifactMap.map<T>(table) : createMemoryMap<T>();
```

`artifactMap("...")` 被调用约 30 次。连接器客户端、souls、命令策略、安全姿态、
egress 策略、特性开关、模型清单、品牌配置、skills、skill packs、
凭证/授权/请求、consent links、secret drops、sandbox bodies、deployments、
approvals、projects、monitors、crons、idempotency、ambient cursors、
browser sessions……全部通过这**两行**拿到各自的持久/内存实现。

这才是这个文件能容纳 60 多个组件的原因：**加一个持久化 store 的成本是一行
`artifactMap("table_name")`，不是一个新的三元表达式。** 把「二选一」从每个
调用点提炼成一个工厂函数，边际成本就从 O(1) 降到接近 0。

### 4.3 第三条：显式声明 `*_STORE=postgres`，4 处

```ts
const requireDbUrl = (kind: string): string => {
  if (!config.databaseUrl) throw new Error(`${kind}=postgres requires DATABASE_URL`);
  return config.databaseUrl;
};
```

`sessions`、`runSignals`、`runStore`、`runActivity` 这四个**不从
`DATABASE_URL` 的存在推断**，必须显式说 `SESSION_STORE=postgres`，
说了却没给 URL 就崩。

为什么单独这四个？它们是执行内核的状态（[[qm-run-lifecycle]]）——
「会话历史存哪里」是一个部署者必须**有意识**做出的决定，不该因为顺手配了个
`DATABASE_URL` 就悄悄改变。**推断出来的默认适合无关紧要的东西，
要紧的东西应该逼人明说。**

---

## 五、状态有孪生，能力不作假

不是所有组件都有内存兜底。缺东西的时候，代码分两种反应：

**状态**（数据存哪儿）→ 给一个内存孪生，功能照常。

**能力**（能不能做某件事）→ **整个组件不存在**，类型上是 `undefined`。

| 组件 | 缺什么就没有 |
| --- | --- |
| `keychain?: Keychain` | 没有 `CONNECTOR_SECRET_KEY`（加密密钥） |
| `browserSessionStore?` | 同上 |
| `processes?: ProcessRegistry` | sandbox 后端不支持进程会话 |
| `monitorPoller` | 没有 `processes` |
| `taskProtection` | 没有 ECS 环境 |
| `securityScreener` | 没配代理后端 |
| `reachDeniedNotifier` | 没配通知频道 |
| scheduler 的 `jobQueue` | 没有 `DATABASE_URL` |

最能说明问题的是第一条：**没有加密密钥时，整个凭证子系统从 `BuiltApp` 里消失**，
而不是退化成「明文存在内存里」。所有下游消费者都被写成能处理
`keychain === undefined`。

**一个假的加密比没有加密更危险**，因为前者会让人以为凭证是被保护的。
同样，一个假的进程注册表会让 monitor 报告一堆不存在的作业。
「能力」这一类东西没有可信的降级形态，所以只能缺席。

`leaderLease` 和 `instanceRegistry` 是第三种：缺 DB 时是 **noop 实现**
而不是内存实现——因为「单进程里的领导者选举」这个概念本身没意义，
noop（永远拿到锁）恰好就是单进程下的正确语义。

三种反应对应三种性质：

| 性质 | 缺失时 | 例子 |
| --- | --- | --- |
| 状态 | 内存孪生 | 所有 store |
| 能力 | 不存在（`undefined`） | keychain、processes |
| 协调 | noop（单实例下的正确语义） | leaderLease、instanceRegistry |

---

## 六、九处延迟绑定：装配文件真正的职责

`buildApp()` 大致十一个阶段，严格按依赖顺序。但有九处地方是**先建空壳、
后填字段**——它们标出了这个系统里所有的循环依赖。

最干净的一处：

```ts
const membership: { canReadScope?; canManageScope?; managesArtifactHome? } = {};
const acl = createAclStore(..., {
  manages: (p, s, a) => membership.managesArtifactHome!(s, a ?? "", p),
});
// ... 480 行之后 ...
membership.managesArtifactHome = ...;
```

ACL 需要「这个人管不管得了这个 scope」，而这个判断需要 directory 和 projects，
而 projects 需要 ACL。用一个空对象加上闭包里的 `!` 断言把环打开。

其余八处：

| 延迟绑定 | 环 |
| --- | --- |
| `cronChanged.notify = (id) => scheduler.notifyChanged(id)` | scheduler 要 crons，crons 要通知 scheduler |
| `orchestratorDeps.surfaceContext = createSurfaceContextPuller(app, ...)` | orchestrator → 拉取器 → app → orchestrator |
| `orchestratorDeps.channelPolicy` | 同上 |
| `orchestratorDeps.surfaceCache` | 同上 |
| `orchestratorDeps.control = createControlService(app, scheduler)` | 同上 |
| `hasLiveWork` 闭包引用 160 行之后才声明的 `processes` | 词法上的前向引用 |
| `busy: () => workers.some(w => w.busy())` | 同上，两行 |
| `liveFallback` 通过可变的 deps 对象读 `surfaceContext` | 调用时解析而非捕获时解析 |

九处全部靠「箭头函数在构造期不被调用」这一点成立。这是有效的，
但它也是这个文件最脆的部分——把任何一个改成立即求值都会炸。

### 6.1 装配文件里为什么有业务逻辑

`wiring.ts` 里还有一批明显不是「构造对象」的代码：

- `stopWithBackstop`（§7.2）——整个关停算法
- `liveFallback`——Slack 消息形状到镜像行的翻译（[[qm-surface-mirror]] §5）
- `crons` 装饰器——手写代理，在三个方法后触发变更通知
- `pokeReaper`——带 1 秒冷却的去抖
- 三个 `runs.onTerminal` 处理器，第三个会去扫 approvals、查参与者、
  重新确认有没有活跃 run，再往状态总线发 `awaiting_approval` 或 `idle`
- `orphanedSignalSweeper`——重放孤儿信号，并且每小时最多剪枝一次 7 天前的信号
- `reachDeniedNotifier.notify`——拼 Slack 消息文本，含按小时分桶的幂等键
- `resolveModelProviderKeys` / `resolveCustomProviders`——两处都写着同一条降级
  策略：**一个损坏的自定义密钥不能毒化整个回合 / 不能阻止服务启动**

为什么在这里？因为**每一条都需要两三个只在这一层才共存的组件**：
拉取器 + 镜像、crons + scheduler、runs + sessions + approvals + 状态总线、
keychain + pack fetcher。把它们推下去就会造出 §6 那些延迟绑定要解决的循环。

所以这个文件的真实职责不是「构造对象」，是**拥有对象之间的边**。
1490 行里大概三分之一是边上的逻辑。这是一个可以争论的架构选择——
好处是循环依赖被集中在一个文件里而不是散落各处，坏处是这个文件谁也不敢动。

---

## 七、`index.ts`：启动顺序与优雅关停

### 7.1 十一步

```
loadConfig()                    // 顶层，无 try/catch——校验失败就是启动崩溃
buildApp(config)                // 同步；hydration 是内部的浮动 promise
Slack 环境三态判定               // absent / configured / partial
createServer(app, { ...66 个键 })
await config.hydrate()
await identity.hydrate()
await deploymentLayerReady
deploymentLayerRefresh.start()  // 30s
runtime.start()                 // 全部后台循环
server.listen(port)
scheduler.start(1000)           // 仅当 backgroundWorkEnabled
createSlackRuntimeReconciler()  // 5s 轮询
```

**`runtime.start()` 在 `listen()` 之前。** 后台 worker 可能在 HTTP 端口打开
之前就开始领 run 了。对一个多实例部署这是对的——新实例应该先开始干活，
再开始接流量；反过来会有一个「能接请求但还没准备好」的窗口。

`hydrate` 那三步是 `await` 的：配置、身份、装机层必须就绪才服务。
而 `buildApp` 内部的其它 hydration 是浮动 promise——**只有会影响正确性的
预热才阻塞启动。**

### 7.2 关停：三层背压

```ts
function shutdown(signal: string): void {
  if (shuttingDown) return;                 // 重复信号幂等
  shuttingDown = true;
  void slackRuntime.stop().catch(...);      // 不 await
  built.scheduler.stop();
  built.deploymentLayerRefresh.stop();
  server.close();                           // 不再接新连接
  server.closeIdleConnections();            // 立刻断掉 keep-alive
  stopWithBackstop(built.runtime, config.shutdownDrainMs, "qm",
                   () => server.closeAllConnections());
}
```

`runtime.stop()` 内部是分级的：

1. **先停所有定时器**（同步，十个 sweeper）——不再产生新工作。
2. `await` 所有 worker 的 `stop(shutdownDrainMs)` 排空，
   外面包一层 `swallowAs`，**排空失败不能跳过第 3 步**。
3. `await` 所有 worker 的 `releaseInFlight()`——**无条件释放租约**，
   哪怕第 2 步成功了也要做。
4. `drain.stop()`——清掉 ECS 任务保护。
5. 关连接。

而 `stopWithBackstop` 是这一切之上的兜底：

```ts
const hardExit = setTimeout(() => {
  console.error(`[${label}] drain overran; releasing in-flight leases before forced exit`);
  void Promise.race([runtime.releaseInFlightRuns(), sleep(3_000, { unref: true })])
    .finally(() => process.exit(0));
}, shutdownDrainMs + 5_000);
hardExit.unref();
```

三层：

- **排空预算 + 5 秒**的硬退出定时器（默认合计 15 秒）。
- 硬退出触发时**不直接 exit，先花最多 3 秒释放租约**再走。
- `hardExit.unref()`——一切提前结束时这个定时器不会拖住事件循环。

关键在第二层。**租约比干净退出更要紧**：一个没释放的 run 租约意味着那次对话
要等到 reaper 超时回收（[[qm-run-lifecycle]] §3）才能继续。所以即使在
「已经超时、准备强杀」的路径上，也要再挤出 3 秒去释放。而 3 秒也是有上限的——
一个卡住的数据库不能把进程扣住。

`Runtime` 接口上专门有一个 `releaseInFlightRuns()`，就是为了让这个兜底能
独立于 `stop()` 调用它。**兜底路径需要的能力要显式暴露在接口上**，
而不是指望能复用正常路径的某个内部步骤。

### 7.3 66 个扁平参数

```ts
export function createServer(app: App, deps: ServerOptions = {}): Server
// type ServerOptions = Omit<ServerDeps, "control">
```

`ServerDeps` 有 **76 个字段，其中唯一必填的 `control` 被 `Omit` 掉了**——
于是 `createServer` 的每一个参数都是可选的。`index.ts` 传 66 个键，
其中 24 个包在 `...(x ? { k: x } : {})` 里。

后果说清楚：**漏传一个依赖不是类型错误，只是某一族路由在运行时静默失效。**
好处是测试可以用零依赖构造一个 server。

而且这个扁平化做了两次：`buildApp` 返回 65 个字段的 `BuiltApp`，
`index.ts` 手工把它重新投影成 66 个键的 `ServerDeps`，中间还掺进二十来个
`config.*` 和三个计算值。**两个接口靠人力保持同步**，没有自动透传。

### 7.4 Slack 令牌可以热轮换

`createSlackRuntimeReconciler` 每 5 秒跑一次，优先级是
**存储里的安装记录压过环境变量**：

- 存储里有记录 → 用它的令牌重建插件配置，版本号取 `stored.version`
- 没记录但状态是 `managed` → 返回 `null`，**故意不启动 Slack**
- 否则 → 回落到环境变量，版本号是字符串 `"environment"`

版本变了就停旧的、起新的；起新的失败就**回滚到上一份配置**；回滚也失败才
抛 `AggregateError`。

这是整个系统里唯一一处「配置热更新」，而且做得完整：有版本号、有回滚、
有回滚失败的处理。**能热更新的东西必须能热回滚**，否则一次坏配置就是一次
彻底的服务中断。

---

## 八、`deployment/`：一个装机能往上加什么

先澄清：**`src/deployment/` 和 `src/deploy/`（[[qm-publish-layer]]）毫无关系。**
后者是 agent 的 `publish` 功能，前者是**这套 QM 装机本身**的定制层。
五个文件其实是三件事。

### 8.1 一个 deployment layer 是什么

它是运维方叠在通用 core 之上的一包东西，从磁盘按这个结构加载：

```
$DEPLOYMENT_LAYER/
  tools/<id>/tool.json
  skills/<name>/SKILL.md
```

`tool.json` 描述一个「这台 agent 电脑上装了的命令行工具」，包括：
它叫什么、要不要向模型宣告、给模型的提示语、它需要哪些凭证路径、
用它的哪些命令需要审批、以及一个可选的 AWS 角色 broker。

`deployment-layer.ts` 638 行里**大约 95% 是敌意输入校验**。这是它真正的内容：

```ts
export type ApprovalDecision = "require_approval" | "deny";
```

**审批决定只有两种，没有 `allow`。** 一个装机层能做的只有收紧——它可以说
「这个命令要人批」或「禁止」，说不了「这个命令放行」。这是
[[qm-resolution-layer]] 那套「只有叠加约束，没有合并权限」的收紧代数
在配置文件层面的又一次落点。

凭证路径的校验尤其严：必须是 `$HOME` 相对路径，不许绝对路径 / `~` / 反斜杠 /
空白 / `..` / `.`，**第一段必须以 `.` 开头**——注释解释了为什么：
「非隐藏的 `$HOME` 路径是持久的 agent 数据，不是凭证」。还要和七个内建凭证
路径（`.aws`、`.ssh`、`.netrc`、`.git-credentials` 等）做重叠检查，
并且各工具之间两两不相交。

为什么这么紧张？因为这些字符串会被**插进 shell 探测命令和生成的 Dockerfile 行**
里。文件里对 `id` 和 `install.binary` 的正则限制都带着注释说明这一点。
用了 broker 的工具，它的 binary 还必须是合法的 POSIX 函数名——
「因为注入的凭证会用一个 shell 函数把它包起来」。

审批规则的编译也防越界：一条原始 `pattern` 必须以 `\b<binary>\b` 开头
且**不含顶层交替**，所以一条规则永远逃不出它自己那个工具。
外加一个约 260 行的手写 ReDoS 静态分析器——和
[[qm-crosscutting]] §3 的 `compileSafeRegex` 是同类工作的第二次实现，
这一次带「歧义预算」计数，超过 1024 就拒。（见 §10 存疑 3。）

### 8.2 装机层会往技能注册表里种子

`deployment-layer-store.ts`（588 行）把层里的 skills 投影进技能注册表，
owner 记作 `system:deployment-layer`。碰撞检查有**四层**：

1. 包内部——两个 skill 物化到同一个路径
2. 与已发布的 skill pack 的文件路径
3. 与非层拥有的同名 skill
4. 与非层拥有的 skill 的物化路径

前两层在 PUT 时抛 4xx，**在写任何东西之前**。

应用是「快照—重放—失败回滚」：先 `structuredClone` 现有的层技能，
逐个 upsert 并逐个校验确实发布成功，归档重复的和不再在包里的，最后才切换运行时。
任何一步出错就 `restoreProjection(snapshot)`，带 `[250, 1000, 4000]` 的重试；
回滚本身再失败才抛复合错误。

`SKILL_MATERIALIZATION_LOCK` 是字符串 `"skills:materialization"`，
用作 **Postgres advisory lock 的键**——是舰队级互斥，不只是进程内。
同一把锁也被技能 API 用。原因很实在：多个 core 实例每 30 秒都会 hydrate
同一个持久层，而技能物化会写共享路径，两个实例绝不能同时投影。
（[[qm-crosscutting]] §8.1 讲的双层锁模式，这里是它的第三个实例。）

失败姿态是**降级不崩溃**：一个存下来的层如果应用不了，按 hash 每种只记一次
日志，并保留**当前**运行时层继续服务。

### 8.3 上线后才能验的五件事

`postdeploy-smoke.ts` 是个独立脚本，`process.argv[1]` 判定入口，
仓库里找不到调用方——大概率由仓库外的 CI 手工触发，从部署内部网络跑。

它检查五件事，共同点是**全部依赖配置、因而无法在部署存在之前验证**：

1. 配置项存在（`DATABASE_URL`、`ORG_ID`、两个签名密钥）
2. **两条 Postgres 系统表查询**
3. 一次完整签名的 admin API 往返
4. 五个健康端点，跨三种 Fly 网络模式，加公网路由
5. Slack 两种令牌各调一次 API

第 2 条最有意思。两条查询是：

```sql
-- 标了 PARALLEL SAFE 但源码里含 EXCEPTION 的 plpgsql 函数
WHERE l.lanname = 'plpgsql' AND p.proparallel = 's' AND p.prosrc ~* '\mEXCEPTION\M'
-- 无效或未就绪的索引
WHERE NOT indisvalid OR NOT indisready
```

第一条抓的是：`BEGIN ... EXCEPTION` 会开一个内部子事务，而子事务在并行 worker
里**做不了**。Postgres 完全信任开发者标的 `PARALLEL SAFE`，标错了只会在
运行时、只在查询计划恰好走并行的时候、只对某些行报错。

第二条抓的是 `CREATE INDEX CONCURRENTLY` 失败或被打断留下的残骸——
这种索引对查询规划器不可见，**但每次写入仍然要维护它**。于是你付了写入代价、
没拿到读取收益，而那些本该被加速的查询悄悄退回全表扫描。

两者的共同形状：**schema 层面的、依赖负载才显现的、不报错只是悄悄变慢或
偶发失败的问题**。单元测试抓不到，因为它们是「已部署的 schema」的属性，
而这个 schema 是由幂等 DDL 惰性创建的——它可能和你以为你发布的不一样。

**上线冒烟该检查的正是这类东西**：不是「服务活着吗」（那是健康检查的事），
而是「这次部署有没有引入一个只在生产负载下才会现形的问题」。

第 3 条同样讲究：它调的是 `GET /v1/admin/sessions?...&_smoke=<uuid>`，
带完整 HMAC 签名和现铸的 portal identity 令牌。这一个请求同时验了
签名鉴权、身份签发、admin ACL、会话存储四层——**用一个真实的业务请求当探针，
而不是一个专用的健康端点。** 那个 `_smoke=<uuid>` 是防缓存的。

---

## 九、第二个进程：出网在哪里被执行

`egress-authz-main.ts` 251 行，是整个调研里唯一一个**不属于主进程**的东西。

它不在 `package.json` 里。`deploy/egress-proxy/start.sh` 用
`node /app/src/egress-authz-main.ts &` 起它，然后起 Envoy，
再用一个循环监视：**任何一个死了整个容器就退出 1**。两者是共生的，
不允许只剩一个。

启动脚本在这之前还做了一件事：给 `169.254.0.0/16` 和 `fd00:ec2::254`
装 iptables REJECT 规则——**尽力而为**（没有 NET_ADMIN 就只警告）。

### 9.1 一个请求要过五层

```
沙箱进程 → HTTPS_PROXY(x:<token>@proxy:48080) → Envoy
  → ① Envoy 静态元数据拒绝（虚拟主机 blocked_metadata）
  → ② Lua 过滤器：删掉客户端自带的 x-egress-upstream-address，调本地 /check
  → ③ 授权服务：令牌 → 策略 → DNS 解析 → 逐 IP 判定
  → ④ Envoy 剥掉 proxy-authorization
  → ⑤ 连到被钉住的那个 IP
```

**云元数据端点被挡了三次**：iptables、Envoy 静态虚拟主机、
以及授权服务里的 `LINK_LOCAL` + `METADATA_HOSTS` 常量。三层各自独立，
任何一层单独失效都还有另外两层。对「SSRF 到 IMDS 偷云凭证」这个后果最严重的
攻击，三重冗余是合理的。

Lua 过滤器**失败关闭**：`pcall` 出错、非 200、或者响应里没有上游地址头，
一律 403。

### 9.2 两套网段表，各自的职责

[[qm-crosscutting]] §4 讲的 `isPrivateNetworkIp` 有 14 个 v4 段加 8 个 v6 段。
这个服务里另有一小张表：v4 的 `169.254/16`、v6 的 `fe80::/10`、
外加单个地址 `fd00:ec2::254`，以及按名字匹配的
`metadata.google.internal` / `metadata.goog`。

两套并存，职责完全不同：

| | 小表 | 大表（`isPrivateNetworkIp`） |
| --- | --- | --- |
| 内容 | 链路本地 + 云元数据 | 全部私网/保留/文档网段 |
| 何时生效 | **无条件，每个请求** | 仅当策略里 `denyPrivateNetworks` 为真 |
| 能不能开洞 | **不能** | 能（`privateNetworkAllowedHosts`） |

小表是**不可协商的地板**——任何策略、任何令牌都改不了它。
大表是一个**可选的策略控制**，只在对话对外部人开放时才打开
（`securityPolicy.inboundScreening === "external"`），而且打开之后还会把 core
自己的主机加回白名单，免得 agent 把自己锁在控制面之外。

**「必须永远成立的」和「可以按情况配置的」应该是两张表，不是一张表加一堆例外。**

### 9.3 DNS rebinding：钉住 IP，而不是重新解析

解析和连接之间的时间差是经典的 TOCTOU 攻击面——检查时解析到一个公网 IP，
连接时解析到 `127.0.0.1`。这里的处理是**架构性的**，不靠重查：

```ts
// 一次解析拿到全部地址
dnsLookup(host, { all: true, verbatim: true })
// 每一个都要过：ips.some(bad) 就整体拒绝
// 通过后返回 ips[0]，写进 x-egress-upstream-address
```

Envoy 侧配的是 `original_dst` 集群 + `use_http_header: true`，
**直接连那个字面 IP，不再做第二次 DNS 查询**。窗口不是被缩小了，是不存在。

两个细节值得记：

- 校验用的是 `ips.some(bad)` 而不是「第一个好的就用」——
  **一条恶意 A 记录就毒化整个应答**。混入一个 `127.0.0.1` 的 DNS 轮询答案
  会被整体拒绝，而不是碰运气。
- 那个上游地址头在 Lua 里被**先删后写**：客户端自己带一个进来是没用的。

剩下的边界要说清楚：只用了 `ips[0]`，所以没有故障转移；
授权是按 HTTP 请求做的，一条长活的 CONNECT 隧道只在建立时授权一次。

### 9.4 策略不查，它在令牌里

这个服务**没有策略存储，每个请求除 DNS 外零 I/O**。`EgressPolicy` 是
capability token 上的一个声明——**验签就是取策略**。

```ts
let policy = DENY_ALL;                                    // allowedHosts: ["deny.invalid"]
if (claims) policy = claims.egress;
else if (noTokenAtAll && EGRESS_TOKENLESS === "open") policy = OPEN;
```

第三行有个微妙之处：**带了一个无效/过期令牌，即使在 tokenless-open 模式下也是
`DENY_ALL`**。「没带钥匙」和「带了一把坏钥匙」被区别对待——后者说明有人试图
用凭证访问，那就按凭证的规矩来。

代价说清楚：令牌 TTL 60 分钟，**策略改动要等下一个回合的新令牌才生效**，
这个服务里没有吊销路径。对「收紧出网策略」这个操作来说，这意味着最长一小时的
生效延迟。

还有一处反直觉的：`egressClaimAllowingControlPlane` 在没什么可执行时返回
`undefined`，而 `egressDecision(host, undefined)` 返回**放行**。所以
「令牌里没有策略」= 全开，「没有有效令牌」= 全关。同一个服务里
两种「没有」意思相反——都对，但需要读两遍才确定。

审计对**放行和拒绝都记**，包在 try/catch 里吞掉，
**审计失败绝不改变判定**。落库有三级优先：中继回 core → 直连 Postgres →
内存。中继带缓冲（每 2 秒、每批最多 500、硬上限 5000 并计数丢弃）、
10 秒超时、收到 SIGTERM 时刷一次。core 那边收到后**不信任中继上报的
`allowed` 字段**，自己从 `verdict === "ok"` 重新推导，并强制盖上
`source: "proxy"`。

**跨信任边界传过来的判定结论要重新推导，不要直接采信。**

---

## 十、存疑

1. **`ScopeId` 是裸 `string`。** 一个占全仓 42% 类型导入的核心概念，
   编译器完全不设防。代价在 `wiring.ts` 里能看到几处 `as ScopeId` 断言。
   模板字面量类型或品牌类型都可行，成本是所有从存储读出的字符串要过一次校验。
   没找到注释说明这是权衡后的选择还是历史遗留。

2. **密钥闸门表里有两个永远不会触发的项。** `fly-sandbox` 判
   `SANDBOX_BACKEND === "fly"`，`fly-deploy` 判 `DEPLOY_PROVIDER === "fly"`，
   而 `sandboxBackendEnvStrict` 只接受 `aws | local | sprites`——配 `fly` 会先在
   枚举校验那里崩掉。声明式表格的典型代价：**表项不会随对应代码路径的消失而
   自动失效**，而漂移测试盯的是「表和文档一致」，不是「表和代码一致」。

3. **两个手写的 ReDoS 分析器。** `util/safe-regex.ts` 67 行，
   `deployment/deployment-layer.ts` 里的 `approvalPatternTooSlow` 约 260 行
   带歧义预算。两者面对同一类输入（管理员写的正则），做同一件事，
   实现完全独立。后者更完整，前者更简单。至少应该有一个引用另一个，
   或者说明为什么需要两套强度。

4. **`ServerDeps` 的 76 个字段全部可选。** 漏传一个依赖不是类型错误，
   只是某族路由静默失效。而 `BuiltApp`（65 字段）到 `ServerDeps`（66 键）
   的投影是手工维护的——加一个组件要在两个地方各改一次，忘了第二处编译照过。

5. **`orgId()` 与 `config.orgId` 是两条并行路径。** 前者直读
   `process.env.ORG_ID`，被 32 个叶子模块使用；后者在 `Config` 里，
   被 `wiring.ts` 使用。两者取值相同，但如果哪天 org 变成按请求决定的，
   叶子那条路径要全部改写。`api/routes/shared.ts` 里那个
   `orgScope = (_deps?: unknown) => configOrgScope()`（收 deps 却忽略）
   看得出来这个缝是有意留的，但没有注释说明。

6. **出网策略的生效延迟最长一小时，且无吊销。** 策略随 capability token
   分发，TTL 60 分钟，授权服务没有任何吊销机制。收紧一条出网规则之后，
   已经拿到令牌的沙箱在最长一小时内仍按旧策略放行。对一个「发现某个域名正在
   被滥用，立刻切断」的场景，这个延迟是实质性的。

7. **`postdeploy-smoke.ts` 在仓库里没有调用方。** 没有 npm 脚本、
   没有 GitHub workflow 引用、文档里也找不到。唯一的 importer 是它自己的测试。
   一个只在人记得跑的时候才跑的上线检查，等于没有。

---

## 十一、可迁移做法

**关于领域词汇**

1. 数一下每个核心类型被 import 多少次。这个分布比架构文档更能说明系统实际上
   围绕什么概念组织。
2. 一个占 40% 导入率的标识符类型，值得付出品牌类型的成本——裸 `string`
   会在边界处逼出一堆断言。
3. 用几个小的派生谓词（`isSharedScope` / `isManageableCreationScope`）
   给枚举切分出「有哪些性质」，比在各处写 `kind === "a" || kind === "b"` 好，
   而且切分不重合本身就是一条可以检验的设计约束。

**关于配置**

4. 环境变量解析要有严格版本：**打错的值让进程起不来，不要静默回落到默认值**。
   报错里带上变量名、收到的值、和合法取值列表。
5. 环境变量界面用秒、内部用毫秒时，靠字段名后缀区分（`xxxSec` vs `xxxMs`），
   不要靠记忆。
6. 默认值集中成一张冻结表，用 `?? DEFAULTS.x` 引用。
7. **崩溃 vs 警告的分界线**：输入不可解释或自相矛盾 → 崩；
   输入可解释且自洽但产生一个残缺但能跑的系统 → 警告，并在警告里明说
   **哪个能力会悄悄不存在**。
8. **一个装了一半的安全控制必须崩，一个完全没装的可选安全控制可以只警告。**
   而且反方向也要崩——配了参数却没启用，说明操作者以为它生效了。
9. 降级方向安全的组件（缺密钥就全部拒绝）可以只警告；
   降级方向不安全的必须崩。
10. 把「哪个密钥在什么条件下必需」提炼成一张
    `(名字, 条件谓词)` 的表，让它可以被漂移测试盯住。
    但要意识到：**表项不会随代码路径的消失而自动失效。**
11. 「缺失」的定义要包含「是垃圾」——空白、`placeholder`、`changeme`
    都算缺失。

**关于装配**

12. 二选一的实现切换，把「二选一」提炼成一个工厂函数（`artifactMap`），
    这样新增一个 store 的成本是一行而不是一个三元表达式。
13. 区分三类缺失：**状态**给内存孪生，**能力**直接不存在（`undefined`），
    **协调**给 noop。一个假的加密比没有加密更危险。
14. 推断出来的默认适合无关紧要的东西；要紧的东西（会话历史存哪儿）
    应该逼部署者明说，说了却缺前置条件就崩。
15. 循环依赖用「空壳 + 后填」打开时，把所有这类绑定集中在装配文件里——
    它们是这个系统全部循环的清单。代价是这些绑定全靠「箭头函数在构造期
    不被调用」成立。
16. 承认装配文件会容纳跨组件的策略逻辑。它的真实职责不是构造对象，
    是**拥有对象之间的边**。

**关于启动与关停**

17. 后台工作先于 HTTP 端口启动——先开始干活，再开始接流量。
18. 只有影响正确性的预热才 `await`，其余走浮动 promise。
19. 关停分级：先停所有定时器（不产生新工作）→ 排空 → **无条件释放租约** →
    关连接。排空失败不能跳过释放租约。
20. 兜底超时里不要直接 `exit`，先花一个有上限的时间（这里 3 秒）
    释放租约再退——**租约比干净退出更要紧，但卡住的数据库不能扣住进程。**
21. 兜底路径需要的能力要显式暴露在接口上（`releaseInFlightRuns()`），
    不要指望复用正常路径的内部步骤。
22. 能热更新的东西必须能热回滚，并且要处理「回滚也失败」。

**关于装机定制层**

23. 让定制层**只能收紧**：审批决定只有 `require_approval` 和 `deny`，
    没有 `allow`。
24. 定制层的字符串如果会被插进 shell 或生成的 Dockerfile，
    校验要严到近乎偏执，并在代码里注明为什么。
25. 凭证路径必须是隐藏路径（第一段以 `.` 开头）——非隐藏的家目录路径是
    持久数据，不是凭证。
26. 规则不能逃出它自己的作用域：审批模式必须以目标程序名开头，
    且不含顶层交替。
27. 投影式的应用（把定制层的技能种进注册表）要「快照—重放—失败回滚」，
    并且回滚本身失败要抛复合错误。
28. 多实例都会 hydrate 同一份配置时，物化操作要用**舰队级**互斥
    （Postgres advisory lock），不是进程内锁。
29. 应用失败的姿态是保留当前运行时配置继续服务，按内容哈希每种失败只记一次日志。

**关于上线后的检查**

30. 上线冒烟要检查的不是「服务活着吗」，而是「这次部署有没有引入一个只在
    生产负载下才现形的问题」——schema 层面的、依赖负载的、不报错只是变慢的。
31. 具体两条值得抄：标了 `PARALLEL SAFE` 却含 `EXCEPTION` 的 plpgsql 函数；
    `indisvalid`/`indisready` 为假的残留索引（失败的
    `CREATE INDEX CONCURRENTLY`，付写入代价不给读取收益）。
32. 用一个**真实的业务请求**当探针（带完整签名的 admin API 往返），
    一次验完鉴权、身份、ACL、存储四层，比专用健康端点覆盖得多。
    加一个随机查询参数防缓存。

**关于出网执法**

33. 把「必须永远成立的」和「可以按情况配置的」做成两张表，
    不要一张表加一堆例外。
34. 后果最严重的那条（SSRF 到云元数据）值得三层冗余：iptables、
    代理静态规则、授权服务常量。
35. DNS rebinding 靠**钉住 IP** 解决而不是重新解析：授权时解析一次，
    把 IP 写进一个受控的头，代理直接连那个字面 IP。窗口不是缩小，是消失。
36. 解析出多个地址时，**任意一个不合格就整体拒绝**，不要「第一个好的就用」。
37. 客户端可能伪造的头要**先删后写**。
38. 策略随令牌分发，验签就是取策略——服务本身零 I/O。
    但要明说代价：策略变更有一个等于令牌 TTL 的生效延迟，且没有吊销路径。
39. 「没带令牌」和「带了一个坏令牌」要区别对待：后者说明有人在试图用凭证，
    应当按更严的规则处理。
40. 审计对放行和拒绝都记，且审计失败绝不改变判定。
41. 跨信任边界传过来的判定结论要**重新推导**，不要直接采信上报的字段。
42. 两个必须共生的进程，用一个监视循环保证「任何一个死了就整体退出」。

---

## 十二、与其他篇的连接

**与全部十四篇**：`wiring.ts` 的 `BuiltApp` 是一张组件清单，前面每一篇讲的
子系统都在这 65 个字段里占一格。想看某个组件在什么条件下存在、
它的持久实现和内存实现分别是什么，答案都在这一个文件里。

**与 [[qm-overview]]**：§2.5「供应商中立是架构约束」在本篇 §4 得到了量化——
三条切换轴，其中 `artifactMap` 那条用两行覆盖了约 30 个 store。
§2.6「durable by default」的实现机制也在那里。
本篇同时更正了 overview 的模块分组：这五个顶层文件和 `deployment/`
从未进入 A–J 任何一组。

**与 [[qm-authz-layer]]**：那篇讲出网策略**怎么算出来**（`Resolution.egress`），
本篇 §9 讲它**在哪里被执行**——一个独立进程，策略搭令牌的便车过去。
两篇合起来才是完整的出网故事。

**与 [[qm-run-lifecycle]]**：那篇讲租约、排空、回收。本篇 §7.2 是它们的
**装配与关停侧**：十个 sweeper 的间隔、关停的五个阶段、
以及 `stopWithBackstop` 那个「宁可强杀也要先释放租约」的三层兜底。

**与 [[qm-resolution-layer]]**：`deployment/` 的审批决定只有
`require_approval | deny`——没有 `allow`，是那篇收紧代数在配置文件层的落点。

**与 [[qm-skills-layer]]**：`deployment-layer-store.ts` 会把装机层的技能
种进那篇讲的注册表，四层碰撞检查加上舰队级的
`SKILL_MATERIALIZATION_LOCK`。

**与 [[qm-crosscutting]]**：`compileSafeRegex` 和
`approvalPatternTooSlow` 是同一件事的两次独立实现（§10 存疑 3）；
双层锁模式在本篇 §8.2 是第三次出现；
`isPrivateNetworkIp` 的大表与本篇 §9.2 的小表构成分工。

**与 [[qm-publish-layer]]**：`src/deployment/` 与 `src/deploy/` 名字接近而
毫无关系，本篇 §8 开头澄清了这一点。

**与 [[qm-surface-mirror]]**：`liveFallback` 那段消息形状翻译逻辑住在
`wiring.ts` 里，是 §6.1「装配文件拥有边」的一个实例。

**收尾**：至此 `src/` 全部目录与顶层文件均已覆盖。
[[qm-overview]] §五只剩最后一项——把十五篇里散落的可迁移做法按问题
（而非按模块）收敛成一份清单。

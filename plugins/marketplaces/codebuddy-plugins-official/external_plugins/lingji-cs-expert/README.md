# 灵光记客服专家 · 小灵（lingji-cs-expert）

灵光记（Lynse）内部客服专家。客服同事把客户原话贴进来，小灵从内置的 82 条 FAQ 知识库里模糊匹配出标准答案（带 Q 编号），输出客服可直接复制给客户的亲民话术；查不到就如实建议转人工，**绝不编造**。

> 完全自包含：知识库随插件打包在 `data/qa/`，检索用内置 Python 脚本实现，**不依赖任何外部 MCP / 网络 / 服务**。

## 目录结构

```
lingji-cs-expert/
├── .codebuddy-plugin/plugin.json   # 插件清单（市场展示信息 + agents/skills 声明）
├── agents/lingji-cs-expert.md      # 专家人设「小灵」与工作流程
├── skills/lingji-qa/               # FAQ 检索技能
│   ├── SKILL.md
│   └── scripts/retrieve.py         # 离线模糊检索（中文二元组匹配）
├── data/qa/                       # 12 个分组 md，共 82 条 QA（知识库）
├── avatars/expert.png             # 专家头像
└── README.md
```

## 本地试用

把整个 `lingji-cs-expert/` 目录复制到：
`~/.workbuddy/plugins/marketplaces/my-experts/plugins/`
然后打开 WorkBuddy 专家中心即可看到「小灵」。

或直接跑检索验证：
```bash
python3 lingji-cs-expert/skills/lingji-qa/scripts/retrieve.py "卡片连不上手机咋整" --top 3
```

## 发布到市场（让更多人/同事搜到）

本插件满足官方市场的上架要求（含完整 `.codebuddy-plugin/plugin.json` + README + 通过基本安全审查）。发布有两条路：

### 路线 A：自己托管 GitHub 市场（推荐，免审核、立即可用）
1. 在 GitHub 新建一个**公开**仓库（如 `lingji-cs-expert`）。
2. 把本目录全部内容推上去（注意把 `plugin.json` 里的 `repository` 改成你的真实仓库地址）。
3. 任何人（含同事）在 WorkBuddy/CodeBuddy 里执行：
   ```
   /plugin marketplace add <你的GitHub用户名>/lingji-cs-expert
   /plugin install lingji-cs-expert
   ```
   即可在专家中心搜到并安装「小灵」。**无需平台审核、无需等合并。**

### 路线 B：提交 PR 进官方市场（与那 206 个并列）
官方市场就是 GitHub 仓库 `github.com/zhizhunbao/workbuddy`，清单在 `plugins/marketplaces/codebuddy-plugins-official/`。
1. Fork 该仓库，把本插件放进 `plugins/marketplaces/codebuddy-plugins-official/plugins/lingji-cs-expert/`。
2. 修改根目录 `marketplace.json`，在 `plugins` 数组里加一条本插件条目。
3. 提 PR。维护者审核合并后，所有用户都能在官方市场搜到「小灵」。

> 官方市场贡献要求：完整 `.codebuddy-plugin/plugin.json` + 清晰 README + 通过基本安全审查。本插件均已满足。

## 维护与扩展

- **更新知识库**：改 `data/qa/` 下的 md（保持 `### Qx.y 标题` 格式），下次安装即生效。
- **未来加功能**：本插件是 agent + skill 结构，后续可继续加技能（如订单查询、日志分析等），直接在 `skills/` 下扩展即可。

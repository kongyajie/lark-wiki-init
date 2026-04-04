---
theme: smartblue
highlight: a11y-dark
---

# 用 AI Agent + lark-cli 一键生成飞书知识库目录结构

## 痛点：手动创建 50+ 文档有多痛？

最近在搭建一个「AI Native Builder OS」知识库，规划了认知层、技能层、实践层、输出层四大板块，加上子分类，总共 16 个文档节点。

打开飞书知识库，点击「新建文档」→ 输入标题 → 写入模板内容 → 拖到正确的层级位置……

重复 16 次。

这还只是初始结构。如果后续要建一个更大的知识库，比如团队的技术文档体系（50+ 节点），手动操作简直是噩梦。

**能不能一句话搞定？**

## 方案：Claude Code + lark-cli + 自定义 Skill

### 整体思路

```
用户描述目录结构 → AI 生成 YAML 配置 → Python 脚本调用 lark-cli → 批量创建知识库节点
```

最终效果：在 Claude Code 中说一句「帮我创建飞书知识库」，AI 就会引导你完成整个流程。

### 技术栈

- **Claude Code**：Anthropic 的 CLI AI 助手，支持自定义 Skill 扩展
- **lark-cli**：飞书命令行工具，可以通过命令行操作飞书文档、知识库等
- **Python**：胶水脚本，解析 YAML 配置并递归调用 lark-cli

## 实现过程

### Step 1：定义目录结构（YAML 配置）

用 YAML 描述知识库的树形结构，直观且易编辑：

```yaml
space: "AI_Native_Builder_OS"
root:
  title: "AI Native Builder OS"
  content: "# AI Native Builder OS\n\n构建 AI 原生开发者的知识体系与工作流。"
  children:
    - title: "认知层"
      content: "# 认知层\n\n理解 AI 时代的底层逻辑。"
      children:
        - title: "AI 时代的思维模型"
          content: "# AI 时代的思维模型\n\n## 从工具思维到协作思维\n\n待填写"
        - title: "技术趋势与判断"
          content: "# 技术趋势与判断\n\n## LLM 能力边界\n\n待填写"
    - title: "技能层"
      content: "# 技能层\n\n掌握 AI 原生开发的核心技能。"
      children:
        - title: "Prompt Engineering"
        - title: "AI 编程工具链"
        - title: "Agent 开发"
    # ... 更多节点
```

### Step 2：核心脚本（递归创建）

核心逻辑很简单——解析 YAML，递归遍历树，每个节点调用 `lark-cli docs +create`：

```python
def create_tree(space, node, parent_node=None, depth=0, delay=1.0):
    title = node["title"]
    content = node.get("content", f"# {title}")

    # 调用 lark-cli 创建节点
    result = create_node(space, title, content, parent_node)

    # 获取返回的 wiki_node_token，用于挂载子节点
    token = result.get("wiki_node_token") if result else None

    # 递归创建子节点
    for child in node.get("children", []):
        time.sleep(delay)  # 避免频率限制
        create_tree(space, child, parent_node=token, depth=depth+1, delay=delay)
```

关键点：`lark-cli docs +create` 返回的 `wiki_node_token` 是父子关系的纽带，每次创建子节点时传入父节点的 token。

### Step 3：用 subprocess 调用 lark-cli（避免 shell 转义坑）

```python
def create_node(space, title, content, parent_node=None):
    cmd = [
        "lark-cli", "docs", "+create",
        "--space", space,
        "--title", title,
        "--content", content,  # Python 字符串中 \n 是真正的换行
    ]
    if parent_node:
        cmd.extend(["--parent-node", parent_node])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return json.loads(result.stdout)
```

**为什么用 `subprocess` 而不是直接拼 shell 命令？** 这是我踩的第一个大坑，后面详细说。

### Step 4：封装为 Claude Code Skill

创建 `SKILL.md`，定义触发条件和工作流程：

```yaml
---
name: lark-wiki-init
description: |
  批量创建飞书知识库目录结构。当用户想要在飞书知识库中
  批量创建文档目录树、初始化知识库结构时触发。
---
```

安装后，在 Claude Code 中说「帮我创建飞书知识库」就能触发，AI 会：
1. 引导你描述目录结构
2. 生成 YAML 配置
3. 先 `--dry-run` 预览
4. 确认后执行创建

## 效果展示

### dry-run 预览

```
知识库空间: AI_Native_Builder_OS

=== 预览模式 ===

└── AI Native Builder OS
    ├── 认知层
    │   ├── AI 时代的思维模型
    │   └── 技术趋势与判断
    ├── 技能层
    │   ├── Prompt Engineering
    │   ├── AI 编程工具链
    │   └── Agent 开发
    ├── 实践层
    │   ├── 项目实战记录
    │   ├── 踩坑与复盘
    │   └── 最佳实践
    └── 输出层
        ├── 技术文章
        ├── 开源项目
        └── 分享演讲

共 16 个节点将被创建
```

确认无误，去掉 `--dry-run` 执行，16 个节点在 20 秒内全部创建完成。

## 踩坑记录（重点）

### 坑 1：Shell `\n` 转义问题

**现象**：文档内容中出现字面的 `\n` 而不是换行。

**原因**：在 shell 中直接传递含 `\n` 的字符串时，不同 shell 对转义的处理不一致。比如：

```bash
# 这样写，\n 可能不会被解析为换行
lark-cli docs +create --content "# 标题\n\n内容"
```

更糟糕的是，如果用 `$()` 嵌套命令，转义会更加混乱：

```bash
# 千万别这样写
lark-cli docs +create --content "$(echo '# 标题\n\n内容')"
```

**解决方案**：用 Python `subprocess` 直接传参。Python 字符串中的 `\n` 会被正确处理为换行符，传给子进程时不经过 shell 解析：

```python
subprocess.run([
    "lark-cli", "docs", "+create",
    "--content", "# 标题\n\n内容"  # 这里的 \n 是真正的换行
], capture_output=True, text=True)
```

### 坑 2：知识库节点没有公开的删除 API

**现象**：创建了错误的结构，想删掉重来，发现 lark-cli 没有删除命令。

**真相**：飞书知识库目前没有公开的批量删除 API。要删除节点，只能：
- 在飞书客户端手动一个个删除
- 或者把节点移到回收站

**教训**：创建前一定要用 `--dry-run` 预览确认。我因为这个坑，手动删了两次错误创建的节点树……

### 坑 3：API 频率限制

**现象**：批量创建时，部分请求返回 429 错误。

**解决方案**：每次创建间隔 1 秒。脚本默认 `--delay 1.0`，如果还被限流可以调大：

```bash
python3 wiki_init.py structure.yaml --delay 2
```

### 坑 4：权限配置容易遗漏

**现象**：调用 API 返回权限不足。

**解决方案**：在飞书开放平台为应用添加以下权限，并重新发布版本：
- `wiki:node:create` — 创建知识库节点
- `docx:document:create` — 创建文档

注意：添加权限后需要重新发布应用版本才能生效。

## 开源地址

项目已开源，包含完整的 Skill 定义、Python 脚本和示例配置：

**GitHub**: [kongyajie/lark-wiki-init](https://github.com/kongyajie/lark-wiki-init)

### 快速开始

```bash
# 作为 Claude Code Skill 安装
npx skills add kongyajie/lark-wiki-init -g -y

# 或者直接使用脚本
git clone https://github.com/kongyajie/lark-wiki-init.git
cd lark-wiki-init
python3 scripts/wiki_init.py examples/minimal.yaml --dry-run
```

### 项目结构

```
lark-wiki-init/
├── SKILL.md              # Skill 定义
├── README.md             # 使用说明
├── scripts/
│   └── wiki_init.py      # 核心脚本
├── references/
│   └── lark-cli-wiki.md  # lark-cli 命令参考
├── examples/
│   ├── ai-builder-os.yaml    # 完整示例（16 节点）
│   └── minimal.yaml           # 最小示例（3 节点）
└── evals/
    └── evals.json        # 测试用例
```

## 总结

| 方式 | 创建 16 个节点耗时 | 体验 |
|------|-------------------|------|
| 手动操作 | ~15 分钟 | 枯燥、易出错 |
| 脚本批量创建 | ~20 秒 | 一次编写，反复使用 |
| Claude Code Skill | ~30 秒 | 一句话搞定，AI 帮你生成配置 |

这个项目本身不复杂，但踩坑的过程挺有价值。Shell 转义、API 限制、权限配置这些问题，每个都能让你卡半天。希望这篇文章和开源项目能帮你少走弯路。

AI 时代的开发方式正在变化——不是 AI 替你写代码，而是你和 AI 协作，把重复劳动自动化，把时间花在更有价值的事情上。

---

> 如果觉得有用，欢迎 Star 和分享。有问题或建议，欢迎在 GitHub 提 Issue。

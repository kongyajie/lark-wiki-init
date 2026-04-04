---
theme: smartblue
highlight: a11y-dark
---

# 用 AI Agent + lark-cli 一键生成飞书知识库目录结构（附开源工具）

> 手动在飞书知识库里创建 16 个文档节点，我花了 15 分钟。用 AI Agent 自动化之后，20 秒。

## 起因

最近在搭建个人知识体系，想在飞书知识库里建一个「AI Native Builder OS」——按认知层、技能层、实践层、输出层四个维度组织，每个维度下面还有子分类，总共 16 个文档节点。

打开飞书知识库，开始操作：

1. 点「新建文档」
2. 输入标题
3. 写入模板内容
4. 拖到正确的层级位置

重复 16 次。

到第 8 个的时候我就崩溃了——这也太机械了。而且一旦结构规划有调整，又得手动改一遍。

作为一个天天用 AI 写代码的人，我决定把这件事自动化。

## 思路

我日常用 Claude Code 做开发，它支持自定义 Skill（可以理解为给 AI 加装的"技能包"）。同时飞书有个命令行工具 `lark-cli`，可以通过终端操作文档和知识库。

把两者结合起来：

```
描述目录结构 → YAML 配置 → Python 脚本递归调用 lark-cli → 批量创建节点
```

封装成 Claude Code Skill 之后，以后只需要说一句「帮我创建飞书知识库」，AI 就能引导完成整个流程。

## 什么是 Claude Code Skill？

简单说，Skill 是 Claude Code 的扩展能力。你写一个 `SKILL.md` 文件，定义触发条件和执行指令，AI 就能在合适的时机自动调用。

比如我定义了：

```yaml
---
name: lark-wiki-init
description: |
  批量创建飞书知识库目录结构。当用户想要在飞书知识库中
  批量创建文档目录树、初始化知识库结构时触发。
---
```

之后在 Claude Code 里说「帮我初始化飞书知识库」，它就知道该调用这个 Skill，引导我提供配置、预览结构、执行创建。

## 实现

### 1. 用 YAML 描述目录树

YAML 天然适合描述树形结构，比 JSON 可读性好得多：

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
      children:
        - title: "Prompt Engineering"
        - title: "AI 编程工具链"
        - title: "Agent 开发"
    - title: "实践层"
      children:
        - title: "项目实战记录"
        - title: "踩坑与复盘"
        - title: "最佳实践"
    - title: "输出层"
      children:
        - title: "技术文章"
        - title: "开源项目"
        - title: "分享演讲"
```

每个节点有 `title`（标题）、`content`（Markdown 内容，可选）、`children`（子节点，可选）。不写 content 的话，脚本会自动用 `# {title}` 作为默认内容。

### 2. 核心脚本：递归创建

核心逻辑就一个递归函数——遍历树，每个节点调用 `lark-cli docs +create`，拿到返回的 `wiki_node_token` 后传给子节点：

```python
def create_tree(space, node, parent_node=None, depth=0, delay=1.0):
    title = node["title"]
    content = node.get("content", f"# {title}")

    # 调用 lark-cli 创建节点
    result = create_node(space, title, content, parent_node)

    # 拿到 wiki_node_token，这是父子关系的纽带
    token = result.get("wiki_node_token") if result else None

    # 递归创建子节点
    for child in node.get("children", []):
        time.sleep(delay)  # 避免触发频率限制
        create_tree(space, child, parent_node=token, depth=depth+1)
```

调用 lark-cli 的部分，用 `subprocess` 直接传参（原因后面踩坑部分会讲）：

```python
def create_node(space, title, content, parent_node=None):
    cmd = [
        "lark-cli", "docs", "+create",
        "--space", space,
        "--title", title,
        "--content", content,
    ]
    if parent_node:
        cmd.extend(["--parent-node", parent_node])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return json.loads(result.stdout)
```

### 3. dry-run 预览

因为飞书知识库节点创建后没法批量删除（对，这也是个坑），所以加了 `--dry-run` 模式，先看看要创建什么：

```bash
$ python3 scripts/wiki_init.py structure.yaml --dry-run

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

确认没问题，去掉 `--dry-run` 执行。16 个节点，大约 20 秒全部创建完成。

## 踩坑实录

这个项目代码量不大，但踩的坑不少。每个都能让你卡半天，记录下来希望帮后来人避坑。

### 坑 1：Shell `\n` 转义——最隐蔽的 Bug

**现象**：创建出来的文档里，内容出现了字面的 `\n`，而不是换行。

**排查过程**：一开始我让 Claude Code 直接在 shell 里拼命令：

```bash
lark-cli docs +create --content "# 标题\n\n正文内容"
```

看起来没问题对吧？但 shell 双引号里的 `\n` **不会**被解析为换行符——它就是字面的反斜杠加 n。

更坑的是，如果你用 `$()` 嵌套：

```bash
lark-cli docs +create --content "$(echo -e '# 标题\n\n内容')"
```

不同 shell（bash/zsh）、不同系统对 `echo -e` 的行为还不一样，有的支持有的不支持。

**解决方案**：别跟 shell 转义较劲了。用 Python `subprocess` 直接传参，Python 字符串里的 `\n` 就是真正的换行符，传给子进程时不经过 shell：

```python
subprocess.run([
    "lark-cli", "docs", "+create",
    "--content", "# 标题\n\n内容"  # Python 里 \n 就是换行
], capture_output=True, text=True)
```

**教训**：涉及特殊字符传参时，能不过 shell 就别过 shell。

### 坑 2：知识库节点不能批量删除

**现象**：第一次创建的结构有问题，想删掉重来，发现 lark-cli 没有删除命令。去翻飞书开放平台文档，也没找到公开的删除 API。

**真相**：飞书知识库节点目前只能在客户端手动删除，或者移到回收站。没有 API 支持批量删除。

我因为这个坑，手动在飞书客户端里一个个删了两次错误创建的节点树。每次十几个节点，点到手酸。

**教训**：这就是为什么 `--dry-run` 是必须的。创建前一定要预览确认，因为撤销的成本很高。

### 坑 3：API 频率限制（429）

**现象**：批量创建到一半，部分请求开始报错。

**原因**：飞书 API 有调用频率限制，连续快速请求会触发 429 Too Many Requests。

**解决方案**：每次创建之间加 1 秒延迟。脚本默认 `--delay 1.0`，如果节点特别多可以调大：

```bash
python3 wiki_init.py structure.yaml --delay 2
```

16 个节点加上延迟大概 20 秒，完全可以接受。

### 坑 4：权限配置容易遗漏

**现象**：`lark-cli` 登录成功了，但创建节点时报权限不足。

**原因**：飞书应用需要单独配置 API 权限，光登录不够。

**需要的权限**：
- `wiki:node:create` — 创建知识库节点
- `docx:document:create` — 创建文档

去飞书开放平台 → 应用管理 → 权限管理里添加，添加后**需要重新发布应用版本**才能生效。这一步很容易忘。

## 使用方式

### 方式一：Claude Code Skill（推荐）

如果你也在用 Claude Code，一行命令安装：

```bash
npx skills add kongyajie/lark-wiki-init -g -y
```

然后在 Claude Code 里说「帮我创建飞书知识库目录结构」，AI 会：

1. 引导你描述想要的目录结构
2. 自动生成 YAML 配置文件
3. 先 `--dry-run` 预览让你确认
4. 确认后执行批量创建

全程对话式操作，不需要手写 YAML。

### 方式二：独立脚本

不用 Claude Code 也能用，直接跑 Python 脚本：

```bash
# 克隆项目
git clone https://github.com/kongyajie/lark-wiki-init.git
cd lark-wiki-init

# 安装依赖
pip install pyyaml
npm install -g lark-cli
lark-cli auth login

# 预览
python3 scripts/wiki_init.py examples/minimal.yaml --dry-run

# 执行创建
python3 scripts/wiki_init.py examples/minimal.yaml

# 挂到已有节点下
python3 scripts/wiki_init.py structure.yaml --parent-node wikcnXXXXXX
```

## 项目结构

```
lark-wiki-init/
├── SKILL.md                   # Claude Code Skill 定义
├── README.md                  # 使用说明
├── scripts/
│   └── wiki_init.py           # 核心脚本
├── references/
│   └── lark-cli-wiki.md       # lark-cli 命令参考
├── examples/
│   ├── ai-builder-os.yaml     # 完整示例（16 节点）
│   └── minimal.yaml           # 最小示例（3 节点）
└── evals/
    └── evals.json             # Skill 触发测试用例
```

## 效率对比

| 方式 | 创建 16 个节点 | 可复用性 |
|------|---------------|---------|
| 飞书客户端手动操作 | ~15 分钟 | 每次都要重复 |
| Python 脚本 + YAML | ~20 秒 | 改配置即可复用 |
| Claude Code Skill | ~30 秒 | 对话式操作，零配置门槛 |

## 写在最后

这个项目本身代码量很小，核心逻辑就是一个递归函数。但从想法到落地的过程中，shell 转义、API 限制、权限配置、不可逆操作这些坑，每个都实实在在地卡了我一阵。

把它做成 Claude Code Skill 开源出来，一方面是方便自己以后复用，另一方面也希望帮到有同样需求的人。

更大的感受是：AI 时代的开发方式确实在变。以前遇到这种批量操作，可能写个脚本就完事了。现在多了一层——把脚本封装成 AI 能调用的 Skill，下次连脚本都不用自己跑，跟 AI 说一句话就行。

**开源地址**：[github.com/kongyajie/lark-wiki-init](https://github.com/kongyajie/lark-wiki-init)

如果对你有帮助，欢迎 Star。有问题或建议，GitHub Issue 见。

---

*本文涉及的工具：[Claude Code](https://docs.anthropic.com/en/docs/claude-code)、[lark-cli](https://github.com/nicepkg/lark-cli)*

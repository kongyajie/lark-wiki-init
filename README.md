# lark-wiki-init

用 AI Agent + lark-cli 一键批量创建飞书知识库目录结构。

## 这是什么

一个 Claude Code Skill，让你用一句话就能在飞书知识库中批量创建完整的文档目录树。告别手动一个个创建文档的痛苦。

## 安装

### 作为 Claude Code Skill 安装

```bash
npx skills add kongyajie/lark-wiki-init -g -y
```

### 前置条件

1. 安装 lark-cli：
```bash
npm install -g lark-cli
```

2. 登录飞书：
```bash
lark-cli auth login
```

3. 确保飞书应用有以下权限：
   - `wiki:node:create`
   - `docx:document:create`

4. 安装 Python 依赖：
```bash
# macOS (Homebrew Python)
pip install --user pyyaml
# 或使用 brew
brew install libyaml

# Linux / 其他
pip install pyyaml
```

## 使用方式

### 方式一：通过 Claude Code Skill（推荐）

安装 skill 后，在 Claude Code 中直接说：

> "帮我在飞书知识库创建目录结构"

AI 会引导你描述目录结构，生成 YAML 配置，预览确认后执行创建。

### 方式二：独立脚本

1. 编写 YAML 配置文件：

```yaml
space: "7620663498296642741"  # 空间 ID，通过 lark-cli wiki spaces list 查看
root:
  title: "知识管理中心"
  content: "# 知识管理中心\n\n欢迎来到知识库。"
  children:
    - title: "学习笔记"
      content: "# 学习笔记\n\n记录学习过程。"
      children:
        - title: "前端"
          content: "# 前端\n\n## React\n\n待填写"
        - title: "后端"
          content: "# 后端\n\n## Node.js\n\n待填写"
    - title: "项目记录"
      content: "# 项目记录"
```

2. 预览结构：

```bash
python3 scripts/wiki_init.py structure.yaml --dry-run
```

输出：
```
知识库空间: 我的知识库

=== 预览模式 ===

└── 知识管理中心
    ├── 学习笔记
    │   ├── 前端
    │   └── 后端
    └── 项目记录

共 5 个节点将被创建
```

3. 执行创建：

```bash
python3 scripts/wiki_init.py structure.yaml
```

4. 挂到已有节点下：

```bash
python3 scripts/wiki_init.py structure.yaml --parent-node wikcnXXXXXX
```

## 配置文件格式

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `space` | string | 是 | 知识库空间 ID（数字），通过 `lark-cli wiki spaces list` 查看，或填 `my_library` 表示个人知识库 |
| `root` | object | 是 | 根节点 |
| `root.title` | string | 是 | 节点标题 |
| `root.content` | string | 否 | 文档内容（Markdown 格式），默认为 `# {title}` |
| `root.children` | array | 否 | 子节点列表，递归结构 |

## 命令行参数

| 参数 | 说明 |
|------|------|
| `config` | YAML 配置文件路径 |
| `--dry-run` | 预览模式，不实际创建 |
| `--parent-node TOKEN` | 父节点 token，将整棵树挂到该节点下 |
| `--delay N` | 每次创建间隔秒数，默认 1.0 |

## 踩坑记录

### 1. Shell `\n` 转义问题

在 shell 中直接传递含 `\n` 的字符串给 lark-cli 时，`\n` 不会被解析为换行符，导致文档内容出现字面的 `\n`。

**解决方案**：用 Python `subprocess` 直接传参，Python 字符串中的 `\n` 会被正确处理。

### 2. 知识库节点无法批量删除

飞书知识库目前没有公开的删除 API。一旦创建就只能在飞书客户端手动删除。

**建议**：创建前务必用 `--dry-run` 预览确认结构。

### 3. API 频率限制

飞书 API 有调用频率限制，批量创建时如果太快会被限流。

**解决方案**：脚本默认每次创建间隔 1 秒，可通过 `--delay` 调整。

### 4. 权限配置

需要在飞书开放平台为应用添加 `wiki:node:create` 和 `docx:document:create` 权限，并发布版本。

## 示例配置

- [examples/minimal.yaml](examples/minimal.yaml) — 最小示例
- [examples/ai-builder-os.yaml](examples/ai-builder-os.yaml) — 完整的 AI Native Builder OS 知识库结构

## License

MIT

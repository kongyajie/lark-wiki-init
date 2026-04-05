# lark-cli Wiki 相关命令参考

## 安装与登录

```bash
# 安装
npm install -g lark-cli

# 登录（需要飞书应用凭证）
lark-cli auth login
```

## Wiki 节点操作

### 创建文档并挂载到知识库

```bash
# 在知识库空间下创建根节点
lark-cli docs +create \
  --wiki-space "7620663498296642741" \
  --title "文档标题" \
  --markdown "# 标题\n\n文档内容"

# 在已有节点下创建子节点（--wiki-node 与 --wiki-space 互斥）
lark-cli docs +create \
  --wiki-node "wikcnXXXXXX" \
  --title "子文档标题" \
  --markdown "# 子标题\n\n子文档内容"
```

注意：`--wiki-space` 和 `--wiki-node` 是互斥参数，不能同时使用。根节点用 `--wiki-space`，子节点用 `--wiki-node`。

### 完整参数

```
Flags:
      --as string             identity type: user | bot (default "user")
      --dry-run               print request without executing
      --folder-token string   parent folder token
  -h, --help                  help for +create
  -q, --jq string             jq expression to filter JSON output
      --markdown string       Markdown content (Lark-flavored)
      --title string          document title
      --wiki-node string      wiki node token
      --wiki-space string     wiki space ID (use my_library for personal library)
```

### 返回值

创建成功后返回 JSON，包含：
- `wiki_node_token`: 知识库节点 token，用于挂载子节点
- `document_id`: 文档 ID
- `url`: 文档链接

示例返回：
```json
{
  "wiki_node_token": "wikcnXXXXXXXXXX",
  "document_id": "doxcnXXXXXXXXXX",
  "url": "https://xxx.feishu.cn/wiki/wikcnXXXXXXXXXX"
}
```

### 查看知识库空间列表

```bash
lark-cli wiki spaces
```

### 查看知识库节点

```bash
lark-cli wiki nodes --space "空间ID"
```

## 权限要求

飞书应用需要以下 API 权限：
- `wiki:node:create` — 创建知识库节点
- `docx:document:create` — 创建文档
- `wiki:space:read` — 读取知识库空间信息（可选，用于列出空间）

## 常见问题

### 1. `\n` 转义问题

在 shell 中直接传递含 `\n` 的字符串时，可能不会被正确解析为换行符。

**错误方式**：
```bash
lark-cli docs +create --markdown "# 标题\n\n内容"
# \n 可能被当作字面字符串
```

**正确方式**：使用 Python subprocess 传参，避免 shell 转义：
```python
subprocess.run([
    "lark-cli", "docs", "+create",
    "--markdown", "# 标题\n\n内容"  # Python 字符串中 \n 是真正的换行
], capture_output=True, text=True)
```

### 2. 频率限制

飞书 API 有调用频率限制，批量创建时建议每次间隔 1 秒以上。

### 3. 节点删除

目前飞书知识库没有公开的批量删除 API，只能在飞书客户端手动删除。创建前请务必确认结构。

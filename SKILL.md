---
name: lark-wiki-init
description: |
  批量创建飞书知识库目录结构。当用户想要在飞书知识库（Lark Wiki）中
  批量创建文档目录树、初始化知识库结构、或者说"帮我创建飞书知识库"时触发。
  依赖 lark-cli 已安装并完成 auth login。
---

# lark-wiki-init

批量创建飞书知识库（Lark Wiki）目录结构的 Skill。

## 触发条件

当用户表达以下意图时触发：
- "帮我创建飞书知识库目录结构"
- "批量初始化飞书知识库"
- "在飞书知识库中创建文档树"
- "lark wiki init"

## 工作流程

### Step 1: 获取目录结构

从用户描述中提取目录树结构，或让用户提供 YAML 配置文件。

如果用户没有提供 YAML 配置，引导用户描述目录结构，然后生成 YAML 配置文件。YAML 格式如下：

```yaml
space: "知识库名称"    # 知识库空间名（需已存在）
root:
  title: "根节点标题"
  content: "# 根节点\n\n文档内容（Markdown 格式）"
  children:
    - title: "子节点标题"
      content: "# 子节点\n\n文档内容"
      children:
        - title: "孙节点标题"
          content: "# 孙节点\n\n文档内容"
```

将生成的 YAML 保存为 `structure.yaml`。

### Step 2: 预览确认

先用 `--dry-run` 模式预览将要创建的结构：

```bash
python3 <skill_path>/scripts/wiki_init.py structure.yaml --dry-run
```

让用户确认结构无误后再执行。

### Step 3: 执行创建

```bash
python3 <skill_path>/scripts/wiki_init.py structure.yaml
```

如果要挂到已有节点下，使用 `--parent-node` 参数：

```bash
python3 <skill_path>/scripts/wiki_init.py structure.yaml --parent-node <wiki_node_token>
```

### Step 4: 结果确认

脚本会输出每个节点的创建结果，包括 wiki_node_token。确认所有节点创建成功。

## 前置条件

1. 已安装 lark-cli：`npm install -g lark-cli` 或 `npx lark-cli`
2. 已完成登录：`lark-cli auth login`
3. 飞书应用需要以下权限：
   - `wiki:node:create` — 创建知识库节点
   - `docx:document:create` — 创建文档

## 踩坑经验（重要）

1. **Shell 转义问题**：不要在 shell 中用 `"$(...)"` 嵌套传递含 `\n` 的内容，Python subprocess 直接传参更可靠。
2. **无删除 API**：wiki 节点目前没有公开的批量删除 API，创建前务必用 `--dry-run` 确认结构。
3. **节点 token**：`lark-cli docs +create` 返回的 `wiki_node_token` 用于挂载子节点，脚本会自动处理父子关系。
4. **频率限制**：API 有调用频率限制，脚本默认每次创建间隔 1 秒。
5. **内容格式**：content 字段使用 Markdown 格式，lark-cli 会自动转换。

## 参考

- [lark-cli wiki 命令参考](references/lark-cli-wiki.md)

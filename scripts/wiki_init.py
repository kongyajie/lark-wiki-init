#!/usr/bin/env python3
"""
飞书知识库批量初始化脚本

从 YAML 配置文件读取目录树结构，通过 lark-cli 批量创建飞书知识库节点。

用法:
    python3 wiki_init.py structure.yaml              # 执行创建
    python3 wiki_init.py structure.yaml --dry-run     # 预览模式
    python3 wiki_init.py structure.yaml --parent-node wikcnXXX  # 挂到已有节点下
"""

import argparse
import json
import subprocess
import sys
import time

import yaml


def load_config(path: str) -> dict:
    """加载 YAML 配置文件"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_node(
    space: str,
    title: str,
    content: str,
    parent_node: str | None = None,
) -> dict | None:
    """
    调用 lark-cli 创建一个知识库节点。

    - 根节点使用 --wiki-space 创建
    - 子节点使用 --wiki-node 创建（与 --wiki-space 互斥）

    返回 lark-cli 的 JSON 输出，失败返回 None。
    """
    cmd = [
        "lark-cli",
        "docs",
        "+create",
        "--title",
        title,
        "--markdown",
        content,
    ]
    if parent_node:
        cmd.extend(["--wiki-node", parent_node])
    else:
        cmd.extend(["--wiki-space", space])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        print("错误: 未找到 lark-cli，请先安装: npm install -g lark-cli")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(f"超时: 创建节点 '{title}' 超时")
        return None

    if result.returncode != 0:
        print(f"失败: 创建节点 '{title}'")
        print(f"  stderr: {result.stderr.strip()}")
        return None

    # 尝试解析 JSON 输出
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"警告: 无法解析 lark-cli 输出，原始内容:")
        print(f"  stdout: {result.stdout.strip()}")
        return {"raw_output": result.stdout.strip()}

    # lark-cli 返回 {"ok": true/false, "data": {...}} 格式
    if not output.get("ok"):
        error = output.get("error", {})
        print(f"失败: 创建节点 '{title}'")
        print(f"  错误: {error.get('message', '未知错误')}")
        return None

    data = output.get("data", {})

    # 从 doc_url 中提取 wiki_node_token（URL 最后一段路径）
    doc_url = data.get("doc_url", "")
    if doc_url:
        data["wiki_node_token"] = doc_url.rstrip("/").split("/")[-1]

    return data


def print_tree(node: dict, prefix: str = "", is_last: bool = True) -> int:
    """打印目录树预览，返回节点总数"""
    connector = "└── " if is_last else "├── "
    print(f"{prefix}{connector}{node['title']}")

    count = 1
    children = node.get("children", [])
    for i, child in enumerate(children):
        extension = "    " if is_last else "│   "
        count += print_tree(child, prefix + extension, i == len(children) - 1)
    return count


def create_tree(
    space: str,
    node: dict,
    parent_node: str | None = None,
    depth: int = 0,
    delay: float = 1.0,
) -> list[dict]:
    """
    递归创建目录树。

    返回所有创建结果的列表。
    """
    indent = "  " * depth
    title = node["title"]
    content = node.get("content", f"# {title}")

    print(f"{indent}创建: {title} ...", end=" ", flush=True)

    result = create_node(space, title, content, parent_node)

    if result and "wiki_node_token" in result:
        token = result["wiki_node_token"]
        print(f"✓ ({token})")
    elif result:
        token = None
        print("✓ (未获取到 token)")
    else:
        print("✗")
        return [{"title": title, "success": False}]

    results = [{"title": title, "success": True, "result": result}]

    # 递归创建子节点
    children = node.get("children", [])
    for child in children:
        time.sleep(delay)  # 避免频率限制
        child_results = create_tree(
            space,
            child,
            parent_node=token,
            depth=depth + 1,
            delay=delay,
        )
        results.extend(child_results)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="飞书知识库批量初始化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 wiki_init.py structure.yaml --dry-run
  python3 wiki_init.py structure.yaml
  python3 wiki_init.py structure.yaml --parent-node wikcnXXX --delay 2
        """,
    )
    parser.add_argument("config", help="YAML 配置文件路径")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，只显示将要创建的结构，不实际执行",
    )
    parser.add_argument(
        "--parent-node",
        help="父节点 wiki_node_token，将整棵树挂到该节点下",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="每次创建间隔秒数（默认 1.0）",
    )
    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)
    space = config.get("space", "")
    root = config.get("root")

    if not space:
        print("错误: 配置文件中缺少 space 字段")
        sys.exit(1)
    if not root:
        print("错误: 配置文件中缺少 root 字段")
        sys.exit(1)

    print(f"知识库空间: {space}")
    print()

    if args.dry_run:
        print("=== 预览模式 ===")
        print()
        total = print_tree(root)
        print()
        print(f"共 {total} 个节点将被创建")
        print()
        print("确认无误后，去掉 --dry-run 参数执行创建。")
        return

    # 执行创建
    print("=== 开始创建 ===")
    print()
    results = create_tree(
        space,
        root,
        parent_node=args.parent_node,
        delay=args.delay,
    )

    # 汇总
    print()
    print("=== 创建结果 ===")
    success = sum(1 for r in results if r["success"])
    failed = len(results) - success
    print(f"成功: {success}, 失败: {failed}, 总计: {len(results)}")

    if failed > 0:
        print()
        print("失败的节点:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['title']}")


if __name__ == "__main__":
    main()

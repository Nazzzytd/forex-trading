#!/usr/bin/env python3
"""
UltraRAG CLI 主入口
"""
import argparse
import sys
from pathlib import Path

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="UltraRAG Framework - Forex Trading Agent",
        prog="ultrarag"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # build 命令
    build_parser = subparsers.add_parser("build", help="构建工具")
    build_parser.add_argument("tool_file", help="工具定义文件路径")
    build_parser.add_argument("--force", action="store_true", help="强制重新构建")
    
    # run 命令
    run_parser = subparsers.add_parser("run", help="运行工作流")
    run_parser.add_argument("workflow_file", help="工作流文件路径")
    run_parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    # list 命令
    list_parser = subparsers.add_parser("list", help="列出可用工具")
    
    args = parser.parse_args()
    
    # 延迟导入，避免循环导入问题
    if args.command == "build":
        from .build import BuildCommand
        cmd = BuildCommand()
        cmd.execute(args.tool_file, force=args.force)
    elif args.command == "run":
        from .run import RunCommand
        cmd = RunCommand()
        cmd.execute(args.workflow_file, verbose=args.verbose)
    elif args.command == "list":
        from ..servers import list_available_tools
        tools = list_available_tools()
        if tools:
            print("🛠️  可用工具:")
            for tool_name, tool_info in tools.items():
                status = "✅" if tool_info["definition_exists"] else "❌"
                print(f"  {status} {tool_name}")
                if tool_info["definition_exists"]:
                    print(f"     定义文件: {tool_info['path']}/{tool_name}.yaml")
        else:
            print("❌ 未发现任何工具")
            print("💡 请运行 'ultrarag build servers/<tool_name>/<tool_name>.yaml' 构建工具")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
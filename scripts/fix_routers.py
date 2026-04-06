"""修复路由文件脚本 - 将 ResponseModel 改为直接返回字典"""

import re
import os

# 文件列表
files_to_fix = [
    "events.py",
    "clips.py",
    "reviews.py",
    "training.py",
    "metrics.py"
]

# 修复模式
def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # 1. 移除 response_model=ResponseModel 从路由装饰器
    content = re.sub(
        r'@router\.(get|post|put|delete)\("([^"]+)"(, response_model=ResponseModel)?(\, status_code=[^)]+)?\)',
        r'@router.\1("\2"\4)',
        content
    )

    # 2. 替换 ResponseModel 返回为字典返回
    # 匹配 return ResponseModel(code=..., message=..., data=...)
    content = re.sub(
        r'return ResponseModel\(\s*code=(\w+),\s*message=("[^"]+"|\w+),\s*data=(.+?)\s*\)',
        r'return {"code": \1, "message": \2, "data": \3}',
        content
    )

    # 3. 移除 ResponseModel 导入（如果不再需要）
    content = re.sub(
        r'from app\.schemas\.common import ResponseModel\n?',
        '',
        content
    )

    # 4. 添加 Dict, Any 导入（如果需要）
    if 'from typing import' in content:
        if 'Dict' not in content or 'Any' not in content:
            content = re.sub(
                r'from typing import ([^\n]+)',
                lambda m: f'from typing import {m.group(1)}, Dict, Any' if 'Dict' not in m.group(1) else m.group(0),
                content
            )

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed: {filepath}")
        return True
    else:
        print(f"No changes: {filepath}")
        return False


# 执行修复
router_dir = "D:/vidio_school_system/apps/api/app/routers"
for filename in files_to_fix:
    filepath = os.path.join(router_dir, filename)
    if os.path.exists(filepath):
        fix_file(filepath)
    else:
        print(f"File not found: {filepath}")

print("\nDone!")

#!/usr/bin/env python3
"""验证配置模板文件的 YAML 语法"""

import yaml
import sys

configs = [
    'config/template_mysql_es.yaml',
    'config/template_postgresql_es.yaml',
    'config/template_mysql_to_pg_es.yaml',
]

all_valid = True

for cfg_file in configs:
    try:
        with open(cfg_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 检查必需字段
        has_assets = bool(config.get('assets'))
        has_verify = 'verify' in config

        print(f"✓ {cfg_file}")
        print(f"  - YAML syntax valid")
        print(f"  - Assets configured: {has_assets}")
        print(f"  - Verify enabled: {config.get('verify', {}).get('enabled', True)}")

    except Exception as e:
        print(f"✗ {cfg_file}")
        print(f"  - Error: {e}")
        all_valid = False

if all_valid:
    print("\n✓ All configuration templates are valid!")
    sys.exit(0)
else:
    print("\n✗ Some configuration templates have errors")
    sys.exit(1)
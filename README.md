# AIXDR Data Exporter

AIXDR 资产数据导出导入工具。支持在 MySQL、PostgreSQL、Elasticsearch 之间迁移资产数据，含 MySQL→PostgreSQL 跨库 SQL 语法自动转换。

**当前版本：v1.2.0**

## 功能特性

- **三数据源**：MySQL、PostgreSQL、Elasticsearch
- **跨库迁移**：MySQL → PostgreSQL（自动 SQL 语法转换）
- **一键迁移**：`export-import` 串联导出 + 导入 + 验证
- **智能删除**：导入时按 asset_id 清理旧数据，不影响其他资产
- **级联导出**：自动追踪 asset_id → device_id 关联，导出全部关联表
- **ES 按月分片**：告警/事件索引支持 `maxs_alarm_{YYYYMM}` 模式
- **多格式支持**：SQL / CSV / JSON Lines / NDJSON
- **配置模板**：3 套标准模板覆盖全部迁移场景

## 数据模型与关联逻辑

### MySQL / PostgreSQL 表关系

5 张表通过 `asset_id` 和 `device_id` 级联关联（MySQL 表名大写，PostgreSQL 表名小写）：

```
XDR_ASSET (asset_id, device_id)
  │
  ├── asset_id ──→ XDR_ASSET_IP       (资产 IP)
  ├── asset_id ──→ XDR_ASSET_VULN     (资产漏洞)
  ├── asset_id ──→ XDR_RISK_PORT      (风险端口)
  └── device_id ─→ XDR_WEAK_PASSWORD  (弱密码)
```

| 表名 (MySQL / PostgreSQL) | 关联字段 | 关联目标 | 过滤条件 |
|---------------------------|---------|---------|---------|
| XDR_ASSET / xdr_asset | asset_id | — | `asset_id IN (...)` |
| XDR_ASSET_IP / xdr_asset_ip | asset_id | XDR_ASSET | `asset_id IN (...)` |
| XDR_ASSET_VULN / xdr_asset_vuln | asset_id | XDR_ASSET | `asset_id IN (...)` |
| XDR_RISK_PORT / xdr_risk_port | asset_id | XDR_ASSET | `asset_id IN (...)` |
| XDR_WEAK_PASSWORD / xdr_weak_password | device_id | XDR_ASSET.device_id | `device_id IN (...)` |

> **关键**：`XDR_WEAK_PASSWORD` 不通过 `asset_id` 关联，而是通过 `XDR_ASSET.device_id` 间接关联。导出时先从 `XDR_ASSET` 收集 `device_id`，再导出对应的弱密码记录。

### Elasticsearch 索引关系

5 类索引，按 `ASSET_ID` 查询，告警/事件使用 nested 查询：

| 索引 | 查询方式 | 查询字段 | 说明 |
|------|---------|---------|------|
| xdr_asset | term | ASSET_ID | 资产主数据 |
| xdr_asset_fingerprint | term | ASSET_ID | 资产指纹 |
| xdr_asset_his | term | ASSET_ID | 资产历史 |
| maxs_alarm_{YYYYMM} | nested | AFFECTED_ASSET_INFO.ASSET_ID | 告警（按月分片） |
| maxs_event_{YYYYMM} | nested | AFFECTED_ASSET_INFO.ASSET_ID | 事件（按月分片） |

### 导出顺序

按依赖关系顺序导出，先主表后关联表：

1. `XDR_ASSET`（同时收集 `device_id`）
2. `XDR_ASSET_IP`
3. `XDR_ASSET_VULN`
4. `XDR_RISK_PORT`
5. `XDR_WEAK_PASSWORD`（使用步骤 1 收集的 `device_id`）

### 智能删除顺序

导入时按依赖逆序删除，先删被依赖方再删主表，避免外键约束冲突：

1. `XDR_WEAK_PASSWORD`（按 `device_id`）
2. `XDR_RISK_PORT`（按 `asset_id`）
3. `XDR_ASSET_VULN`（按 `asset_id`）
4. `XDR_ASSET_IP`（按 `asset_id`）
5. `XDR_ASSET`（按 `asset_id`）

> PostgreSQL 导入兼容首次导入场景：当目标库 `xdr_asset` 尚无数据时，从待导入的 SQL 文件中解析 `device_id` 作为兜底，确保 `xdr_weak_password` 也能正确清理。

## 使用手册

### 安装

```bash
# 方式一：从源码运行（开发推荐）
pip install -r requirements.txt
python cli.py --help

# 方式二：从 wheel 包安装（分发推荐）
pip install dist/aixdr_data_exporter-1.2.0-py3-none-any.whl
aixdr-exporter --help
```

> 如 `aixdr-exporter` 命令找不到，将 pip 用户目录加入 PATH：
> `export PATH=$PATH:$(python3 -c "import site; print(site.USER_BASE)")/bin`

### 配置模板

项目提供 3 套标准模板，复制后修改必填项即可：

| 模板文件 | 迁移场景 |
|---------|---------|
| `config/template_mysql_es.yaml` | MySQL + ES → MySQL + ES |
| `config/template_postgresql_es.yaml` | PostgreSQL + ES → PostgreSQL + ES |
| `config/template_mysql_to_pg_es.yaml` | MySQL → PostgreSQL + ES（跨库） |

```bash
cp config/template_mysql_es.yaml config/my_config.yaml
# 编辑 my_config.yaml，修改标记为【必填】的字段
```

### 配置项说明

```yaml
# ── 数据库（按场景选用，不要混用）──
source:        # MySQL 源库【必填·MySQL 场景】
target:        # MySQL 目标库【必填·MySQL 场景】
pg_source:     # PostgreSQL 源库【必填·PG 场景】
pg_target:     # PostgreSQL 目标库【必填·PG 或跨库场景】

# 以上各库均含字段：host / port / user / password / database

# ── Elasticsearch ──
es_source:     # ES 源集群【必填】host / port / user / password / use_ssl
es_target:     # ES 目标集群【必填】

# ── 资产与索引 ──
assets:                       # 资产 ID 列表【必填】
  - 2019410738962841604
es_indices:
  index_cycles: [202605, 202604, 202603]  # 告警/事件月份【必填】

# ── 输出路径（可选）──
export.output:          ./exports/assets_export.sql
es_export.output_dir:   ./exports/es_latest/

# ── 验证（可选）──
verify.enabled: true    # 导入后验证，默认开启
```

### 命令参考

| 命令 | 用途 | 示例 |
|------|------|------|
| `export` | 仅导出 | `aixdr-exporter export --config cfg.yaml` |
| `import` | 仅导入 | `aixdr-exporter import --config cfg.yaml` |
| `export-import` | 一键导出+导入+验证 | `aixdr-exporter export-import --config cfg.yaml` |
| `config init` | 生成配置模板 | `aixdr-exporter config init -o cfg.yaml` |

**常用参数：**

- `--source mysql|postgresql|es`：指定数据源（不指定则自动检测）
- `--target mysql|postgresql|es`：指定目标（不指定则自动检测）
- `--drop-tables`：导入前删除整表（慎用，默认智能删除）

### 迁移场景

```bash
# 1. MySQL + ES → MySQL + ES（自动检测源/目标）
aixdr-exporter export-import --config my_config.yaml

# 2. MySQL → PostgreSQL（自动语法转换）
aixdr-exporter export-import --config my_config.yaml --source mysql --target postgresql

# 3. PostgreSQL → PostgreSQL
aixdr-exporter export-import --config my_config.yaml --source postgresql --target postgresql

# 4. 仅迁移 ES 数据
aixdr-exporter export-import --config my_config.yaml --source es --target es

# 5. 分步执行（先导出后导入）
aixdr-exporter export --config my_config.yaml
aixdr-exporter import --config my_config.yaml

# 6. 仅操作单一数据源
aixdr-exporter export --config my_config.yaml --source mysql
aixdr-exporter import --config my_config.yaml --target postgresql
```

## MySQL → PostgreSQL 语法转换

跨库迁移时自动转换 SQL 语法（`exporter/sql_converter.py`）：

| 转换项 | MySQL | PostgreSQL |
|--------|-------|-----------|
| 标识符引用 | `` `table_name` `` | `"table_name"`（转小写） |
| TINYINT | TINYINT | SMALLINT |
| MEDIUMINT | MEDIUMINT | INTEGER |
| FLOAT | FLOAT | REAL |
| DOUBLE | DOUBLE | DOUBLE PRECISION |
| DATETIME | DATETIME | TIMESTAMP |
| BLOB 系列 | BLOB / MEDIUMBLOB / LONGBLOB | BYTEA |
| 无符号 | UNSIGNED | 移除 |
| 表选项 | ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 | 移除 |
| 索引长度 | `INDEX idx (col(191))` | `INDEX idx (col)` |
| AUTO_INCREMENT | AUTO_INCREMENT | 移除（依赖序列） |
| DROP TABLE | DROP TABLE | DROP TABLE IF EXISTS |
| CREATE INDEX | CREATE INDEX | CREATE INDEX IF NOT EXISTS |
| 布尔值 | `'true'` / `'false'` | TRUE / FALSE |
| 字符串内转义引号 | `\"` | `"` |

## 项目结构

```
AIXDR_data_exporter_pgsql/
├── cli.py                          # CLI 入口
├── run.py                          # 快捷运行脚本
├── setup.py / pyproject.toml       # 打包配置
├── requirements.txt                # 依赖清单
├── config/                         # 配置模板
│   ├── template_mysql_es.yaml
│   ├── template_postgresql_es.yaml
│   └── template_mysql_to_pg_es.yaml
├── exporter/
│   ├── core/                       # 核心层
│   │   ├── config_manager.py       # 配置管理
│   │   ├── operation.py            # 操作抽象
│   │   └── workflow.py             # 工作流编排
│   ├── handlers/                   # 处理器层
│   │   ├── mysql_handler.py
│   │   ├── postgresql_handler.py
│   │   └── elasticsearch_handler.py
│   ├── mysql_exporter.py           # MySQL 导出
│   ├── mysql_importer.py           # MySQL 导入
│   ├── postgresql_exporter.py      # PostgreSQL 导出
│   ├── postgresql_importer.py      # PostgreSQL 导入
│   ├── sql_converter.py            # MySQL→PG 语法转换
│   ├── related_tables_exporter.py  # 关联表级联导出
│   ├── elasticsearch_exporter.py   # ES 导出导入
│   └── data_validator.py           # 数据验证
└── exports/                        # 导出数据目录（gitignored）
```

## 开发与打包

```bash
# 本地开发运行
pip install -r requirements.txt
python cli.py --help

# 重新打包
rm -rf build/ dist/ *.egg-info/
python setup.py sdist bdist_wheel
# 产物位于 dist/
```

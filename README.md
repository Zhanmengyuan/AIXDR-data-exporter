# AIXDR Data Exporter

AIXDR 资产数据导出导入工具。支持将资产及其关联数据从 MySQL 数据库和 Elasticsearch 集群导出，并导入到 MySQL 或 PostgreSQL 目标环境。

## 最新版本

**v1.2.0** - 新增 PostgreSQL 完整支持

## 功能特性

- **MySQL 数据导出/导入**：资产主表、资产 IP、资产漏洞、风险端口、弱密码
- **PostgreSQL 数据导出/导入**：支持从 PostgreSQL 数据库导出数据并导入到 PostgreSQL 目标环境
- **MySQL → PostgreSQL 数据迁移**：支持从 MySQL 导出的数据转换并导入到 PostgreSQL
- **Elasticsearch 数据导出/导入**：资产索引、资产指纹、资产历史、告警、事件
- **一键导出+导入**：支持从源到目标的全自动数据迁移
- **智能删除**：导入时仅删除指定资产的相关数据，不影响其他数据
- **多资产支持**：一次配置多个资产 ID，批量操作
- **SQL 语法转换**：自动将 MySQL 语法转换为 PostgreSQL 兼容语法
- **数据验证**：导入后自动验证数据完整性

## 快速开始 - 真实操作指南

### 第一步：准备安装包

项目已构建好，安装包位于 `dist/` 目录：

```
dist/
├── aixdr_data_exporter-1.2.0-py3-none-any.whl  # Wheel 安装包（推荐）
└── aixdr_data_exporter-1.2.0.tar.gz            # 源码包
```

### 第二步：安装工具

```bash
# 进入项目目录
cd /path/to/AIXDR_data_exporter_pgsql

# 1. 安装 wheel 包（推荐）
pip install dist/aixdr_data_exporter-1.2.0-py3-none-any.whl

# 2. 验证安装成功
aixdr-exporter --help
```

> **常见问题**：如果 `aixdr-exporter` 命令找不到，需要将 pip 安装目录添加到 PATH：
>
> ```bash
> # Linux/Mac 临时添加
> export PATH=$PATH:$(python3 -c "import site; print(site.USER_BASE)")/bin
> 
> # Linux/Mac 永久添加（写入 ~/.bashrc 或 ~/.zshrc）
> echo 'export PATH=$PATH:$(python3 -c "import site; print(site.USER_BASE)")/bin' >> ~/.zshrc
> source ~/.zshrc
> ```

### 第三步：选择配置模板（推荐）

**使用标准配置模板，只需修改参数值即可：**

```bash
# 查看可用的配置模板
ls config/template_*.yaml

# 输出：
# template_mysql_es.yaml           # MySQL + ES 迁移
# template_postgresql_es.yaml      # PostgreSQL + ES 迁移
# template_mysql_to_pg_es.yaml     # MySQL → PostgreSQL 跨库迁移
```

**选择合适的模板：**
```bash
# MySQL + ES 迁移
cp config/template_mysql_es.yaml config/my_migration.yaml

# PostgreSQL + ES 迁移
cp config/template_postgresql_es.yaml config/my_migration.yaml

# MySQL → PostgreSQL 跨库迁移
cp config/template_mysql_to_pg_es.yaml config/my_migration.yaml
```

**修改必填参数：**
打开配置文件，修改标记为 **【必填】** 的字段：
- ✅ 数据库地址、端口、用户名、密码
- ✅ Elasticsearch 地址、端口、用户名、密码
- ✅ 资产 ID 列表
- ✅ ES 索引月份

**详细使用指南：**
```bash
# 查看配置模板详细说明
cat config/README.md
cat config/CONFIG_TEMPLATE_GUIDE.md
```

### 第四步：了解配置文件结构（可选）

**配置模板包含以下关键部分：**

#### MySQL + ES 迁移配置结构
```yaml
source:      # MySQL 源数据库【必填】
target:      # MySQL 目标数据库【必填】
es_source:   # ES 源集群【必填】
es_target:   # ES 目标集群【必填】
assets:      # 资产 ID 列表【必填】
index_cycles: # ES 索引月份【必填】
```

#### PostgreSQL + ES 迁移配置结构
```yaml
pg_source:   # PostgreSQL 源数据库【必填】
pg_target:   # PostgreSQL 目标数据库【必填】
es_source:   # ES 源集群【必填】
es_target:   # ES 目标集群【必填】
assets:      # 资产 ID 列表【必填】
index_cycles: # ES 索引月份【必填】
```

#### MySQL → PostgreSQL 跨库迁移配置结构
```yaml
source:      # MySQL 源数据库【必填】
pg_target:   # PostgreSQL 目标数据库【必填】
es_source:   # ES 源集群【必填】
es_target:   # ES 目标集群【必填】
assets:      # 资产 ID 列表【必填】
index_cycles: # ES 索引月份【必填】

```

**注意：以上仅展示配置结构，实际使用请直接复制标准模板文件。**

详细配置说明请查看：[config/CONFIG_TEMPLATE_GUIDE.md](config/CONFIG_TEMPLATE_GUIDE.md)
### 第五步：执行操作

#### 操作 1：一键导出+导入（推荐）

```bash
# MySQL → MySQL
aixdr-exporter export-import --config my_config.yaml

# MySQL → PostgreSQL
aixdr-exporter export-import --config my_config.yaml --source mysql --target postgresql

# PostgreSQL → PostgreSQL
aixdr-exporter export-import --config my_config.yaml --source postgresql --target postgresql

# ES → ES
aixdr-exporter export-import --config my_config.yaml --source es --target es

# MySQL+ES → MySQL+ES（自动检测）
aixdr-exporter export-import --config my_config.yaml
```

#### 操作 2：分步执行

```bash
# 第一步：仅导出
aixdr-exporter export --config my_config.yaml

# 第二步：仅导入
aixdr-exporter import --config my_config.yaml
```

#### 操作 3：指定数据源/目标

```bash
# 仅导出 MySQL
aixdr-exporter export --config my_config.yaml --source mysql

# 仅导出 PostgreSQL
aixdr-exporter export --config my_config.yaml --source postgresql

# 仅导出 ES
aixdr-exporter export --config my_config.yaml --source es

# 仅导入到 MySQL
aixdr-exporter import --config my_config.yaml --target mysql

# 仅导入到 PostgreSQL
aixdr-exporter import --config my_config.yaml --target postgresql

# 仅导入到 ES
aixdr-exporter import --config my_config.yaml --target es

# 导入前删除旧表（慎用，会清空表）
aixdr-exporter import --config my_config.yaml --drop-tables
```

### 第六步：验证结果

导入完成后，工具会自动验证数据完整性。你也可以手动验证：

```bash
# 查看导出文件
ls -lh exports/

# MySQL 验证（连接目标库）
mysql -h target_host -u root -p -D target_db -e "SELECT COUNT(*) FROM XDR_ASSET;"

# PostgreSQL 验证
psql -h target_host -p 5432 -U root -d target_db -c "SELECT COUNT(*) FROM xdr_asset;"

# ES 验证
curl -u elastic:password https://target_host:9200/xdr_asset/_count
```

## PostgreSQL 导入功能详解

### 核心文件说明

项目包含以下 PostgreSQL 相关文件：

| 文件路径 | 功能说明 |
|---------|---------|
| `exporter/postgresql_importer.py` | PostgreSQL 数据导入核心模块，处理 SQL 导入、数据转换、智能删除 |
| `exporter/handlers/postgresql_handler.py` | PostgreSQL 数据处理器，提供统一的导入、验证接口 |
| `exporter/sql_converter.py` | MySQL 到 PostgreSQL 的 SQL 语法转换器 |
| `config/example_postgresql_config.yaml` | PostgreSQL 配置示例文件 |

### PostgreSQLImporter 核心功能

`exporter/postgresql_importer.py` 提供以下核心功能：

1. **数据库连接管理**：自动连接 PostgreSQL，支持数据库自动创建
2. **SQL 语句解析**：智能分割 SQL 语句，正确处理字符串中的分号
3. **智能删除**：按资产 ID 删除目标表中的旧数据，按正确顺序执行删除操作
4. **数据导入**：仅导入 INSERT 语句，跳过 DDL 操作，避免破坏目标表结构
5. **表名映射**：自动处理表名大小写问题，支持 public schema
6. **批量提交**：每 1000 条记录自动提交，提升导入效率
7. **CSV/JSON 导入**：支持从 CSV 和 JSON Lines 格式导入数据

### MySQLToPostgreSQLConverter 转换功能

`exporter/sql_converter.py` 提供以下语法转换：

| 转换项 | MySQL 语法 | PostgreSQL 语法 |
|-------|-----------|----------------|
| 标识符引用 | `` `table_name` `` | `"table_name"` |
| 数据类型 | `TINYINT`, `MEDIUMINT`, `BLOB` | `SMALLINT`, `INTEGER`, `BYTEA` |
| 表选项 | `ENGINE=InnoDB`, `DEFAULT CHARSET=utf8` | 自动移除 |
| 自增列 | `AUTO_INCREMENT` | `SERIAL`/`BIGSERIAL` |
| 布尔值 | `'true'`, `'false'` | `TRUE`, `FALSE` |
| 索引长度 | `INDEX idx (col(191))` | `INDEX idx (col)` |

## 项目结构

```
AIXDR_data_exporter_pgsql/
├── cli.py                          # 命令行入口
├── run.py                          # 快捷运行脚本
├── setup.py                        # 打包配置
├── pyproject.toml                  # 现代构建配置
├── MANIFEST.in                     # 源码包清单
├── requirements.txt                # 依赖清单
├── README.md                       # 项目文档
├── QUICK_COMMAND_REFERENCE.md      # 命令速查手册
├── dist/                           # 构建产物（可分发的安装包）
│   ├── aixdr_data_exporter-1.2.0-py3-none-any.whl
│   └── aixdr_data_exporter-1.2.0.tar.gz
├── config/
│   ├── example_postgresql_config.yaml  # PostgreSQL 配置示例
│   └── production_config.yaml          # 生产环境配置
├── exporter/
│   ├── __init__.py                     # 包导出入口
│   ├── postgresql_importer.py          # [新增] PostgreSQL 数据导入
│   ├── sql_converter.py                # [新增] MySQL 到 PostgreSQL 语法转换
│   ├── core/                           # 核心层
│   │   ├── config_manager.py           # 配置管理器
│   │   ├── operation.py                # 操作抽象
│   │   └── workflow.py                 # 工作流编排
│   ├── handlers/                       # 处理器层
│   │   ├── base_handler.py             # 基础接口
│   │   ├── mysql_handler.py            # MySQL 处理器
│   │   ├── postgresql_handler.py       # [新增] PostgreSQL 处理器
│   │   └── elasticsearch_handler.py    # ES 处理器
│   ├── mysql_exporter.py               # MySQL 数据导出
│   ├── mysql_importer.py               # MySQL 数据导入
│   ├── related_tables_exporter.py      # 关联表导出
│   ├── data_validator.py               # 数据验证
│   └── elasticsearch_exporter.py       # ES 数据导出导入
└── exports/                           # 导出数据目录（gitignored）
    ├── es_latest/
    │   ├── es_alarms.ndjson
    │   ├── es_asset.ndjson
    │   ├── es_asset_his.ndjson
    │   ├── es_events.ndjson
    │   └── es_fingerprint.ndjson
    └── assets_export.sql
```

## 导出内容

### MySQL 数据库

| 表名 | 过滤条件 | 说明 |
|-----|---------|-----|
| `XDR_ASSET` | `asset_id IN (...)` | 资产主表 |
| `XDR_ASSET_IP` | `asset_id IN (...)` | 资产 IP |
| `XDR_ASSET_VULN` | `asset_id IN (...)` | 资产漏洞 |
| `XDR_RISK_PORT` | `asset_id IN (...)` | 风险端口 |
| `XDR_WEAK_PASSWORD` | `device_id IN (...)` | 弱密码（通过 device_id 关联） |

### Elasticsearch 索引

| 索引 | 查询方式 | 说明 |
|-----|---------|-----|
| `xdr_asset` | `term: ASSET_ID` | 资产主数据 |
| `xdr_asset_fingerprint` | `term: ASSET_ID` | 资产指纹 |
| `xdr_asset_his` | `term: ASSET_ID` | 资产历史数据 |
| `maxs_alarm_{yyyymm}` | `nested: AFFECTED_ASSET_INFO.ASSET_ID` | 告警（按月分片） |
| `maxs_event_{yyyymm}` | `nested: AFFECTED_ASSET_INFO.ASSET_ID` | 事件（按月分片） |

## 开发和打包

### 本地开发运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 直接运行（源码目录内）
python3 cli.py --help
```

### 重新打包

如果你需要修改代码并重新打包：

```bash
# 1. 清理旧构建
rm -rf build/ dist/ *.egg-info/

# 2. 构建新包
python3 setup.py sdist bdist_wheel

# 3. 新包位于 dist/ 目录
ls -lh dist/
```

## 更多命令参考

详见 [QUICK_COMMAND_REFERENCE.md](QUICK_COMMAND_REFERENCE.md)，包含完整的命令速查表、配置示例和常见问题解答。

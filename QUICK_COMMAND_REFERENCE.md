# AIXDR 数据导出导入 - 快速命令参考

> **版本说明**：v1.1.0 重构后，所有功能统一为 3 个主命令：`export`、`import`、`export-import`  
> **导出范围**：仅支持**资产导出**，导出指定资产的所有相关数据
> **新增支持**：PostgreSQL 目标数据库导入

---

# 快速开始

### 1. 把 .whl 复制过去（29k）

### 2. 安装
```bash
pip install aixdr_data_exporter-1.1.0-py3-none-any.whl
```

### 3. 生成配置模板
```bash
aixdr-exporter config init --output config.yaml
```

### 4. 编辑配置
```bash
vim config.yaml    # 改一下 host、password、assets
```

### 5. 执行
```bash
aixdr-exporter export --config config.yaml
```

---

## 📋 命令对照表

| 目的 | 命令 | 说明 |
|------|------|------|
| **一键导出+导入** | `export-import --config FILE` | 资产导出+导入+验证 |
| **导出资产** | `export --config FILE` | 按资产ID导出 |
| **导入数据** | `import --config FILE` | 导入数据（MySQL/PostgreSQL/ES） |
| **导入到 PostgreSQL** | `import --config FILE --target postgresql` | 仅导入到 PostgreSQL |
| **获取帮助** | `export --help` | 查看某命令的参数 |

---

## 🔧 完整参数说明

### export - 导出资产数据

```bash
python3 cli.py export --config FILE [--source TYPE] [--output PATH]
```

| 参数 | 必需 | 选项 | 说明 |
|------|------|------|------|
| `--config` | ✓ | - | 配置文件路径 |
| `--source` | | mysql \| es | 数据源（可选，不指定则自动导出所有配置的数据源） |
| `--output` | | PATH | 输出文件路径（覆盖config） |

**导出行为**：
- **不指定 `--source`**：自动检测 config，同时导出配置的所有数据源
  - 有 MySQL (`source`) 就导出 MySQL
  - 有 Elasticsearch (`es_source`) 就导出 ES
  - 两个都有就同时导出两个
- **指定 `--source mysql`**：仅导出 MySQL 数据
- **指定 `--source es`**：仅导出 Elasticsearch 数据

**导出内容说明**：
- 导出 `config.yaml` 中 `assets` 字段指定的所有资产
- MySQL 导出包含：XDR_ASSET、XDR_ASSET_IP、XDR_ASSET_VULN、XDR_RISK_PORT
- Elasticsearch 导出包含：xdr_asset、xdr_asset_fingerprint、xdr_asset_his、maxs_alarm_*、maxs_event_*

**示例：**
```bash
# 同时导出 MySQL 和 Elasticsearch 数据（如果两个都配置了）
python3 cli.py export --config config.yaml

# 仅导出 MySQL 数据
python3 cli.py export --config config.yaml --source mysql

# 仅导出 Elasticsearch 数据
python3 cli.py export --config config.yaml --source es

# 覆盖输出路径
python3 cli.py export --config config.yaml --output /tmp/export.sql
```

---

### import - 导入数据

```bash
python3 cli.py import --config FILE [--input PATH] [--target TYPE] [--drop-tables]
```

| 参数 | 必需 | 选项 | 说明 |
|------|------|------|------|
| `--config` | ✓ | - | 配置文件路径 |
| `--input` | | PATH | 输入文件/目录路径（覆盖config） |
| `--target` | | mysql \| postgresql \| es | 目标类型（可选，不指定则自动导入所有配置的目标） |
| `--drop-tables` | | FLAG | 导入前删除表（MySQL/PostgreSQL） |

**导入行为**：
- **不指定 `--target`**：自动检测 config，同时导入到配置的所有目标
  - 有 MySQL (`target`) 就导入 MySQL
  - 有 PostgreSQL (`pg_target`) 就导入 PostgreSQL
  - 有 Elasticsearch (`es_target`) 就导入 ES
  - 多个配置就同时导入到多个
- **指定 `--target mysql`**：仅导入 MySQL 数据
- **指定 `--target postgresql`**：仅导入 PostgreSQL 数据
- **指定 `--target es`**：仅导入 Elasticsearch 数据

**示例：**
```bash
# 同时导入 MySQL、PostgreSQL 和 Elasticsearch 数据（如果都配置了）
python3 cli.py import --config config.yaml

# 仅导入 MySQL，导入前删除旧表
python3 cli.py import --config config.yaml --target mysql --drop-tables

# 仅导入 PostgreSQL
python3 cli.py import --config config.yaml --target postgresql

# 仅导入 Elasticsearch
python3 cli.py import --config config.yaml --target es

# 指定输入文件
python3 cli.py import --config config.yaml --input /tmp/export.sql

# 同时导入，并指定输入文件
python3 cli.py import --config config.yaml --input /tmp/export.sql
```

---

### export-import - 一键导出+导入+验证

```bash
python3 cli.py export-import --config FILE [--source TYPE] [--target TYPE]
```

| 参数 | 必需 | 选项 | 说明 |
|------|------|------|------|
| `--config` | ✓ | - | 配置文件路径 |
| `--source` | | mysql \| es | 源类型（可选，自动检测） |
| `--target` | | mysql \| postgresql \| es | 目标类型（可选，自动检测） |

**示例：**
```bash
# MySQL → MySQL 资产导出+导入
python3 cli.py export-import --config config.yaml

# MySQL → PostgreSQL 资产导出+导入
python3 cli.py export-import --config config.yaml --source mysql --target postgresql

# MySQL → Elasticsearch
python3 cli.py export-import --config config.yaml --source mysql --target es

# Elasticsearch → Elasticsearch
python3 cli.py export-import --config config.yaml --source es --target es
```

---

### config init - 生成配置模板

```bash
aixdr-exporter config init [--output FILE]
```

| 参数 | 必需 | 说明 |
|------|------|------|
| `--output` / `-o` | | 输出文件路径（不指定则打印到终端） |

**示例：**
```bash
# 打印到终端
aixdr-exporter config init

# 写入文件
aixdr-exporter config init --output my_config.yaml

# 重定向到文件
aixdr-exporter config init > my_config.yaml
```

---

## 📝 配置文件示例

### MySQL 配置

```yaml
source:
  host: 10.21.19.99
  port: 3306
  user: root
  password: your_password
  database: SSA

target:
  host: 192.168.115.68
  port: 3306
  user: root
  password: your_password
  database: SSA

assets:
  - 2019410738962841604
  - 2018021633618649093

export:
  output: ./exports/assets_export_{timestamp}.sql

import:
  input: ./exports/assets_export_{timestamp}.sql

verify:
  enabled: true
```

### PostgreSQL 配置

```yaml
# MySQL 源数据库（从中导出）
source:
  host: 10.21.19.99
  port: 3306
  user: root
  password: maxs.PDG~2022
  database: SSA

# PostgreSQL 目标数据库（导入到）
pg_target:
  host: 192.168.113.169
  port: 15432
  user: root
  password: maxs.PDG~2022
  database: ssa

# 要导出的资产 ID
assets:
  - 2015077142737756174

# 导出输出文件（MySQL 格式的 SQL）
export:
  output: ./exports/assets_export.sql

# 导入输入文件（将自动转换为 PostgreSQL 格式）
import:
  input: ./exports/assets_export.sql

# 导入后启用验证
verify:
  enabled: true
```

### Elasticsearch 配置

```yaml
es_source:
  host: 10.21.19.99
  port: 9200
  user: elastic
  password: your_password
  use_ssl: true

es_target:
  host: 192.168.115.68
  port: 9200
  user: elastic
  password: your_password
  use_ssl: true

assets:
  - 2019410738962841604

es_indices:
  asset: xdr_asset
  fingerprint: xdr_asset_fingerprint
  asset_his: xdr_asset_his
  alarm_pattern: maxs_alarm_
  event_pattern: maxs_event_
  index_cycles: [202605, 202604, 202603, 202602, 202601]

es_export:
  output_dir: ./exports/es_{timestamp}/
  size_per_batch: 1000

verify:
  enabled: true
```

### 混合配置（同时导出 MySQL + ES，导入到 MySQL + PostgreSQL + ES）

```yaml
# MySQL 源
source:
  host: 10.21.19.99
  port: 3306
  user: root
  password: your_password
  database: SSA

# ES 源
es_source:
  host: 10.21.19.99
  port: 9200
  user: elastic
  password: your_password
  use_ssl: true

# MySQL 目标
target:
  host: 192.168.115.68
  port: 3306
  user: root
  password: your_password
  database: SSA

# PostgreSQL 目标
pg_target:
  host: 192.168.113.169
  port: 15432
  user: root
  password: your_password
  database: ssa

# ES 目标
es_target:
  host: 192.168.115.68
  port: 9200
  user: elastic
  password: your_password
  use_ssl: true

assets:
  - 2019410738962841604

es_indices:
  asset: xdr_asset
  fingerprint: xdr_asset_fingerprint
  asset_his: xdr_asset_his
  alarm_pattern: maxs_alarm_
  event_pattern: maxs_event_
  index_cycles: [202605, 202604]

export:
  output: ./exports/assets_export_{timestamp}.sql

es_export:
  output_dir: ./exports/es_{timestamp}/
  size_per_batch: 1000

import:
  input: ./exports/assets_export_{timestamp}.sql

verify:
  enabled: true
```

---

## 📊 导出内容说明

### MySQL 导出的表

| 表名 | 说明 |
|------|------|
| `XDR_ASSET` | 资产主表（主键） |
| `XDR_ASSET_IP` | 资产 IP 地址 |
| `XDR_ASSET_VULN` | 资产漏洞信息 |
| `XDR_RISK_PORT` | 风险端口 |
| `XDR_WEAK_PASSWORD` | 弱密码（通过 device_id 关联） |

**注**：仅导出配置中 `assets` 字段指定的资产及其相关数据。

### Elasticsearch 导出的索引

| 索引 | 说明 |
|------|------|
| `xdr_asset` | 资产主数据 |
| `xdr_asset_fingerprint` | 资产指纹 |
| `xdr_asset_his` | 资产历史数据 |
| `maxs_alarm_*` | 告警数据（按月份） |
| `maxs_event_*` | 事件数据（按月份） |

---

## ⚙️ 配置项说明

### source / target（MySQL）

```yaml
source:
  host: 数据库主机地址
  port: 端口号（默认：3306）
  user: 用户名
  password: 密码
  database: 数据库名
```

### pg_target（PostgreSQL）

```yaml
pg_target:
  host: PostgreSQL 主机地址
  port: 端口号（默认：5432）
  user: 用户名
  password: 密码
  database: 数据库名
```

### es_source / es_target（Elasticsearch）

```yaml
es_source:
  host: ES 主机地址
  port: 端口号（默认：9200）
  user: 用户名
  password: 密码
  use_ssl: 是否使用 SSL（默认：true）
```

### assets（资产列表）

```yaml
assets:
  - 2019410738962841604  # 资产 ID
  - 2018021633618649093
  # 仅会导出这些资产的数据
```

### es_indices（ES 索引配置）

```yaml
es_indices:
  asset: xdr_asset                    # 资产主索引名
  fingerprint: xdr_asset_fingerprint  # 资产指纹索引名
  asset_his: xdr_asset_his            # 资产历史索引名
  alarm_pattern: maxs_alarm_          # 告警索引前缀
  event_pattern: maxs_event_          # 事件索引前缀
  index_cycles: [202605, 202604]      # 要导出的月份周期
```

### export（导出配置）

```yaml
export:
  output: ./exports/assets_export_{timestamp}.sql
  # {timestamp} 会自动替换为当前时间（格式：YYYYMMDD_HHMMSS）
```

### es_export（ES 导出配置）

```yaml
es_export:
  output_dir: ./exports/es_{timestamp}/  # 输出目录
  size_per_batch: 1000                  # 每批导出的文档数
```

### verify（验证配置）

```yaml
verify:
  enabled: true  # 导入后自动验证
```

---

## 🎯 常见场景

### 场景 1：同时导出 MySQL 和 Elasticsearch 数据

配置文件同时有 `source` 和 `es_source` 时：

```bash
# 自动导出两个数据源
python3 cli.py export --config config.yaml

# 输出：
# Exporting from: MYSQL, ES
# [MYSQL] Export completed
# [Elasticsearch] Export completed
# All exports completed successfully!
```

### 场景 2：仅导出某个数据源

```bash
# 仅导出 MySQL
python3 cli.py export --config config.yaml --source mysql

# 仅导出 Elasticsearch
python3 cli.py export --config config.yaml --source es
```

### 场景 3：导出并导入资产到另一个 MySQL 库

```bash
# 推荐：一键完成（同时导出 MySQL 和 ES）
python3 cli.py export-import --config config.yaml

# 或分步骤
python3 cli.py export --config config.yaml
python3 cli.py import --config config.yaml
```

### 场景 4：从 MySQL 导出到 PostgreSQL（新增）

```bash
# 一键：MySQL → PostgreSQL
python3 cli.py export-import --config config.yaml --source mysql --target postgresql

# 或分步骤
python3 cli.py export --config config.yaml
python3 cli.py import --config config.yaml --target postgresql
```

### 场景 6：ES 数据导出和导入

```bash
# 仅导出 ES 数据
python3 cli.py export --config config.yaml --source es

# 仅导入 ES 数据
python3 cli.py import --config config.yaml --target es

# 一键：ES → ES
python3 cli.py export-import --config config.yaml --source es --target es
```

### 场景 7：同时导入多个目标（MySQL + PostgreSQL + ES）

配置文件同时有 `target`、`pg_target` 和 `es_target` 时：

```bash
# 自动导入到所有配置的目标
python3 cli.py import --config config.yaml

# 输出：
# Importing to: MYSQL, POSTGRESQL, ES
# [MYSQL] Import completed
# [PostgreSQL] Import completed
# [Elasticsearch] Import completed
# All imports completed successfully!
```

### 场景 8：仅导入某个目标

```bash
# 仅导入 MySQL
python3 cli.py import --config config.yaml --target mysql

# 仅导入 PostgreSQL
python3 cli.py import --config config.yaml --target postgresql

# 仅导入 Elasticsearch
python3 cli.py import --config config.yaml --target es
```

### 场景 9：导入前清空目标表

```bash
# 清空 MySQL 并导入
python3 cli.py import --config config.yaml --target mysql --drop-tables

# 清空 PostgreSQL 并导入
python3 cli.py import --config config.yaml --target postgresql --drop-tables
```

### 场景 10：导出多个资产

在 config.yaml 中配置多个资产 ID：

```yaml
assets:
  - 2019410738962841604
  - 2018021633618649093
  - 2019410738962841605
  # ... 更多资产
```

然后运行：
```bash
# 自动导出所有配置的数据源中的这些资产
python3 cli.py export --config config.yaml
```

---

## 🔍 故障排查

### 问题：导出失败，提示连接错误

**检查事项：**
1. 源数据库连接是否正常
2. config 中的 host、port、user、password 是否正确
3. 数据库是否允许远程连接

```bash
# 测试 MySQL 连接
mysql -h 10.21.19.99 -u root -p -D SSA -e "SELECT COUNT(*) FROM XDR_ASSET;"

# 测试 PostgreSQL 连接
psql -h 192.168.113.169 -p 15432 -U root -d ssa -c "SELECT COUNT(*) FROM xdr_asset;"

# 测试 ES 连接
curl -u elastic:password https://10.21.19.99:9200/_cat/indices
```

### 问题：PostgreSQL 导入失败，表不存在

**解决方案：**
1. 确保目标 PostgreSQL 数据库中已创建所有需要的表
2. 表名应该是小写的（PostgreSQL 默认大小写敏感）
3. 检查表是否在 public schema 中

```bash
# 检查目标表是否存在
psql -h host -p port -U user -d db -c "\dt"
```

### 问题：导入失败，主键冲突

**解决方案：**
```bash
# 方法 1：使用智能删除（推荐，仅删除指定资产的旧数据）
python3 cli.py import --config config.yaml

# 方法 2：删除旧数据再导入
python3 cli.py import --config config.yaml --drop-tables

# 方法 3：手动删除冲突的资产
# 在目标库执行：
# MySQL: DELETE FROM XDR_ASSET WHERE asset_id IN (2019410738962841604, ...);
# PostgreSQL: DELETE FROM xdr_asset WHERE asset_id IN (2019410738962841604, ...);
```

### 问题：ES 导入找不到文件

**解决方案：**
1. 确保 `es_export.output_dir` 配置正确
2. 检查导出目录是否存在
3. 确保目录下有 .ndjson 文件

```bash
# 查看导出目录
ls -la ./exports/es_latest/
```

### 问题：导出的文件很大

**优化建议：**
1. 分批导出（分次导出不同的资产）
2. 压缩导出文件

```bash
# 压缩导出
python3 cli.py export --config config.yaml | gzip > export.sql.gz
```

---

## 📖 获取帮助

```bash
# 查看所有命令
python3 cli.py --help

# 查看特定命令的参数
python3 cli.py export --help
python3 cli.py import --help
python3 cli.py export-import --help
```

---

## 📅 时间戳占位符

配置中的 `{timestamp}` 会自动替换：

```yaml
export:
  output: ./exports/assets_export_{timestamp}.sql
es_export:
  output_dir: ./exports/es_{timestamp}/
```

替换结果示例：
```
./exports/assets_export_20260601_160940.sql
./exports/es_20260601_160940/
```

格式：`YYYYMMDD_HHMMSS`

---

## 🚀 性能提示

### 大数据量导出

```bash
# 增加超时时间（如需要）
export MYSQL_CLIENT_CONNECT_TIMEOUT=30
python3 cli.py export --config config.yaml
```

### 批量操作

对于多个资产的导出，推荐在配置文件中列出所有资产 ID，而不是多次运行命令：

```yaml
assets:
  - 2019410738962841604
  - 2018021633618649093
  - 2019410738962841605
  # ... 更多资产
```

### ES 导出优化

```yaml
es_export:
  size_per_batch: 5000  # 增加每批大小，提高导出速度
```

---

## 📌 注意事项

1. **配置文件安全**：不要在配置文件中提交密码到 Git，使用环境变量或密钥管理服务
2. **数据备份**：导入前务必备份目标数据库
3. **导出文件存储**：导出文件包含敏感数据，请妥善保管
4. **验证**：导入后总是验证数据完整性
5. **资产列表**：务必在 config.yaml 的 `assets` 字段中指定要导出的资产
6. **PostgreSQL 表名**：PostgreSQL 表名默认是小写的，导入时会自动处理
7. **SQL 转换**：从 MySQL 导入到 PostgreSQL 时，会自动进行语法转换
8. **智能删除**：默认情况下，导入前会删除目标库中与配置资产相关的旧数据，而不是清空整个表

---

## 🔄 版本对比（v1.0 → v1.1）

| 操作 | v1.0 命令 | v1.1 命令 |
|------|----------|----------|
| **导出资产** | `export-assets-from-config --config FILE` | `export --config FILE` |
| **导入** | `import ...` | `import --config FILE` |
| **导出+导入** | `export-import-asset --config FILE` | `export-import --config FILE` |
| **ES 导出+导入** | `export-import-es-from-config --config FILE` | `export-import --config FILE --source es --target es` |
| **PostgreSQL 导入** | 不支持 | `import --config FILE --target postgresql` |
| **MySQL→PostgreSQL** | 不支持 | `export-import --config FILE --source mysql --target postgresql` |

**升级建议**：推荐使用新命令，旧命令仍可用但不再维护。

---

## 💡 核心概念

- **资产导出**：按 `assets` 字段中指定的资产 ID 进行导出
- **关联数据**：导出资产的所有相关表（IP、漏洞、风险端口、弱密码等）
- **多源导出**：`export` 命令支持同时导出 MySQL 和 Elasticsearch
  - 不指定 `--source` 时，自动导出 config 中配置的所有数据源
  - 指定 `--source` 时，仅导出指定的数据源
- **多目标导入**：`import` 命令支持同时导入 MySQL、PostgreSQL 和 Elasticsearch
  - 不指定 `--target` 时，自动导入到 config 中配置的所有目标
  - 指定 `--target` 时，仅导入到指定的目标
- **自动检测**：系统会根据 config.yaml 自动检测可用的数据源和目标
- **SQL 转换**：自动将 MySQL 语法转换为 PostgreSQL 兼容语法
- **智能删除**：导入前仅删除指定资产的旧数据，保留其他数据
- **验证**：导入后自动验证数据完整性（可配置）

---

## 📞 支持

遇到问题？查看：
- `README.md` - 项目说明和 PostgreSQL 适配详细文档
- `cli.py --help` - 命令行帮助

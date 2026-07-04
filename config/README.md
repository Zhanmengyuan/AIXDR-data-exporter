# AIXDR 数据迁移配置模板

本目录包含标准化的数据迁移配置模板，用户只需修改参数值即可快速完成数据迁移。

## 📁 配置模板文件

| 模板文件 | 适用场景 | 特点 |
|---------|---------|------|
| **template_mysql_es.yaml** | MySQL + ES 迁移 | MySQL→MySQL + ES→ES |
| **template_postgresql_es.yaml** | PostgreSQL + ES 迁移 | PostgreSQL→PostgreSQL + ES→ES |
| **template_mysql_to_pg_es.yaml** | 跨库迁移 | MySQL→PostgreSQL + ES→ES（自动语法转换） |

## 🚀 快速开始（3 步完成迁移）

### 第一步：选择模板

根据迁移场景选择合适的配置模板：

```bash
# MySQL + ES 迁移
cp config/template_mysql_es.yaml config/my_migration.yaml

# PostgreSQL + ES 迁移
cp config/template_postgresql_es.yaml config/my_migration.yaml

# MySQL → PostgreSQL 跨库迁移
cp config/template_mysql_to_pg_es.yaml config/my_migration.yaml
```

### 第二步：修改参数

打开配置文件，修改标记为 **【必填】** 的字段：

**必须修改：**
- ✅ 数据库地址、端口、用户名、密码
- ✅ Elasticsearch 地址、端口、用户名、密码
- ✅ 资产 ID 列表
- ✅ ES 索引月份（如 `202605, 202604, 202603`）

**可选修改：**
- 导出文件路径（默认已设置）
- ES 索引名称（默认已设置）

### 第三步：执行迁移

```bash
# 一键迁移（推荐）
aixdr-exporter export-import --config config/my_migration.yaml

# 或指定数据源和目标
aixdr-exporter export-import --config config/my_migration.yaml --source mysql --target postgresql
```

## 📊 三种迁移场景对比

### 场景 1：MySQL + Elasticsearch

**使用场景：** MySQL 数据库迁移 + ES 集群迁移

**配置要点：**
```yaml
source:      # MySQL 源数据库【必填】
target:      # MySQL 目标数据库【必填】
es_source:   # ES 源集群【必填】
es_target:   # ES 目标集群【必填】
assets:      # 资产 ID【必填】
index_cycles: # ES 月份索引【必填】
```

**执行命令：**
```bash
# 完整迁移
aixdr-exporter export-import --config my_config.yaml

# 仅迁移 MySQL
aixdr-exporter export-import --config my_config.yaml --source mysql --target mysql

# 仅迁移 ES
aixdr-exporter export-import --config my_config.yaml --source es --target es
```

---

### 场景 2：PostgreSQL + Elasticsearch

**使用场景：** PostgreSQL 数据库迁移 + ES 集群迁移

**配置要点：**
```yaml
pg_source:   # PostgreSQL 源数据库【必填】
pg_target:   # PostgreSQL 目标数据库【必填】
es_source:   # ES 源集群【必填】
es_target:   # ES 目标集群【必填】
assets:      # 资产 ID【必填】
index_cycles: # ES 月份索引【必填】
```

**执行命令：**
```bash
# 完整迁移
aixdr-exporter export-import --config my_config.yaml

# 仅迁移 PostgreSQL
aixdr-exporter export-import --config my_config.yaml --source postgresql --target postgresql

# 仅迁移 ES
aixdr-exporter export-import --config my_config.yaml --source es --target es
```

---

### 场景 3：MySQL → PostgreSQL（跨库迁移）

**使用场景：** 从 MySQL 迁移到 PostgreSQL + ES 集群迁移

**特点：** **自动 SQL 语法转换**
- ✅ 反引号 → 双引号
- ✅ MySQL 语法 → PostgreSQL 语法
- ✅ 数据类型自动转换

**配置要点：**
```yaml
source:      # MySQL 源数据库【必填】
pg_target:   # PostgreSQL 目标数据库【必填】
es_source:   # ES 源集群【必填】
es_target:   # ES 目标集群【必填】
assets:      # 资产 ID【必填】
index_cycles: # ES 月份索引【必填】
```

**执行命令：**
```bash
# 完整迁移（MySQL → PostgreSQL + ES → ES）
aixdr-exporter export-import --config my_config.yaml --source mysql --target postgresql

# 仅迁移 MySQL → PostgreSQL（自动语法转换）
aixdr-exporter export-import --config my_config.yaml --source mysql --target postgresql

# 仅迁移 ES
aixdr-exporter export-import --config my_config.yaml --source es --target es
```

## 🔧 关键配置字段说明

### 数据库配置

| 字段 | MySQL | PostgreSQL | 说明 |
|------|-------|-----------|------|
| 配置块名 | `source` / `target` | `pg_source` / `pg_target` | PostgreSQL 用 `pg_` 前缀 |
| 默认端口 | 3306 | 5432 | 根据实际端口修改 |
| 数据库名 | SSA | ssa | PostgreSQL 通常用小写 |

### Elasticsearch 配置

```yaml
es_source:
  host: 10.21.19.99       # ES 地址【必填】
  port: 9200              # ES 端口【必填】
  user: elastic           # ES 用户名【必填】
  password: your_password # ES 密码【必填】
  use_ssl: true           # SSL 开关【必填】
```

### 资产 ID 配置

```yaml
assets:
  - 2019410738962841604   # 资产 ID 1【必填】
  - 2018021633618649093   # 资产 ID 2【必填】
```

**获取资产 ID：**
```sql
SELECT asset_id FROM xdr_asset WHERE asset_name = '目标资产名称';
```

### ES 索引月份配置

```yaml
es_indices:
  index_cycles: [202605, 202604, 202603]  # 必填，格式 YYYYMM
```

**说明：**
- 导出 `maxs_alarm_202605`, `maxs_event_202605` 等索引
- 建议导出最近 3-6 个月的数据

## 📝 配置文件对比表

| 配置项 | MySQL→MySQL+ES | PostgreSQL→Pg+ES | MySQL→Pg+ES |
|-------|---------------|------------------|-------------|
| **源数据库** | `source` | `pg_source` | `source` |
| **目标数据库** | `target` | `pg_target` | `pg_target` |
| **ES 源** | `es_source` | `es_source` | `es_source` |
| **ES 目标** | `es_target` | `es_target` | `es_target` |
| **SQL 转换** | ❌ 不需要 | ❌ 不需要 | ✅ 自动转换 |

## ⚠️ 重要提示

### 1. 密码安全
```bash
# 不要提交包含真实密码的配置文件到 Git
git add config/my_migration.yaml  # ❌ 避免这样做
```

### 2. 网络连接
确保能连接到：
- ✅ 源数据库
- ✅ 目标数据库
- ✅ 源 ES 集群
- ✅ 目标 ES 集群

### 3. 数据验证
迁移完成后，工具会自动验证：
- ✅ 表是否存在
- ✅ 数据行数是否匹配
- ✅ 索引是否存在
- ✅ 文档数量是否匹配

### 4. 智能删除模式
导入时使用智能删除：
- ✅ 仅删除指定 `asset_id` 的相关数据
- ✅ 不影响其他资产的数据
- ✅ 保留表结构不变

## 📖 详细使用指南

查看完整的配置模板使用指南：

```bash
# 查看详细指南
cat config/CONFIG_TEMPLATE_GUIDE.md

# 或在编辑器中打开
open config/CONFIG_TEMPLATE_GUIDE.md
```

## 🔍 配置文件验证

验证配置文件语法：

```bash
# 验证所有配置模板
python3 validate_configs.py

# 输出：
# ✓ config/template_mysql_es.yaml - YAML syntax valid
# ✓ config/template_postgresql_es.yaml - YAML syntax valid
# ✓ config/template_mysql_to_pg_es.yaml - YAML syntax valid
```

## 📞 常见问题

**Q1: 如何只迁移数据库，不迁移 ES？**
```bash
aixdr-exporter export-import --config my_config.yaml --source mysql --target postgresql
```

**Q2: 如何只迁移 ES，不迁移数据库？**
```bash
aixdr-exporter export-import --config my_config.yaml --source es --target es
```

**Q3: MySQL → PostgreSQL 会自动转换 SQL 吗？**
是的，工具会自动转换 MySQL 语法到 PostgreSQL 兼容语法。

**Q4: 如何选择 ES 月份索引？**
在配置文件的 `index_cycles` 字段中设置，格式为 YYYYMM。

## ✅ 下一步

1. 选择合适的配置模板
2. 修改必填参数值
3. 执行迁移命令
4. 验证迁移结果

详细操作请参考：[CONFIG_TEMPLATE_GUIDE.md](CONFIG_TEMPLATE_GUIDE.md)
# AIXDR 数据迁移配置模板使用指南

## 📁 配置模板文件列表

| 模板文件名 | 适用场景 | 说明 |
|-----------|---------|------|
| `template_mysql_es.yaml` | MySQL + ES 迁移 | MySQL → MySQL + ES → ES |
| `template_postgresql_es.yaml` | PostgreSQL + ES 迁移 | PostgreSQL → PostgreSQL + ES → ES |
| `template_mysql_to_pg_es.yaml` | 跨库迁移 | MySQL → PostgreSQL + ES → ES（自动语法转换） |

---

## 🚀 快速使用步骤

### 第一步：选择合适的模板

根据您的迁移场景，选择对应的配置模板：

```bash
# 查看可用的配置模板
ls config/template_*.yaml

# 输出：
# template_mysql_es.yaml           # MySQL + ES 迁移
# template_postgresql_es.yaml      # PostgreSQL + ES 迁移  
# template_mysql_to_pg_es.yaml     # MySQL → PostgreSQL 跨库迁移
```

### 第二步：复制模板文件

```bash
# 选择模板并复制（以 MySQL + ES 为例）
cp config/template_mysql_es.yaml config/my_migration.yaml
```

### 第三步：修改配置参数

打开复制后的配置文件，修改标记为 **【必填】** 的参数：

**必须修改的字段：**
- ✅ 数据库地址（`host`）
- ✅ 数据库端口（`port`）
- ✅ 数据库用户名（`user`）
- ✅ 数据库密码（`password`）
- ✅ 数据库名（`database`）
- ✅ Elasticsearch 地址、端口、用户名、密码
- ✅ 资产 ID 列表（`assets`）
- ✅ ES 索引月份（`index_cycles`）

**可选修改的字段：**
- 导出文件路径（默认已设置）
- ES 索引名称（默认已设置）
- 验证开关（默认已设置）

### 第四步：执行迁移命令

```bash
# 一键迁移（推荐）
aixdr-exporter export-import --config config/my_migration.yaml

# 或者指定数据源和目标
aixdr-exporter export-import --config config/my_migration.yaml --source mysql --target postgresql
```

---

## 📋 三种迁移场景详细说明

### 场景 1：MySQL + Elasticsearch 迁移

**模板文件：** `template_mysql_es.yaml`

**适用情况：**
- MySQL 数据库之间迁移
- Elasticsearch 集群之间迁移
- 同时迁移 MySQL 和 ES 数据

**配置要点：**
```yaml
# MySQL 配置
source:          # MySQL 源数据库
target:          # MySQL 目标数据库

# ES 配置
es_source:       # ES 源集群
es_target:       # ES 目标集群

# 数据选择
assets:          # 资产 ID 列表
index_cycles:    # ES 索引月份
```

**执行命令：**
```bash
# 完整迁移（MySQL + ES）
aixdr-exporter export-import --config my_config.yaml

# 仅迁移 MySQL
aixdr-exporter export-import --config my_config.yaml --source mysql --target mysql

# 仅迁移 ES
aixdr-exporter export-import --config my_config.yaml --source es --target es
```

---

### 场景 2：PostgreSQL + Elasticsearch 迁移

**模板文件：** `template_postgresql_es.yaml`

**适用情况：**
- PostgreSQL 数据库之间迁移
- Elasticsearch 集群之间迁移
- 同时迁移 PostgreSQL 和 ES 数据

**配置要点：**
```yaml
# PostgreSQL 配置
pg_source:       # PostgreSQL 源数据库
pg_target:       # PostgreSQL 目标数据库

# ES 配置
es_source:       # ES 源集群
es_target:       # ES 目标集群

# 数据选择
assets:          # 资产 ID 列表
index_cycles:    # ES 索引月份
```

**执行命令：**
```bash
# 完整迁移（PostgreSQL + ES）
aixdr-exporter export-import --config my_config.yaml

# 仅迁移 PostgreSQL
aixdr-exporter export-import --config my_config.yaml --source postgresql --target postgresql

# 仅迁移 ES
aixdr-exporter export-import --config my_config.yaml --source es --target es
```

---

### 场景 3：MySQL → PostgreSQL 跨库迁移

**模板文件：** `template_mysql_to_pg_es.yaml`

**适用情况：**
- 从 MySQL 迁移到 PostgreSQL
- Elasticsearch 集群之间迁移
- **自动 SQL 语法转换**（MySQL → PostgreSQL）

**配置要点：**
```yaml
# 源数据库（MySQL）
source:          # MySQL 源数据库

# 目标数据库（PostgreSQL）
pg_target:       # PostgreSQL 目标数据库

# ES 配置
es_source:       # ES 源集群
es_target:       # ES 目标集群

# 数据选择
assets:          # 资产 ID 列表
index_cycles:    # ES 索引月份
```

**执行命令：**
```bash
# 完整迁移（MySQL → PostgreSQL + ES → ES）
aixdr-exporter export-import --config my_config.yaml --source mysql --target postgresql

# 仅迁移 MySQL → PostgreSQL
aixdr-exporter export-import --config my_config.yaml --source mysql --target postgresql

# 仅迁移 ES
aixdr-exporter export-import --config my_config.yaml --source es --target es
```

**特点：**
- ✅ 自动将 MySQL SQL 语法转换为 PostgreSQL 兼容语法
- ✅ 自动处理数据类型差异（如布尔值、日期格式）
- ✅ 自动转换反引号为双引号（PostgreSQL 标准）

---

## 🔧 配置字段详解

### 数据库连接配置

#### MySQL 配置
```yaml
source:                   # 或 target
  host: 10.21.19.99       # 数据库地址【必填】
  port: 3306              # 端口【必填】（默认 3306）
  user: root              # 用户名【必填】
  password: your_password # 密码【必填】
  database: SSA           # 数据库名【必填】
```

#### PostgreSQL 配置
```yaml
pg_source:                # 或 pg_target
  host: 192.168.112.150   # 数据库地址【必填】
  port: 5432              # 端口【必填】（默认 5432）
  user: root              # 用户名【必填】
  password: your_password # 密码【必填】
  database: ssa           # 数据库名【必填】
```

#### Elasticsearch 配置
```yaml
es_source:                # 或 es_target
  host: 10.21.19.99       # ES 集群地址【必填】
  port: 9200              # ES 端口【必填】（默认 9200）
  user: elastic           # ES 用户名【必填】
  password: your_password # ES 密码【必填】
  use_ssl: true           # 是否使用 SSL【必填】
```

### 资产 ID 配置
```yaml
assets:
  - 2019410738962841604   # 资产 ID 1【必填】
  - 2018021633618649093   # 资产 ID 2【必填】
  # 可以添加更多资产 ID...
```

**获取资产 ID 的方法：**
```sql
-- 在源数据库中查询
SELECT asset_id FROM xdr_asset WHERE asset_name = '目标资产名称';
```

### ES 索引配置
```yaml
es_indices:
  asset: xdr_asset                    # 资产索引【可选】
  fingerprint: xdr_asset_fingerprint  # 指纹索引【可选】
  asset_his: xdr_asset_his            # 历史索引【可选】
  alarm_pattern: maxs_alarm_          # 告警索引前缀【可选】
  event_pattern: maxs_event_          # 事件索引前缀【可选】
  
  # 要导出的月份【必填】
  index_cycles: [202605, 202604, 202603]
```

**月份索引说明：**
- 格式：YYYYMM（年月）
- 例如：202605 表示 2026年5月
- 会导出 `maxs_alarm_202605` 和 `maxs_event_202605` 等索引

---

## ⚙️ 高级配置选项

### 导出文件路径
```yaml
export:
  output: ./exports/assets_export.sql  # MySQL/PostgreSQL 导出文件
  
es_export:
  output_dir: ./exports/es_latest/      # ES 导出目录
  size_per_batch: 1000                  # 每批次导出数量
```

### 数据验证
```yaml
verify:
  enabled: true  # 导入后验证数据完整性（默认 true）
```

---

## 📊 迁移数据说明

### MySQL/PostgreSQL 迁移的数据表

| 表名 | 说明 | 过滤条件 |
|------|------|----------|
| `xdr_asset` | 资产主表 | 按 `asset_id` |
| `xdr_asset_ip` | 资产 IP | 按 `asset_id` |
| `xdr_asset_vuln` | 资产漏洞 | 按 `asset_id` |
| `xdr_risk_port` | 风险端口 | 按 `asset_id` |
| `xdr_weak_password` | 弱密码 | 按 `device_id`（关联自 `xdr_asset`） |

### Elasticsearch 迁移的索引

| 索引名 | 说明 | 过滤条件 |
|--------|------|----------|
| `xdr_asset` | 资产索引 | 按 `asset_id` |
| `xdr_asset_fingerprint` | 资产指纹 | 按 `asset_id` |
| `xdr_asset_his` | 资产历史 | 按 `asset_id` |
| `maxs_alarm_YYYYMM` | 告警索引 | 按 `asset_id` + 月份 |
| `maxs_event_YYYYMM` | 事件索引 | 按 `asset_id` + 月份 |

---

## 🎯 常见问题解答

### Q1: 如何只迁移 MySQL 数据，不迁移 ES？

**A:** 使用配置模板，但执行命令时指定数据源：
```bash
aixdr-exporter export-import --config my_config.yaml --source mysql --target mysql
```

### Q2: 如何只迁移 ES 数据，不迁移 MySQL？

**A:** 使用配置模板，但执行命令时指定数据源：
```bash
aixdr-exporter export-import --config my_config.yaml --source es --target es
```

### Q3: MySQL → PostgreSQL 迁移会自动转换 SQL 吗？

**A:** 是的！工具会自动转换：
- 反引号 ` → 双引号 "
- MySQL BOOLEAN → PostgreSQL BOOLEAN
- MySQL 日期格式 → PostgreSQL 日期格式
- MySQL AUTO_INCREMENT → PostgreSQL SERIAL

### Q4: 如何选择要导出的 ES 月份索引？

**A:** 在配置文件中设置 `index_cycles`：
```yaml
es_indices:
  index_cycles: [202605, 202604, 202603]  # 导出最近3个月
```

### Q5: 导入时会删除旧数据吗？

**A:** 默认使用智能删除模式：
- 仅删除指定 `asset_id` 的相关数据
- 不影响其他资产的数据
- 保留表结构不变

---

## 📝 配置模板示例对比

| 配置项 | MySQL→MySQL+ES | Pg→Pg+ES | MySQL→Pg+ES |
|-------|---------------|----------|-------------|
| 源数据库 | `source` | `pg_source` | `source` |
| 目标数据库 | `target` | `pg_target` | `pg_target` |
| ES 源 | `es_source` | `es_source` | `es_source` |
| ES 目标 | `es_target` | `es_target` | `es_target` |
| SQL 转换 | ❌ 不需要 | ❌ 不需要 | ✅ 自动转换 |
| 导出格式 | MySQL SQL | PostgreSQL SQL | MySQL SQL |

---

## 🚨 注意事项

1. **密码安全**：不要将包含真实密码的配置文件提交到 Git
2. **资产 ID**：确保资产 ID 在源数据库中存在
3. **ES 月份**：确保指定的月份索引在 ES 中存在
4. **网络连接**：确保能连接到源和目标数据库/ES
5. **数据备份**：迁移前建议备份目标数据库

---

## ✅ 验证迁移结果

迁移完成后，工具会自动验证数据完整性：

**验证内容：**
- ✅ 表是否存在
- ✅ 数据行数是否匹配
- ✅ 索引是否存在
- ✅ 文档数量是否匹配

**手动验证：**
```sql
-- PostgreSQL/MySQL 验证
SELECT COUNT(*) FROM xdr_asset WHERE asset_id IN (目标资产ID列表);
SELECT COUNT(*) FROM xdr_asset_ip WHERE asset_id IN (目标资产ID列表);

-- Elasticsearch 验证（使用 Kibana 或 API）
GET xdr_asset/_count?q=asset_id:目标资产ID
```

---

## 📞 技术支持

遇到问题请检查：
1. 配置文件格式是否正确（YAML 格式）
2. 数据库连接信息是否正确
3. 资产 ID 是否存在
4. ES 索引月份是否正确

查看详细日志：
```bash
# 执行迁移时查看详细输出
aixdr-exporter export-import --config my_config.yaml --verbose
```
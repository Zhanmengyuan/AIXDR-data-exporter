"""AIXDR Data Exporter CLI - Refactored"""

import json
import os
import urllib3
import click
from colorama import Fore, Style, init
from exporter import (
    ConfigManager,
    Workflow,
    MySQLHandler,
    PostgreSQLHandler,
    ElasticsearchHandler,
)

urllib3.disable_warnings()

# Initialize colorama for colored output
init()


def print_success(msg: str):
    """Print success message"""
    click.echo(f"{Fore.GREEN}✓ {msg}{Style.RESET_ALL}")


def print_error(msg: str):
    """Print error message"""
    click.echo(f"{Fore.RED}✗ {msg}{Style.RESET_ALL}")


def print_info(msg: str):
    """Print info message"""
    click.echo(f"{Fore.CYAN}ℹ {msg}{Style.RESET_ALL}")


def print_warning(msg: str):
    """Print warning message"""
    click.echo(f"{Fore.YELLOW}⚠ {msg}{Style.RESET_ALL}")


def get_handler(source_type: str):
    """Get appropriate handler based on source type"""
    if source_type == 'mysql':
        return MySQLHandler()
    elif source_type == 'postgresql':
        return PostgreSQLHandler()
    elif source_type == 'es':
        return ElasticsearchHandler()
    else:
        raise ValueError(f"Unknown source type: {source_type}")


@click.group()
def cli():
    """AIXDR Data Exporter - Export and import AIXDR asset data"""
    pass


@cli.command()
@click.option('--config', required=True, help='Configuration file path')
@click.option('--source', type=click.Choice(['mysql', 'postgresql', 'es']), help='Data source type (auto-detect if not specified)')
@click.option('--output', help='Output file/directory path (overrides config)')
def export(config, source, output):
    """Export asset data from source database/Elasticsearch

    If no --source is specified, will auto-detect and export:
    - MySQL if source config exists
    - PostgreSQL if pg_source config exists
    - Elasticsearch if es_source config exists
    - All available sources if multiple configs exist
    """
    try:
        # Load config
        cfg = ConfigManager.load_config(config)

        # Determine which data sources to export
        has_mysql = bool(cfg.get('source'))
        has_pg = bool(cfg.get('pg_source'))
        has_es = bool(cfg.get('es_source'))

        # If source is specified, use only that
        if source:
            sources_to_export = [source]
        else:
            # Auto-detect: export available sources
            sources_to_export = []
            if has_mysql:
                sources_to_export.append('mysql')
            if has_pg:
                sources_to_export.append('postgresql')
            if has_es:
                sources_to_export.append('es')

        if not sources_to_export:
            print_error("No data source configured (need 'source', 'pg_source', or 'es_source' in config)")
            return

        print_info("=" * 60)
        print_info(f"Exporting from: {', '.join(s.upper() for s in sources_to_export)}")
        print_info("=" * 60)

        all_success = True
        export_summary = {
            'mysql': {'success': False, 'file': None, 'size': 0, 'status': 'Not exported'},
            'postgresql': {'success': False, 'file': None, 'size': 0, 'status': 'Not exported'},
            'es': {'success': False, 'dir': None, 'files': [], 'status': 'Not exported'},
        }

        # Export from each source
        for source_type in sources_to_export:
            print_info(f"\n[{source_type.upper()}] Starting export...")

            if source_type == 'mysql':
                valid, msg = ConfigManager.validate_source_config(cfg)
                if not valid:
                    print_error(f"[MySQL] {msg}")
                    export_summary['mysql']['status'] = f"Failed: {msg}"
                    all_success = False
                    continue

                source_cfg = ConfigManager.extract_source_config(cfg)
                asset_ids = ConfigManager.extract_asset_ids(cfg)
                output_file = output or ConfigManager.extract_export_output(cfg)
                output_file = ConfigManager.resolve_output_path(output_file)

                handler = get_handler('mysql')
                result = Workflow.execute_export(
                    handler=handler,
                    config=source_cfg,
                    mode='asset',
                    asset_ids=asset_ids,
                    table_list=None,
                    output_path=output_file,
                )

                if result:
                    # Get file info
                    if os.path.exists(output_file):
                        file_size = os.path.getsize(output_file)
                        export_summary['mysql']['success'] = True
                        export_summary['mysql']['file'] = output_file
                        export_summary['mysql']['size'] = file_size
                        export_summary['mysql']['status'] = 'Success'
                        print_success(f"[MySQL] Export completed")
                    else:
                        export_summary['mysql']['status'] = 'File not found'
                        print_error(f"[MySQL] Export file not found: {output_file}")
                        all_success = False
                else:
                    export_summary['mysql']['status'] = 'Export failed'
                    print_error(f"[MySQL] Export failed")
                    all_success = False

            elif source_type == 'postgresql':
                valid, msg = ConfigManager.validate_pg_source_config(cfg)
                if not valid:
                    print_error(f"[PostgreSQL] {msg}")
                    export_summary['postgresql']['status'] = f"Failed: {msg}"
                    all_success = False
                    continue

                source_cfg = ConfigManager.extract_pg_source_config(cfg)
                asset_ids = ConfigManager.extract_asset_ids(cfg)
                output_file = output or ConfigManager.extract_export_output(cfg)
                output_file = ConfigManager.resolve_output_path(output_file)

                handler = get_handler('postgresql')
                result = Workflow.execute_export(
                    handler=handler,
                    config=source_cfg,
                    mode='asset',
                    asset_ids=asset_ids,
                    table_list=None,
                    output_path=output_file,
                )

                if result:
                    # Get file info
                    if os.path.exists(output_file):
                        file_size = os.path.getsize(output_file)
                        export_summary['postgresql']['success'] = True
                        export_summary['postgresql']['file'] = output_file
                        export_summary['postgresql']['size'] = file_size
                        export_summary['postgresql']['status'] = 'Success'
                        print_success(f"[PostgreSQL] Export completed")
                    else:
                        export_summary['postgresql']['status'] = 'File not found'
                        print_error(f"[PostgreSQL] Export file not found: {output_file}")
                        all_success = False
                else:
                    export_summary['postgresql']['status'] = 'Export failed'
                    print_error(f"[PostgreSQL] Export failed")
                    all_success = False

            elif source_type == 'es':
                valid, msg = ConfigManager.validate_es_source_config(cfg)
                if not valid:
                    print_error(f"[Elasticsearch] {msg}")
                    export_summary['es']['status'] = f"Failed: {msg}"
                    all_success = False
                    continue

                source_cfg = ConfigManager.extract_es_source_config(cfg)
                asset_ids = ConfigManager.extract_asset_ids(cfg)

                # Get ES indices config
                es_indices = ConfigManager.extract_es_indices(cfg)
                index_cycles = es_indices.get('index_cycles', [])
                table_list = {'index_cycles': index_cycles} if index_cycles else None

                output_file = output or ConfigManager.extract_es_export_output(cfg)
                output_file = ConfigManager.resolve_output_path(output_file)

                handler = get_handler('es')
                result = Workflow.execute_export(
                    handler=handler,
                    config=source_cfg,
                    mode='asset',
                    asset_ids=asset_ids,
                    table_list=table_list,
                    output_path=output_file,
                )

                if result:
                    # Get directory info
                    if os.path.exists(output_file):
                        es_files = [f for f in os.listdir(output_file) if f.endswith('.ndjson')]
                        export_summary['es']['success'] = True
                        export_summary['es']['dir'] = output_file
                        export_summary['es']['files'] = es_files
                        export_summary['es']['status'] = 'Success'
                        print_success(f"[Elasticsearch] Export completed")
                    else:
                        export_summary['es']['status'] = 'Directory not found'
                        print_error(f"[Elasticsearch] Export directory not found: {output_file}")
                        all_success = False
                else:
                    export_summary['es']['status'] = 'Export failed'
                    print_error(f"[Elasticsearch] Export failed")
                    all_success = False

        # Print detailed summary
        print_info("\n" + "=" * 70)
        print_info("导出汇总报告 (Export Summary Report)")
        print_info("=" * 70)

        # MySQL Summary
        mysql_info = export_summary['mysql']
        print_info("\n【MySQL 导出情况】")
        print_info(f"  状态: {mysql_info['status']}")
        if mysql_info['success']:
            print_info(f"  导出文件: {mysql_info['file']}")
            print_info(f"  文件大小: {mysql_info['size']:,} bytes ({mysql_info['size']/1024/1024:.2f} MB)")
            print_info(f"  数据来源: 生产库 ({source_cfg.get('host')})")
            print_info(f"  导出资产: {ConfigManager.extract_asset_ids(cfg)}")
        else:
            print_warning(f"  ❌ MySQL 导出失败")

        # PostgreSQL Summary
        pg_info = export_summary['postgresql']
        print_info("\n【PostgreSQL 导出情况】")
        print_info(f"  状态: {pg_info['status']}")
        if pg_info['success']:
            print_info(f"  导出文件: {pg_info['file']}")
            print_info(f"  文件大小: {pg_info['size']:,} bytes ({pg_info['size']/1024/1024:.2f} MB)")
            print_info(f"  数据来源: PostgreSQL库 ({source_cfg.get('host')})")
            print_info(f"  导出资产: {ConfigManager.extract_asset_ids(cfg)}")
        else:
            print_warning(f"  ❌ PostgreSQL 导出失败")

        # Elasticsearch Summary
        es_info = export_summary['es']
        print_info("\n【Elasticsearch 导出情况】")
        print_info(f"  状态: {es_info['status']}")
        if es_info['success']:
            print_info(f"  导出目录: {es_info['dir']}")
            print_info(f"  导出文件: {', '.join(es_info['files'])}")
            print_info(f"  数据来源: ES 集群 ({source_cfg.get('host')}:{source_cfg.get('port', 9200)})")
            print_info(f"  导出资产: {ConfigManager.extract_asset_ids(cfg)}")
            print_info(f"  索引周期: {index_cycles if index_cycles else '无周期配置'}")
        else:
            print_warning(f"  ❌ Elasticsearch 导出失败或部分失败")

        # Overall status
        print_info("\n" + "=" * 70)
        if all_success:
            print_success("✓ 所有导出任务完成！")
        else:
            print_warning("⚠ 某些导出任务失败，请查看上方日志")
        print_info("=" * 70)

    except Exception as e:
        print_error(f"Export error: {e}")


@cli.command()
@click.option('--config', required=True, help='Configuration file path')
@click.option('--input', help='Input file/directory path (overrides config)')
@click.option('--target', type=click.Choice(['mysql', 'postgresql', 'es']), help='Target type')
@click.option('--drop-tables', is_flag=True, default=False,
              help='Drop tables before import')
def import_(config, input, target, drop_tables):
    """Import data to target database/Elasticsearch"""
    import_impl(config, input, target, drop_tables)


@cli.command()
@click.option('--config', required=True, help='Configuration file path')
@click.option('--source', type=click.Choice(['mysql', 'postgresql', 'es']), help='Source type')
@click.option('--target', type=click.Choice(['mysql', 'postgresql', 'es']), help='Target type')
def export_import(config, source, target):
    """One-command export + import + verify for assets"""
    try:
        # Load config
        cfg = ConfigManager.load_config(config)

        # Detect source and target types
        source_type = source or ConfigManager.get_source_type(cfg)
        target_type = target or ConfigManager.get_target_type(cfg)

        print_info(f"Source: {source_type.upper()}, Target: {target_type.upper()}")

        # Validate both configs
        if source_type == 'mysql':
            valid, msg = ConfigManager.validate_source_config(cfg)
            if not valid:
                print_error(msg)
                return
            source_cfg = ConfigManager.extract_source_config(cfg)
            asset_ids = ConfigManager.extract_asset_ids(cfg)

        elif source_type == 'postgresql':
            valid, msg = ConfigManager.validate_pg_source_config(cfg)
            if not valid:
                print_error(msg)
                return
            source_cfg = ConfigManager.extract_pg_source_config(cfg)
            asset_ids = ConfigManager.extract_asset_ids(cfg)

        elif source_type == 'es':
            valid, msg = ConfigManager.validate_es_source_config(cfg)
            if not valid:
                print_error(msg)
                return
            source_cfg = ConfigManager.extract_es_source_config(cfg)
            asset_ids = ConfigManager.extract_asset_ids(cfg)
            es_indices = ConfigManager.extract_es_indices(cfg)
            table_list = {'index_cycles': es_indices.get('index_cycles', [])}

        else:
            print_error(f"Unsupported source type: {source_type}")
            return

        if target_type == 'mysql':
            valid, msg = ConfigManager.validate_target_config(cfg)
            if not valid:
                print_error(msg)
                return
            # Get the target config specifically, not the combined one
            target_dict = cfg.get('target', {})
            target_cfg = {
                'host': target_dict.get('host'),
                'user': target_dict.get('user'),
                'password': target_dict.get('password'),
                'database': target_dict.get('database'),
                'port': target_dict.get('port', 3306),
            }

        elif target_type == 'postgresql':
            valid, msg = ConfigManager.validate_pg_target_config(cfg)
            if not valid:
                print_error(msg)
                return
            target_cfg = ConfigManager.extract_pg_target_config(cfg)

        elif target_type == 'es':
            valid, msg = ConfigManager.validate_es_target_config(cfg)
            if not valid:
                print_error(msg)
                return
            target_cfg = ConfigManager.extract_es_target_config(cfg)

        else:
            print_error(f"Unsupported target type: {target_type}")
            return

        # Get temporary file path (ES uses a directory, MySQL/PostgreSQL use a file)
        if source_type == 'es':
            temp_file = ConfigManager.extract_es_export_output(cfg)
        else:
            temp_file = ConfigManager.extract_export_output(cfg)
        temp_file = ConfigManager.resolve_output_path(temp_file)

        # Check if verify is enabled
        verify_enabled = ConfigManager.is_verify_enabled(cfg)

        # Execute export first
        export_handler = get_handler(source_type)
        print_info(f"Starting export from {source_type.upper()}...")
        export_success = Workflow.execute_export(
            handler=export_handler,
            config=source_cfg,
            mode='asset',
            asset_ids=asset_ids,
            table_list=table_list if source_type == 'es' else None,
            output_path=temp_file,
        )

        if not export_success:
            print_error("Export failed, aborting import")
            return

        print_success("Export completed successfully!")

        # Now execute import
        import_handler = get_handler(target_type)
        print_info(f"Starting import to {target_type.upper()}...")

        if target_type == 'postgresql':
            # Determine if we need to convert from MySQL syntax
            convert_from_mysql = (source_type == 'mysql')
            import_success = import_handler.import_data(
                config=target_cfg,
                input_path=temp_file,
                drop_tables=False,
                asset_ids=asset_ids,
                convert_from_mysql=convert_from_mysql,
            )
        else:
            # For MySQL or ES, use the Workflow
            import_success = Workflow.execute_import(
                handler=import_handler,
                config=target_cfg,
                input_path=temp_file,
                drop_tables=False,
                asset_ids=asset_ids,
            )

        if import_success:
            print_success("Import completed successfully!")
        else:
            print_error("Import failed!")
            return

        # Verify if enabled
        if verify_enabled and target_type in ['mysql', 'postgresql']:
            print_info(f"Verifying {target_type.upper()} target...")
            verify_results = import_handler.verify(target_cfg)
            if verify_results and verify_results.get('all_valid'):
                print_success("Verification passed!")
            else:
                print_warning("Verification had issues")

        print_success("Export+Import completed successfully!")

    except Exception as e:
        print_error(f"Export+Import error: {e}")


@cli.command()
def validate():
    """Legacy command - show help"""
    print_info("Validation is now integrated into export-import command.")
    print_info("Use: python cli.py export-import --config config.yaml")


# Alias for import_ command
@cli.command(name='import')
@click.option('--config', required=True, help='Configuration file path')
@click.option('--input', help='Input file/directory path (overrides config)')
@click.option('--target', type=click.Choice(['mysql', 'postgresql', 'es']), help='Target type')
@click.option('--drop-tables', is_flag=True, default=False,
              help='Drop tables before import')
def import_alias(config, input, target, drop_tables):
    """Alias for import- command"""
    import_impl(config, input, target, drop_tables)


def import_impl(config, input, target, drop_tables):
    """Implementation of import command

    If no --target is specified, will auto-detect and import:
    - MySQL if target config exists
    - PostgreSQL if pg_target config exists
    - Elasticsearch if es_target config exists
    - Multiple targets if multiple configs exist

    For MySQL/PostgreSQL: Uses smart delete mode by default
    - Deletes only data for assets in config's 'assets' field
    - Preserves all other data in the database
    - Use --drop-tables flag to delete entire tables instead
    """
    try:
        # Load config
        cfg = ConfigManager.load_config(config)

        # Determine which data targets to import to
        has_mysql_target = bool(cfg.get('target'))
        has_pg_target = bool(cfg.get('pg_target'))
        has_es_target = bool(cfg.get('es_target'))

        # If target is specified, use only that
        if target:
            targets_to_import = [target]
        else:
            # Auto-detect: import to available targets
            targets_to_import = []
            if has_mysql_target:
                targets_to_import.append('mysql')
            if has_pg_target:
                targets_to_import.append('postgresql')
            if has_es_target:
                targets_to_import.append('es')

        if not targets_to_import:
            print_error("No import target configured (need 'target', 'pg_target', or 'es_target' in config)")
            return

        print_info("=" * 60)
        print_info(f"Importing to: {', '.join(t.upper() for t in targets_to_import)}")
        print_info("=" * 60)

        all_success = True

        # Import to each target
        for target_type in targets_to_import:
            print_info(f"\n[{target_type.upper()}] Starting import...")

            if target_type == 'mysql':
                valid, msg = ConfigManager.validate_target_config(cfg)
                if not valid:
                    print_error(f"[MySQL] {msg}")
                    all_success = False
                    continue

                target_cfg = ConfigManager.extract_source_config(cfg)  # Same format
                # Wait, we need to extract the target specifically, not source
                # Let's use the internal target dict
                target_dict = cfg.get('target', {})
                target_cfg = {
                    'host': target_dict.get('host'),
                    'user': target_dict.get('user'),
                    'password': target_dict.get('password'),
                    'database': target_dict.get('database'),
                    'port': target_dict.get('port', 3306),
                }
                input_file = input or ConfigManager.extract_import_input(cfg)

                if not os.path.exists(input_file):
                    print_error(f"[MySQL] Input file not found: {input_file}")
                    all_success = False
                    continue

                # Extract asset_ids for smart delete
                asset_ids = ConfigManager.extract_asset_ids(cfg) if not drop_tables else None

                handler = get_handler('mysql')
                result = Workflow.execute_import(
                    handler=handler,
                    config=target_cfg,
                    input_path=input_file,
                    drop_tables=drop_tables,
                    asset_ids=asset_ids,
                )

                if result:
                    print_success(f"[MySQL] Import completed")
                else:
                    print_error(f"[MySQL] Import failed")
                    all_success = False

            elif target_type == 'postgresql':
                valid, msg = ConfigManager.validate_pg_target_config(cfg)
                if not valid:
                    print_error(f"[PostgreSQL] {msg}")
                    all_success = False
                    continue

                target_cfg = ConfigManager.extract_pg_target_config(cfg)
                input_file = input or ConfigManager.extract_import_input(cfg)

                if not os.path.exists(input_file):
                    print_error(f"[PostgreSQL] Input file not found: {input_file}")
                    all_success = False
                    continue

                # Extract asset_ids for smart delete
                asset_ids = ConfigManager.extract_asset_ids(cfg) if not drop_tables else None

                handler = get_handler('postgresql')
                result = handler.import_data(
                    config=target_cfg,
                    input_path=input_file,
                    drop_tables=drop_tables,
                    asset_ids=asset_ids,
                    convert_from_mysql=True,
                )

                if result:
                    print_success(f"[PostgreSQL] Import completed")
                else:
                    print_error(f"[PostgreSQL] Import failed")
                    all_success = False

            elif target_type == 'es':
                valid, msg = ConfigManager.validate_es_target_config(cfg)
                if not valid:
                    print_error(f"[Elasticsearch] {msg}")
                    all_success = False
                    continue

                target_cfg = ConfigManager.extract_es_target_config(cfg)
                input_file = input or ConfigManager.extract_es_export_output(cfg)

                if not os.path.exists(input_file):
                    print_error(f"[Elasticsearch] Input directory not found: {input_file}")
                    all_success = False
                    continue

                handler = get_handler('es')
                result = Workflow.execute_import(
                    handler=handler,
                    config=target_cfg,
                    input_path=input_file,
                    drop_tables=drop_tables,
                )

                if result:
                    print_success(f"[Elasticsearch] Import completed")
                else:
                    print_error(f"[Elasticsearch] Import failed")
                    all_success = False

        print_info("=" * 60)
        if all_success:
            print_success("All imports completed successfully!")
        else:
            print_warning("Some imports failed, please check above")

        # Print final aggregated summary
        if has_pg_target and all_success:
            pg_target_config = ConfigManager.extract_pg_target_config(cfg)
            _print_pg_summary(pg_target_config)

        if has_es_target and all_success:
            es_target_config = ConfigManager.extract_es_target_config(cfg)
            _print_es_summary(es_target_config)

    except Exception as e:
        print_error(f"Import error: {e}")


def _print_pg_summary(pg_config):
    """打印 PostgreSQL 导入汇总统计"""
    import psycopg2
    try:
        conn = psycopg2.connect(
            host=pg_config['host'],
            user=pg_config['user'],
            password=pg_config['password'],
            dbname=pg_config['database'],
            port=pg_config.get('port', 5432),
        )
        cursor = conn.cursor()

        tables = ['xdr_asset', 'xdr_asset_ip', 'xdr_asset_vuln', 'xdr_risk_port', 'xdr_weak_password']
        print_info("\n" + "=" * 60)
        print_info("📊 PostgreSQL 导入汇总统计")
        print_info("=" * 60)
        total = 0
        for table in tables:
            try:
                cursor.execute(f'SELECT count(*) FROM {table}')
                cnt = cursor.fetchone()[0]
                label = {
                    'xdr_asset': '资产信息',
                    'xdr_asset_ip': 'IP 信息',
                    'xdr_asset_vuln': '漏洞信息',
                    'xdr_risk_port': '风险端口',
                    'xdr_weak_password': '弱密码',
                }.get(table, table)
                print_info(f"  {label:12s} ({table:20s}): {cnt:>8,} rows")
                total += cnt
            except Exception:
                print_info(f"  {table}: 表不存在")
        print_info("  " + "─" * 48)
        print_info(f"  {'总计':12s} {'':20s}: {total:>8,} rows")

        cursor.close()
        conn.close()
    except Exception as e:
        print_error(f"  PG 统计查询失败: {e}")


def _print_es_summary(es_config):
    """打印 Elasticsearch 导入汇总统计，按月维度展示告警和事件"""
    try:
        host = es_config['host']
        port = es_config.get('port', 9200)
        user = es_config['user']
        password = es_config['password']
        use_ssl = es_config.get('use_ssl', True)

        scheme = 'https' if use_ssl else 'http'
        base_url = f'{scheme}://{host}:{port}'

        http = urllib3.PoolManager(cert_reqs='CERT_NONE', assert_hostname=False)
        headers = urllib3.make_headers(basic_auth=f'{user}:{password}')

        # 获取所有索引信息
        response = http.request(
            'GET',
            f'{base_url}/_cat/indices?format=json&expand_wildcards=all',
            headers=headers,
        )
        indices = json.loads(response.data.decode())

        # 按索引类型归类
        asset_docs = 0
        fingerprint_docs = 0
        asset_his_docs = 0
        alarm_by_month = {}
        event_by_month = {}
        other_docs = 0

        for idx in indices:
            name = idx['index']
            count = int(idx.get('docs.count', 0))
            if name == 'xdr_asset':
                asset_docs = count
            elif name == 'xdr_asset_fingerprint':
                fingerprint_docs = count
            elif name == 'xdr_asset_his':
                asset_his_docs = count
            elif name.startswith('maxs_alarm_'):
                month = name.replace('maxs_alarm_', '')
                alarm_by_month[month] = alarm_by_month.get(month, 0) + count
            elif name.startswith('maxs_event_'):
                month = name.replace('maxs_event_', '')
                event_by_month[month] = event_by_month.get(month, 0) + count

        total = asset_docs + fingerprint_docs + asset_his_docs + sum(alarm_by_month.values()) + sum(event_by_month.values())

        print_info("\n" + "=" * 60)
        print_info("📊 Elasticsearch 导入汇总统计")
        print_info("=" * 60)
        print_info(f"  资产信息      (xdr_asset)             : {asset_docs:>8,} docs")
        print_info(f"  指纹信息      (xdr_asset_fingerprint) : {fingerprint_docs:>8,} docs")
        print_info(f"  历史信息      (xdr_asset_his)         : {asset_his_docs:>8,} docs")

        if alarm_by_month:
            print_info(f"  ── 告警信息 (maxs_alarm_*) 按月分布 ──")
            for month in sorted(alarm_by_month.keys()):
                print_info(f"    {month} : {alarm_by_month[month]:>8,} docs")
            print_info(f"    合计      : {sum(alarm_by_month.values()):>8,} docs")

        if event_by_month:
            print_info(f"  ── 事件信息 (maxs_event_*) 按月分布 ──")
            for month in sorted(event_by_month.keys()):
                print_info(f"    {month} : {event_by_month[month]:>8,} docs")
            print_info(f"    合计      : {sum(event_by_month.values()):>8,} docs")

        print_info("  " + "─" * 48)
        print_info(f"  ES 总计                                 : {total:>8,} docs")

    except Exception as e:
        print_error(f"  ES 统计查询失败: {e}")


@cli.group()
def config():
    """Manage configuration"""
    pass


@config.command()
@click.option('--output', '-o', default=None, help='Output file path (prints to stdout if not specified)')
def init(output):
    """Generate a configuration template

    Generates a default config template with placeholder values.
    Use --output to write to a file, or redirect stdout to a file.
    """
    template = """# AIXDR Data Exporter Configuration
# ========================================
# Please modify the values below to match your environment.
# Remove any sections you don't need (e.g., es_source/es_target for MySQL only).

# MySQL Source Database (export from)
source:
  host: 10.21.19.99
  port: 3306
  user: root
  password: your_password
  database: SSA

# MySQL Target Database (import to - use either this or pg_target, not both)
target:
  host: 192.168.113.40
  port: 3306
  user: root
  password: your_password
  database: SSA

# PostgreSQL Target Database (import to - use either this or target, not both)
# pg_target:
#   host: localhost
#   port: 5432
#   user: postgres
#   password: your_password
#   database: aixdr

# Elasticsearch Source (export from)
es_source:
  host: 10.21.19.99
  port: 9200
  user: elastic
  password: your_password
  use_ssl: true

# Elasticsearch Target (import to)
es_target:
  host: 192.168.113.40
  port: 9200
  user: elastic
  password: your_password
  use_ssl: true

# Asset IDs to export
assets:
  - 2019154309520072744

# ES index configuration
es_indices:
  asset: xdr_asset
  fingerprint: xdr_asset_fingerprint
  asset_his: xdr_asset_his
  alarm_pattern: maxs_alarm_
  event_pattern: maxs_event_
  index_cycles: [202605, 202604, 202603, 202602, 202601]

# ES export directory
es_export:
  output_dir: ./exports/es_latest/
  size_per_batch: 1000

# Export output file (SQL for MySQL)
export:
  output: ./exports/assets_export.sql

# Import input file (SQL for MySQL/PostgreSQL)
import:
  input: ./exports/assets_export.sql

# Enable verification after import
verify:
  enabled: true
"""
    if output:
        try:
            output_dir = os.path.dirname(output)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            with open(output, 'w', encoding='utf-8') as f:
                f.write(template)
            click.echo(f"✓ Configuration template written to: {output}")
        except Exception as e:
            click.echo(f"✗ Failed to write config file: {e}", err=True)
    else:
        click.echo(template)


if __name__ == '__main__':
    cli()

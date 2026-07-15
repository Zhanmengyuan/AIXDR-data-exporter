"""Configuration Management Module"""

import os
import yaml
from datetime import datetime
from typing import Optional, Tuple, Dict, Any


class ConfigManager:
    """Unified configuration management"""

    @staticmethod
    def load_config(config_file: str) -> Optional[Dict[str, Any]]:
        """Load configuration from YAML file"""
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Config file not found: {config_file}")

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            raise RuntimeError(f"Error loading config: {e}")

    @staticmethod
    def validate_source_config(cfg: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate source database configuration"""
        if not cfg:
            return False, "Config is empty"

        source = cfg.get('source', {})
        required_fields = ['host', 'user', 'password', 'database']

        missing = [f for f in required_fields if not source.get(f)]
        if missing:
            return False, f"Missing source fields: {', '.join(missing)}"

        return True, "Source config is valid"

    @staticmethod
    def validate_target_config(cfg: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate target database configuration (MySQL or PostgreSQL)"""
        if not cfg:
            return False, "Config is empty"

        # Check for either target (MySQL) or pg_target (PostgreSQL)
        if cfg.get('target'):
            target = cfg.get('target', {})
            db_type = 'MySQL'
        elif cfg.get('pg_target'):
            target = cfg.get('pg_target', {})
            db_type = 'PostgreSQL'
        else:
            return False, "No target or pg_target configuration found"

        required_fields = ['host', 'user', 'password', 'database']

        missing = [f for f in required_fields if not target.get(f)]
        if missing:
            return False, f"Missing {db_type} target fields: {', '.join(missing)}"

        return True, f"{db_type} target config is valid"

    @staticmethod
    def validate_pg_target_config(cfg: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate PostgreSQL target configuration"""
        if not cfg:
            return False, "Config is empty"

        pg_target = cfg.get('pg_target', {})
        required_fields = ['host', 'user', 'password', 'database']

        missing = [f for f in required_fields if not pg_target.get(f)]
        if missing:
            return False, f"Missing pg_target fields: {', '.join(missing)}"

        return True, "PostgreSQL target config is valid"

    @staticmethod
    def validate_pg_source_config(cfg: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate PostgreSQL source configuration"""
        if not cfg:
            return False, "Config is empty"

        pg_source = cfg.get('pg_source', {})
        required_fields = ['host', 'user', 'password', 'database']

        missing = [f for f in required_fields if not pg_source.get(f)]
        if missing:
            return False, f"Missing pg_source fields: {', '.join(missing)}"

        return True, "PostgreSQL source config is valid"

    @staticmethod
    def validate_es_source_config(cfg: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate Elasticsearch source configuration"""
        if not cfg:
            return False, "Config is empty"

        es_source = cfg.get('es_source', {})
        required_fields = ['host', 'user', 'password']

        missing = [f for f in required_fields if not es_source.get(f)]
        if missing:
            return False, f"Missing es_source fields: {', '.join(missing)}"

        return True, "ES source config is valid"

    @staticmethod
    def validate_es_target_config(cfg: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate Elasticsearch target configuration"""
        if not cfg:
            return False, "Config is empty"

        es_target = cfg.get('es_target', {})
        required_fields = ['host', 'user', 'password']

        missing = [f for f in required_fields if not es_target.get(f)]
        if missing:
            return False, f"Missing es_target fields: {', '.join(missing)}"

        return True, "ES target config is valid"

    @staticmethod
    def extract_source_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Extract source database config"""
        source = cfg.get('source', {})
        return {
            'host': source.get('host'),
            'user': source.get('user'),
            'password': source.get('password'),
            'database': source.get('database'),
            'port': source.get('port', 3306),
        }

    @staticmethod
    def extract_target_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Extract target database config (MySQL or PostgreSQL)"""
        # Check for pg_target first
        if cfg.get('pg_target'):
            pg_target = cfg.get('pg_target', {})
            return {
                'host': pg_target.get('host'),
                'user': pg_target.get('user'),
                'password': pg_target.get('password'),
                'database': pg_target.get('database'),
                'port': pg_target.get('port', 5432),
                'type': 'postgresql',
            }
        # Fallback to regular target (MySQL)
        target = cfg.get('target', {})
        return {
            'host': target.get('host'),
            'user': target.get('user'),
            'password': target.get('password'),
            'database': target.get('database'),
            'port': target.get('port', 3306),
            'type': 'mysql',
        }

    @staticmethod
    def extract_pg_target_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Extract PostgreSQL target config"""
        pg_target = cfg.get('pg_target', {})
        return {
            'host': pg_target.get('host'),
            'user': pg_target.get('user'),
            'password': pg_target.get('password'),
            'database': pg_target.get('database'),
            'port': pg_target.get('port', 5432),
        }

    @staticmethod
    def extract_pg_source_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Extract PostgreSQL source config"""
        pg_source = cfg.get('pg_source', {})
        return {
            'host': pg_source.get('host'),
            'user': pg_source.get('user'),
            'password': pg_source.get('password'),
            'database': pg_source.get('database'),
            'port': pg_source.get('port', 5432),
        }

    @staticmethod
    def extract_es_source_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Extract Elasticsearch source config"""
        es_source = cfg.get('es_source', {})
        return {
            'host': es_source.get('host'),
            'user': es_source.get('user'),
            'password': es_source.get('password'),
            'port': es_source.get('port', 9200),
            'use_ssl': es_source.get('use_ssl', True),
        }

    @staticmethod
    def extract_es_target_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Extract Elasticsearch target config"""
        es_target = cfg.get('es_target', {})
        return {
            'host': es_target.get('host'),
            'user': es_target.get('user'),
            'password': es_target.get('password'),
            'port': es_target.get('port', 9200),
            'use_ssl': es_target.get('use_ssl', True),
        }

    @staticmethod
    def extract_asset_ids(cfg: Dict[str, Any]) -> Optional[list]:
        """Extract asset IDs from config
        Supports multiple formats:
        - YAML list:  assets:\n  - 201737...
        - YAML inline: assets: [201737..., 201915...]
        - Comma-separated string: assets: \"201737..., 201915...\"
        """
        assets = cfg.get('assets', None)
        if assets is None:
            return None
        if isinstance(assets, str):
            return [a.strip() for a in assets.split(',') if a.strip()]
        if isinstance(assets, list):
            return assets
        return None

    @staticmethod
    def extract_table_list(cfg: Dict[str, Any]) -> Optional[list]:
        """Extract table list from config"""
        export_cfg = cfg.get('export', {})
        tables = export_cfg.get('tables', None)
        if isinstance(tables, str):
            return [t.strip() for t in tables.split(',')]
        return tables

    @staticmethod
    def extract_export_output(cfg: Dict[str, Any]) -> str:
        """Extract export output path"""
        export_cfg = cfg.get('export', {})
        return export_cfg.get('output', './export.sql')

    @staticmethod
    def extract_import_input(cfg: Dict[str, Any]) -> str:
        """Extract import input path"""
        import_cfg = cfg.get('import', {})
        return import_cfg.get('input', './export.sql')

    @staticmethod
    def extract_es_export_output(cfg: Dict[str, Any]) -> str:
        """Extract ES export output directory"""
        es_export = cfg.get('es_export', {})
        return es_export.get('output_dir', './exports/es_{timestamp}/')

    @staticmethod
    def extract_es_indices(cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Extract ES indices configuration"""
        es_indices = cfg.get('es_indices', {})
        return {
            'asset': es_indices.get('asset', 'xdr_asset'),
            'fingerprint': es_indices.get('fingerprint', 'xdr_asset_fingerprint'),
            'asset_his': es_indices.get('asset_his', 'xdr_asset_his'),
            'alarm_pattern': es_indices.get('alarm_pattern', 'maxs_alarm_'),
            'event_pattern': es_indices.get('event_pattern', 'maxs_event_'),
            'index_cycles': es_indices.get('index_cycles', []),
        }

    @staticmethod
    def extract_batch_size(cfg: Dict[str, Any]) -> int:
        """Extract ES batch size"""
        es_export = cfg.get('es_export', {})
        return es_export.get('size_per_batch', 1000)

    @staticmethod
    def is_verify_enabled(cfg: Dict[str, Any]) -> bool:
        """Check if verification is enabled"""
        verify = cfg.get('verify', {})
        return verify.get('enabled', True)

    @staticmethod
    def resolve_output_path(output_path: str) -> str:
        """Replace {timestamp} placeholder with current timestamp"""
        if '{timestamp}' in output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = output_path.replace('{timestamp}', timestamp)
        return output_path

    @staticmethod
    def get_source_type(cfg: Dict[str, Any], source_param: Optional[str] = None) -> str:
        """Detect or get source type from config"""
        if source_param:
            return source_param

        # Try to detect from config
        if cfg.get('source'):
            return 'mysql'
        elif cfg.get('pg_source'):
            return 'postgresql'
        elif cfg.get('es_source'):
            return 'es'

        raise ValueError("Cannot determine source type from config")

    @staticmethod
    def get_target_type(cfg: Dict[str, Any], target_param: Optional[str] = None) -> str:
        """Detect or get target type from config"""
        if target_param:
            return target_param

        # Try to detect from config
        if cfg.get('pg_target'):
            return 'postgresql'
        elif cfg.get('target'):
            return 'mysql'
        elif cfg.get('es_target'):
            return 'es'

        raise ValueError("Cannot determine target type from config")

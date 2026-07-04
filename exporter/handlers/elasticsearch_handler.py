"""Elasticsearch Data Handler"""

import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from .base_handler import DataHandler
from ..elasticsearch_exporter import ElasticsearchExporter, ElasticsearchImporter


class ElasticsearchHandler(DataHandler):
    """Handler for Elasticsearch operations"""

    def export(
        self,
        config: Dict[str, Any],
        asset_ids: Optional[List[int]] = None,
        table_list: Optional[List[str]] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Export data from Elasticsearch

        Args:
            config: ES config (host, user, password, port, use_ssl)
            asset_ids: Asset IDs to export (required)
            table_list: Indices pattern list (optional, uses default if not provided)
            output_path: Output directory path (template with {timestamp})

        Returns:
            str: Path to export directory
        """
        if not asset_ids:
            raise ValueError("asset_ids is required for ES export")

        if not output_path:
            output_path = f'./exports/es_{datetime.now().strftime("%Y%m%d_%H%M%S")}/'

        # Replace {timestamp} in path
        if '{timestamp}' in output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = output_path.replace('{timestamp}', timestamp)

        # Create output directory
        os.makedirs(output_path, exist_ok=True)

        # Clean old NDJSON files to prevent duplicate data
        for ndjson_file in ["es_asset.ndjson", "es_fingerprint.ndjson", "es_asset_his.ndjson", "es_alarms.ndjson", "es_events.ndjson"]:
            file_path = os.path.join(output_path, ndjson_file)
            if os.path.exists(file_path):
                os.remove(file_path)

        print(f"ℹ Exporting from ES: {config['host']}:{config.get('port', 9200)}")
        print(f"ℹ Asset IDs: {asset_ids}")
        print(f"ℹ Output directory: {output_path}")

        try:
            es_exporter = ElasticsearchExporter(
                host=config['host'],
                user=config['user'],
                password=config['password'],
                port=config.get('port', 9200),
                use_ssl=config.get('use_ssl', True),
            )

            total_exported = 0

            # Export asset data
            asset_output = os.path.join(output_path, "es_asset.ndjson")
            count = es_exporter.export_asset(asset_ids, asset_output)
            total_exported += count
            print(f"ℹ xdr_asset: {count} docs")

            # Export fingerprint
            fp_output = os.path.join(output_path, "es_fingerprint.ndjson")
            count = es_exporter.export_fingerprint(asset_ids, fp_output)
            total_exported += count
            print(f"ℹ xdr_asset_fingerprint: {count} docs")

            # Export asset_his
            his_output = os.path.join(output_path, "es_asset_his.ndjson")
            count = es_exporter.export_asset_his(asset_ids, his_output)
            total_exported += count
            print(f"ℹ xdr_asset_his: {count} docs")

            # Export alarms (if index_cycles provided in table_list)
            index_cycles = []
            if isinstance(table_list, dict) and 'index_cycles' in table_list:
                index_cycles = table_list['index_cycles']

            if index_cycles:
                alarm_output = os.path.join(output_path, "es_alarms.ndjson")
                count = es_exporter.export_alarms_by_asset_ids(asset_ids, index_cycles, alarm_output)
                total_exported += count
                print(f"ℹ maxs_alarm_* (cycles {index_cycles}): {count} docs")

                # Export events
                event_output = os.path.join(output_path, "es_events.ndjson")
                count = es_exporter.export_events_by_asset_ids(asset_ids, index_cycles, event_output)
                total_exported += count
                print(f"ℹ maxs_event_* (cycles {index_cycles}): {count} docs")

            es_exporter.close()
            print(f"✓ Export completed: {total_exported} total docs")

            return output_path

        except Exception as e:
            raise RuntimeError(f"ES export failed: {e}")

    def import_data(
        self,
        config: Dict[str, Any],
        input_path: str,
        drop_tables: bool = False,
        asset_ids: Optional[List[int]] = None,
    ) -> bool:
        """
        Import data to Elasticsearch

        Args:
            config: ES config (host, user, password, port, use_ssl)
            input_path: Input directory path (containing .ndjson files)
            drop_tables: Ignored for ES (not applicable)
            asset_ids: Ignored for ES (ES uses document ID for updates)

        Returns:
            bool: True if successful
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input path not found: {input_path}")

        print(f"ℹ Importing to ES: {config['host']}:{config.get('port', 9200)}")
        print(f"ℹ Input directory: {input_path}")

        try:
            es_importer = ElasticsearchImporter(
                host=config['host'],
                user=config['user'],
                password=config['password'],
                port=config.get('port', 9200),
                use_ssl=config.get('use_ssl', True),
            )

            total_imported = 0

            # Import all NDJSON files
            ndjson_files = [
                "es_asset.ndjson",
                "es_fingerprint.ndjson",
                "es_asset_his.ndjson",
                "es_alarms.ndjson",
                "es_events.ndjson",
            ]

            for ndjson_file in ndjson_files:
                full_path = os.path.join(input_path, ndjson_file)
                if os.path.exists(full_path) and os.path.getsize(full_path) > 0:
                    count = es_importer.import_bulk(full_path)
                    total_imported += count
                    print(f"ℹ {ndjson_file}: {count} docs")
                else:
                    print(f"ℹ {ndjson_file}: empty or not found, skipping")

            es_importer.close()
            print(f"✓ Import completed: {total_imported} total docs")

            return True

        except Exception as e:
            raise RuntimeError(f"ES import failed: {e}")

    def verify(
        self,
        config: Dict[str, Any],
        expected_tables: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Verify data in Elasticsearch

        Note: ES verification is limited - just checking connection
        Full verification would require comparing source and target indices

        Args:
            config: ES config
            expected_tables: Ignored for ES

        Returns:
            dict: Simple verification result
        """
        try:
            es_exporter = ElasticsearchExporter(
                host=config['host'],
                user=config['user'],
                password=config['password'],
                port=config.get('port', 9200),
                use_ssl=config.get('use_ssl', True),
            )
            es_exporter.close()

            print("✓ ES cluster is accessible")
            return {
                'all_valid': True,
                'message': 'ES cluster connection verified',
            }
        except Exception as e:
            print(f"✗ ES verification failed: {e}")
            return {
                'all_valid': False,
                'message': str(e),
            }

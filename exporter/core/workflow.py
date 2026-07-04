"""Workflow Management Module"""

from typing import Optional, List, Dict, Any
from .config_manager import ConfigManager
from .operation import ExportOperation, ImportOperation, ExportImportOperation


class Workflow:
    """Unified workflow orchestration"""

    @staticmethod
    def execute_export(
        handler,
        config: Dict[str, Any],
        mode: str = 'tables',
        asset_ids: Optional[List[int]] = None,
        table_list: Optional[List[str]] = None,
        output_path: Optional[str] = None,
    ) -> bool:
        """Execute export workflow"""
        operation = ExportOperation(
            handler=handler,
            config=config,
            mode=mode,
            asset_ids=asset_ids,
            table_list=table_list,
            output_path=output_path,
        )
        return operation.execute()

    @staticmethod
    def execute_import(
        handler,
        config: Dict[str, Any],
        input_path: str,
        drop_tables: bool = False,
        asset_ids: Optional[List[int]] = None,
    ) -> bool:
        """Execute import workflow"""
        operation = ImportOperation(
            handler=handler,
            config=config,
            input_path=input_path,
            drop_tables=drop_tables,
            asset_ids=asset_ids,
        )
        return operation.execute()

    @staticmethod
    def execute_export_import(
        export_handler,
        import_handler,
        source_config: Dict[str, Any],
        target_config: Dict[str, Any],
        mode: str = 'tables',
        asset_ids: Optional[List[int]] = None,
        table_list: Optional[List[str]] = None,
        temp_file: Optional[str] = None,
        verify_enabled: bool = True,
    ) -> bool:
        """Execute export + import workflow"""
        operation = ExportImportOperation(
            export_handler=export_handler,
            import_handler=import_handler,
            source_config=source_config,
            target_config=target_config,
            mode=mode,
            asset_ids=asset_ids,
            table_list=table_list,
            temp_file=temp_file,
            verify_enabled=verify_enabled,
        )
        return operation.execute()

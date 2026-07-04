"""Base Data Handler Interface"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class DataHandler(ABC):
    """Abstract base class for data handlers"""

    @abstractmethod
    def export(
        self,
        config: Dict[str, Any],
        asset_ids: Optional[List[int]] = None,
        table_list: Optional[List[str]] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Export data from source

        Args:
            config: Source configuration
            asset_ids: Asset IDs to export (optional)
            table_list: Table names to export (optional)
            output_path: Output file path

        Returns:
            str: Path to exported file
        """
        pass

    @abstractmethod
    def import_data(
        self,
        config: Dict[str, Any],
        input_path: str,
        drop_tables: bool = False,
    ) -> bool:
        """
        Import data to target

        Args:
            config: Target configuration
            input_path: Input file path
            drop_tables: Whether to drop tables before import

        Returns:
            bool: True if import successful
        """
        pass

    @abstractmethod
    def verify(
        self,
        config: Dict[str, Any],
        expected_tables: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Verify data in target

        Args:
            config: Target configuration
            expected_tables: Expected table names to verify

        Returns:
            dict: Verification results
        """
        pass

"""AIXDR Data Exporter Package"""

from .mysql_exporter import MySQLExporter
from .mysql_importer import MySQLImporter
from .postgresql_importer import PostgreSQLImporter
from .sql_converter import MySQLToPostgreSQLConverter
from .data_validator import DataValidator
from .related_tables_exporter import RelatedTablesExporter
from .elasticsearch_exporter import ElasticsearchExporter, ElasticsearchImporter

# Core components
from .core import (
    ConfigManager,
    Operation,
    ExportOperation,
    ImportOperation,
    ExportImportOperation,
    Workflow,
)

# Handlers
from .handlers import (
    DataHandler,
    MySQLHandler,
    PostgreSQLHandler,
    ElasticsearchHandler,
)

__version__ = "1.2.0"
__all__ = [
    "MySQLExporter",
    "MySQLImporter",
    "PostgreSQLImporter",
    "MySQLToPostgreSQLConverter",
    "DataValidator",
    "RelatedTablesExporter",
    "ElasticsearchExporter",
    "ElasticsearchImporter",
    # Core
    "ConfigManager",
    "Operation",
    "ExportOperation",
    "ImportOperation",
    "ExportImportOperation",
    "Workflow",
    # Handlers
    "DataHandler",
    "MySQLHandler",
    "PostgreSQLHandler",
    "ElasticsearchHandler",
]

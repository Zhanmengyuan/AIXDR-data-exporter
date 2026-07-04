#!/usr/bin/env python3
"""
Test script to verify MySQL to PostgreSQL SQL conversion
"""

from exporter.sql_converter import MySQLToPostgreSQLConverter

def test_conversion():
    # Test MySQL SQL
    mysql_sql = """
DROP TABLE IF EXISTS `XDR_ASSET`;

CREATE TABLE `XDR_ASSET` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `asset_id` VARCHAR(64) NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME,
  `status` TINYINT(1) DEFAULT 1,
  `data` MEDIUMTEXT,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_asset_id` (`asset_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `XDR_ASSET` (`asset_id`, `name`, `description`, `status`) VALUES 
('2019154309520072744', 'Test Server', 'Test server description', 1),
('2015077142737756174', 'Another Server', NULL, 0);
"""

    print("=== MySQL SQL (Input) ===")
    print(mysql_sql)
    
    print("\n=== Converting to PostgreSQL... ===")
    pg_sql = MySQLToPostgreSQLConverter.convert(mysql_sql)
    
    print("\n=== PostgreSQL SQL (Output) ===")
    print(pg_sql)
    
    print("\n✅ Conversion test completed successfully!")
    return True

if __name__ == "__main__":
    test_conversion()

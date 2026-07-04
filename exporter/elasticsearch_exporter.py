"""Elasticsearch Data Exporter"""

import json
import os
from datetime import datetime
from typing import List, Optional, Set
from elasticsearch import Elasticsearch


class ElasticsearchExporter:
    def __init__(self, host: str, user: str, password: str, port: int = 9200, use_ssl: bool = True):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.use_ssl = use_ssl

        scheme = "https" if use_ssl else "http"
        self.client = Elasticsearch(
            [f"{scheme}://{host}:{port}"],
            basic_auth=(user, password),
            verify_certs=False,
            request_timeout=60
        )

        if not self.client.ping():
            raise ConnectionError(f"Cannot connect to Elasticsearch at {host}:{port}")

    def export_asset(self, asset_ids: List[str], output_file: str) -> int:
        index = "xdr_asset"
        total = 0

        for asset_id in asset_ids:
            query = {
                "query": {
                    "term": {"ASSET_ID": asset_id}
                },
                "size": 10000
            }

            count, docs = self._scroll_search(index, query)
            if docs:
                with open(output_file, 'a', encoding='utf-8') as f:
                    for doc in docs:
                        f.write(json.dumps({"index": {"_index": index, "_id": doc["_id"]}}, ensure_ascii=False) + "\n")
                        f.write(json.dumps(doc["_source"], ensure_ascii=False) + "\n")
                total += count
                print(f"  {index}: exported {count} docs for asset_id={asset_id}")

        return total

    def export_fingerprint(self, asset_ids: List[str], output_file: str) -> int:
        index = "xdr_asset_fingerprint"
        total = 0

        for asset_id in asset_ids:
            query = {
                "query": {
                    "term": {"ASSET_ID": asset_id}
                },
                "size": 10000
            }

            count, docs = self._scroll_search(index, query)
            if docs:
                with open(output_file, 'a', encoding='utf-8') as f:
                    for doc in docs:
                        f.write(json.dumps({"index": {"_index": index, "_id": doc["_id"]}}, ensure_ascii=False) + "\n")
                        f.write(json.dumps(doc["_source"], ensure_ascii=False) + "\n")
                total += count
                print(f"  {index}: exported {count} docs for asset_id={asset_id}")

        return total

    def export_asset_his(self, asset_ids: List[str], output_file: str) -> int:
        index = "xdr_asset_his"
        total = 0

        for asset_id in asset_ids:
            query = {
                "query": {
                    "term": {"ASSET_ID": asset_id}
                },
                "size": 10000
            }

            if not self._index_exists(index):
                print(f"  {index}: does not exist, skipping")
                continue

            count, docs = self._scroll_search(index, query)
            if docs:
                with open(output_file, 'a', encoding='utf-8') as f:
                    for doc in docs:
                        f.write(json.dumps({"index": {"_index": index, "_id": doc["_id"]}}, ensure_ascii=False) + "\n")
                        f.write(json.dumps(doc["_source"], ensure_ascii=False) + "\n")
                total += count
                print(f"  {index}: exported {count} docs for asset_id={asset_id}")

        return total

    def export_alarms_by_asset_ids(self, asset_ids: List[str], index_cycles: List[str], output_file: str) -> int:
        total = 0

        for suffix in index_cycles:
            index = f"maxs_alarm_{suffix}"
            if not self._index_exists(index):
                print(f"  {index}: does not exist, skipping")
                continue

            count = self._export_nested(index, "AFFECTED_ASSET_INFO", "ASSET_ID", asset_ids, output_file)
            total += count
            print(f"  {index}: exported {count} docs")

        return total

    def export_events_by_asset_ids(self, asset_ids: List[str], index_cycles: List[str], output_file: str) -> int:
        total = 0

        for suffix in index_cycles:
            index = f"maxs_event_{suffix}"
            if not self._index_exists(index):
                print(f"  {index}: does not exist, skipping")
                continue

            count = self._export_nested(index, "AFFECTED_ASSET_INFO", "ASSET_ID", asset_ids, output_file)
            total += count
            print(f"  {index}: exported {count} docs")

        return total

    def _export_nested(self, index: str, nested_path: str, nested_field: str, asset_ids: List[str], output_file: str) -> int:
        query = {
            "query": {
                "nested": {
                    "path": nested_path,
                    "query": {
                        "terms": {
                            f"{nested_path}.{nested_field}": asset_ids
                        }
                    }
                }
            },
            "size": 10000
        }

        count, docs = self._scroll_search(index, query)
        if docs:
            with open(output_file, 'a', encoding='utf-8') as f:
                for doc in docs:
                    f.write(json.dumps({"index": {"_index": index, "_id": doc["_id"]}}, ensure_ascii=False) + "\n")
                    f.write(json.dumps(doc["_source"], ensure_ascii=False) + "\n")

        return count

    def _scroll_search(self, index: str, query: dict) -> tuple:
        count = 0
        docs = []

        try:
            response = self.client.search(index=index, body=query, scroll="2m")
            scroll_id = response["_scroll_id"]
            hits = response["hits"]["hits"]

            while hits:
                docs.extend(hits)
                count += len(hits)
                response = self.client.scroll(scroll_id=scroll_id, scroll="2m")
                scroll_id = response["_scroll_id"]
                hits = response["hits"]["hits"]

            self.client.clear_scroll(scroll_id=scroll_id)
        except Exception as e:
            print(f"    Warning: error scanning {index}: {e}")

        return count, docs

    def _index_exists(self, index: str) -> bool:
        try:
            return self.client.indices.exists(index=index)
        except Exception:
            return False

    def close(self):
        self.client.close()


class ElasticsearchImporter:
    def __init__(self, host: str, user: str, password: str, port: int = 9200, use_ssl: bool = True):
        import requests
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.use_ssl = use_ssl
        self.session = requests.Session()
        self.session.auth = (user, password)
        self.session.verify = False
        self.session.headers.update({"Content-Type": "application/x-ndjson"})
        scheme = "https" if use_ssl else "http"
        self.base_url = f"{scheme}://{host}:{port}"

        try:
            resp = self.session.get(f"{self.base_url}")
            if resp.status_code != 200:
                raise ConnectionError(f"Cannot connect to ES at {host}:{port}, status: {resp.status_code}")
        except Exception as e:
            raise ConnectionError(f"Cannot connect to Elasticsearch at {host}:{port}: {e}")

    def _convert_time_fields(self, doc: dict) -> dict:
        """转换时间字段格式，解决类型不匹配问题"""
        # 需要转换的时间字段列表
        time_fields = [
            'ASSESSMENT_TIME',
            'CREATE_TIME',
            'UPDATE_TIME',
            'REGISTER_TIME',
            'LAST_ONLINE_TIME'
        ]
        
        for field in time_fields:
            if field in doc and isinstance(doc[field], str):
                try:
                    # 尝试将字符串格式的时间转换为时间戳（毫秒）
                    from datetime import datetime
                    # 尝试多种可能的时间格式
                    dt = None
                    for fmt in [
                        '%Y-%m-%d %H:%M:%S',
                        '%Y-%m-%dT%H:%M:%S',
                        '%Y-%m-%d %H:%M:%S.%f'
                    ]:
                        try:
                            dt = datetime.strptime(doc[field], fmt)
                            break
                        except ValueError:
                            continue
                    
                    if dt:
                        # 转换为毫秒级时间戳
                        timestamp = int(dt.timestamp() * 1000)
                        doc[field] = timestamp
                except Exception:
                    # 如果转换失败，保持原样
                    pass
        return doc

    def import_bulk(self, ndjson_file: str) -> int:
        if not os.path.exists(ndjson_file) or os.path.getsize(ndjson_file) == 0:
            print(f"  File is empty or not found: {ndjson_file}, skipping")
            return 0

        # 读取并转换数据
        processed_lines = []
        with open(ndjson_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    # 如果是文档数据（不是 action 行），则进行字段转换
                    if 'index' not in data:
                        data = self._convert_time_fields(data)
                    processed_lines.append(json.dumps(data, ensure_ascii=False))
                except Exception as e:
                    processed_lines.append(line)

        content = '\n'.join(processed_lines) + '\n'
        content_bytes = content.encode('utf-8')

        if not content.strip():
            print(f"  File is empty: {ndjson_file}, skipping")
            return 0

        first_line = processed_lines[0] if processed_lines else ''
        index_name = 'unknown'
        if first_line:
            try:
                action = json.loads(first_line)
                if 'index' in action:
                    index_name = action['index'].get('_index', 'unknown')
                elif '_index' in action:
                    index_name = action.get('_index', 'unknown')
            except:
                index_name = 'unknown'

        url = f"{self.base_url}/_bulk?refresh"
        resp = self.session.post(url, data=content_bytes, timeout=120)

        if resp.status_code != 200:
            try:
                error_detail = resp.json()
            except:
                error_detail = resp.text[:500]

            error_msg = error_detail.get('error', {}).get('reason', str(error_detail))
            print(f"    Bulk import failed (HTTP {resp.status_code}): {error_msg[:200]}")
            return 0

        result = resp.json()
        errors = result.get('errors', False)
        items = result.get('items', [])

        failed = sum(1 for item in items if 'error' in item.get('index', {}))
        succeeded = len(items) - failed

        if failed > 0:
            print(f"    {succeeded} succeeded, {failed} failed")
            first_error = next((item['index'].get('error', {}) for item in items if 'error' in item.get('index', {})), None)
            if first_error:
                reason = first_error.get('reason', str(first_error))[:100]
                print(f"    First error: {reason}")

        print(f"  Imported {succeeded} documents from {ndjson_file}")
        return succeeded

    def close(self):
        self.session.close()

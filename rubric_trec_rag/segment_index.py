from typing import Optional, List
from pathlib import Path
import duckdb

class SegmentIndex:
    def __init__(self, fname: Path):
        self.conn = duckdb.connect(database=str(fname), read_only=True)

    def lookup(self, docid: str) -> Optional[str]:
        '''Given docid, return the `text` of the corpus'''
        self.conn.execute('select segment from segments where docid=?', [docid])
        doc = self.conn.fetchone()
        return doc[0] if doc else None


def build_segment_index(out: Path, inputs: List[Path]):
    out.unlink(missing_ok=True)

    conn = duckdb.connect(database=str(out))
    conn.execute('''
        create table segments as select * from read_ndjson_auto(?, compression="gzip", records="true");
    ''', [[str(x) for x in inputs]])
    conn.execute('''
        create unique index segments_docid_idx on segments(docid)
    ''')
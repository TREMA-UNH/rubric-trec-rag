
from . import segment_index
import pathlib


if __name__ == "__main__":

    import argparse

    desc = f'''Convert TREC RAG segment corpus to DuckDB database. \n
             '''
    
    parser = argparse.ArgumentParser(description="Convert TREC RAG segment data DuckDB database."
                                   , epilog=desc
                                   , formatter_class=argparse.RawDescriptionHelpFormatter
                                   )

    parser.add_argument('--out', type=pathlib.Path, metavar='msmarco.duckdb'
                        , help='duckdb database with segments from the TREC RAG corpus'
                        )

    parser.add_argument(dest='rag_corpus', nargs='+', type=pathlib.Path, metavar='xxx.jsonl.gz'
                        , help='input json file with corpus from the TREC RAG corpus'
                        )

    args = parser.parse_args()  
    
    segment_files_str = "\n".join([p.name for p in args.rag_corpus])  #info
    print(f'Indexing RAG corpus from segment files: \n {segment_files_str}')
    segment_index.build_segment_index(out=args.out, inputs=args.rag_corpus)
    print(f"DuckDB index written to {args.out}")

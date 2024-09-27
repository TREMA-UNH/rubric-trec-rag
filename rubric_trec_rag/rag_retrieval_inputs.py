from collections import defaultdict
import itertools
import json
from pathlib import Path
from typing import Dict, List, Optional, Iterator, Set



from exam_pp.data_model import FullParagraphData, ParagraphData, ParagraphRankingEntry, QueryWithFullParagraphList, writeQueryWithFullParagraphs
from . import segment_index



def read_rag_run_file(run_in_files:List[Path]) ->Iterator[ParagraphRankingEntry]:
    '''Use to read TREC RAG run/retrieval file'''
    # run_entries:List[ParagraphRankingEntry] = list()

    for run_in_file in run_in_files:
        print(f"Loading retrieval run from {run_in_file}")
        with open(run_in_file, 'rt') as file:
            for line in file.readlines():
                splits = line.split(" ")
                run_entry=None
                if len(splits)>=6:
                    run_entry = ParagraphRankingEntry(queryId=splits[0].strip(), paragraphId=splits[2].strip(), rank=int(splits[3].strip()), score=float(splits[4].strip()), method=splits[5].strip())
                else:
                    raise RuntimeError(f"All lines in run file needs to contain six columns to be complete. Offending line: \"{line}\"")
                
                # iterator version of `run_entries.append(run_entry)`
                yield run_entry

def read_rag_query_file(query_file:Path, max_queries:Optional[int]=None) -> Dict[str,str]:
    with open(query_file, 'rt') as file:
        query_dict = dict()
        for line in itertools.islice(file.readlines(), max_queries):
            splits = line.split("\t")
            if len(splits)>=2:
                query_dict[splits[0].strip()]=splits[1].strip()
            else:
                raise RuntimeError(f"each line in query file {query_file} must contain two tab-separated columns. Offending line: \"{line}\"")

    return query_dict



def write_query_file(file_path:Path, queries:Dict[str,str])->None:
    with open(file_path, 'wt', encoding='utf-8') as file:
        json.dump(obj=queries,fp=file)



def convert_paragraphs(input_runs_by_qid:Dict[str,List[ParagraphRankingEntry]], query_set:Dict[str,str], corpus_db: segment_index.SegmentIndex)-> List[QueryWithFullParagraphList]:
    rubric_data:List[QueryWithFullParagraphList] = list()

    for query_id, query_str in query_set.items():
        paragraphs:List[FullParagraphData] = list()
        print(f'Converting {len(input_runs_by_qid[query_id])} paragraphs for query {query_id}...')
        grouped_entries = defaultdict(list)
        for run_entry in input_runs_by_qid[query_id]:
            grouped_entries[run_entry.paragraphId].append(run_entry)
            
        for paragraph_id, run_entries in grouped_entries.items():
            rankings = run_entries

            para_text = corpus_db.lookup(paragraph_id)
            if para_text is None:
                raise RuntimeError(f"docid {paragraph_id} not found in RAG corpus. Caused by run_entry: \n{run_entry}")
            rubric_paragraph= FullParagraphData( paragraph_id= paragraph_id
                                               , text= para_text
                                               , paragraph=None
                                               , paragraph_data=ParagraphData(judgments=list(), rankings=rankings)
                                               , exam_grades=None
                                               , grades=None
                                               )
            paragraphs.append(rubric_paragraph)
            # print(f"{rubric_paragraph}")


        rubric_data.append(QueryWithFullParagraphList(queryId=query_id, paragraphs= paragraphs))
    return rubric_data

def main(cmdargs=None):
    """Convert TREC RAG retrieval data to inputs for EXAM/RUBRIC."""

    import argparse

    desc = f'''Convert TREC RAG retrieval data to inputs for EXAM/RUBRIC. \n
              The RUBRIC input will to be a *JSONL.GZ file that follows this structure: \n
              \n  
                  [query_id, [FullParagraphData]] \n
              \n
               where `FullParagraphData` meets the following structure \n
             {data_model.FullParagraphData.schema_json(indent=2)}
             '''
    
    parser = argparse.ArgumentParser(description="Convert TREC RAG data to RUBRIC inputs."
                                   , epilog=desc
                                   , formatter_class=argparse.RawDescriptionHelpFormatter
                                   )
    # parser.add_argument('rag-corpus', type=str, metavar='xxx.jsonl.gz'
    #                     , help='input json file with corpus from the TREC RAG corpus'
    #                     )
    parser.add_argument('--rag-corpus-db', type=Path, metavar='msmarco.duckdb', required=True
                        , help='duckdb database with segments from the TREC RAG corpus. Create from rag-corpus via \'build_rag_corpus_db\''
                        )


    parser.add_argument('-p', '--rubric-out-file', type=str, metavar='xxx.jsonl.gz', required=True
                        , help='output json file with paragraph to grade with exam questions. The typical file pattern is `exam-xxx.jsonl.gz.'
                        )

    parser.add_argument('--query-path', type=str, metavar='PATH', help='Path to read TREC RAG queries')
    parser.add_argument(dest='input_run_path', type=str, nargs='+', metavar='PATH', help='Path(s) to read TREC RAG retrieval/run files')
    parser.add_argument('--query-out', type=str, metavar='PATH', help='Path to write queries for RUBRIC/EXAM to')

    

    parser.add_argument('--max-queries', type=int, metavar='INT', default=None, help='limit the number of queries that will be processed (for debugging)')
    parser.add_argument('--max-paragraphs', type=int, metavar='INT', default=None, help='limit the number of paragraphs that will be processed (for debugging)')


    # Parse the arguments
    args = parser.parse_args(args = cmdargs)  



    # First we load all queries
    query_set:Dict[str,str] 
    query_set = read_rag_query_file(query_file=args.query_path, max_queries = args.max_queries)

    # Fetch the qrels file  ... and munge
    input_run_data = read_rag_run_file(run_in_files=args.input_run_path)
    input_runs_by_qid:Dict[str,List[ParagraphRankingEntry]] = defaultdict(list)
    for run_entry in input_run_data:
        input_runs_by_qid[run_entry.queryId].append(run_entry)
        # print(f"{qrel_entry}")
    input_query_ids:Set[str] = input_runs_by_qid.keys()
    

    # filter query set to the queries in the qrels file only
    query_set = {qid:qstr  for qid,qstr in query_set.items() if qid in input_query_ids}
    write_query_file(file_path=args.query_out, queries=query_set)

    print(f"query_set = {query_set.keys()}")

    # load the paragraph data from duckdb
    corpus_db = segment_index.SegmentIndex(args.rag_corpus_db) # load duckdb

    

    # now emit the input files for RUBRIC/EXAM
    rubric_data:List[QueryWithFullParagraphList] 
    rubric_data = convert_paragraphs(input_runs_by_qid, query_set=query_set, corpus_db=corpus_db)
 

    writeQueryWithFullParagraphs(file_path=args.rubric_out_file, queryWithFullParagraphList=rubric_data)
    print(f'Rubric paragraph data written to {args.rubric_out_file}')


if __name__ == "__main__":
    main()


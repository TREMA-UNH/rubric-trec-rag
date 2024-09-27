from collections import defaultdict
import hashlib
import itertools
import json
from pathlib import Path
from typing import Dict, List, Optional, Iterator, Set
from pydantic import BaseModel, ValidationError

# from exam_pp.exam_to_qrels import QrelEntry 
from exam_pp import data_model
from exam_pp.data_model import FullParagraphData, ParagraphData, ParagraphRankingEntry, QueryWithFullParagraphList, writeQueryWithFullParagraphs

class RagGenText(BaseModel):
    text:str
    citations: List[int]


class RagGenSubmission(BaseModel):
    run_id : str
    topic_id : str
    topic : str
    references : List[str]
    response_length: int
    answer: List[RagGenText]


def parseRagGenSubmission(line:str) -> RagGenSubmission:
    # Parse the JSON content of the line
    # print(line)
    return RagGenSubmission.parse_raw(line)

def loadRagGenSubmissions(file_paths:List[Path], max_queries:Optional[int]) -> Iterator[RagGenSubmission]:
    '''Load LLMJudge document corpus'''

    # result:List[RagGenSubmission] = list()
    for file_path in file_paths:
        try: 
            with open(file_path, 'rt', encoding='utf-8') as file:
                for line in itertools.islice(file.readlines(), max_queries):
                    try:
                        # result.append(parseRagGenSubmission(line))
                        yield parseRagGenSubmission(line)
                    except ValidationError as e1:
                        print(f"Warning: Validation error parsing {file_path}\nFull Error:\n{e1} Offending line {line}\n")
    
        except  EOFError as e:
            print(f"Warning: File EOFError on {file_path}. Use truncated data....\nFull Error:\n{e} \n")
    # return result



#  ----

def get_md5_hash(input_string: str) -> str:
    # Convert the string to bytes
    input_bytes = input_string.strip().encode('utf-8')

    # Create an MD5 hash object
    md5_hash = hashlib.md5()

    # Update the hash object with the bytes
    md5_hash.update(input_bytes)

    # Get the hexadecimal digest of the hash
    hex_digest = md5_hash.hexdigest()

    return hex_digest






def convert_submission(rag_submission_by_qid:Dict[str,List[RagGenSubmission]])-> List[QueryWithFullParagraphList]:
    rubric_data:List[QueryWithFullParagraphList] = list()

    for query_id, submission_entries in rag_submission_by_qid.items():
        print(f'Converting {len(rag_submission_by_qid[query_id])} submissions for query {query_id}...')
        grouped_entries: Dict[str, FullParagraphData]
        grouped_entries = dict()
        for submission_entry in submission_entries:
            for index, submission_passage in enumerate(submission_entry.answer):
                paragraph_id = get_md5_hash(submission_passage.text)
                rank = index+1
                score = 1.0/rank
                rankingEntry = ParagraphRankingEntry(method=submission_entry.run_id
                                                     , paragraphId=paragraph_id
                                                     , queryId=query_id
                                                     , rank = rank
                                                     , score=score)
                if paragraph_id in grouped_entries:
                    grouped_entries[paragraph_id].paragraph_data.rankings.append(rankingEntry)
                else:
                    submittedParagraph = FullParagraphData(paragraph_id=paragraph_id
                                                           , text=submission_passage.text
                                                           , paragraph = None
                                                           , paragraph_data= ParagraphData(judgments=[], rankings=[rankingEntry])
                                                           , exam_grades=None
                                                           , grades=None)
                    grouped_entries[paragraph_id]=submittedParagraph
            

        rubric_data.append(QueryWithFullParagraphList(queryId=query_id, paragraphs= list(grouped_entries.values())))
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


    parser.add_argument('-p', '--rubric-out-file', type=str, metavar='xxx.jsonl.gz', required=True
                        , help='output json file with paragraph to grade with exam questions. The typical file pattern is `exam-xxx.jsonl.gz.'
                        )

    # parser.add_argument('--query-path', type=str, metavar='PATH', help='Path to read TREC RAG queries')
    parser.add_argument(dest='input_submission_path', type=Path, nargs='+', metavar='PATH', help='Path(s) to read TREC RAG submission files')

    

    parser.add_argument('--max-queries', type=int, metavar='INT', default=None, help='limit the number of queries that will be processed (for debugging)')
    parser.add_argument('--max-paragraphs', type=int, metavar='INT', default=None, help='limit the number of paragraphs that will be processed (for debugging)')


    # Parse the arguments
    args = parser.parse_args(args = cmdargs)  


    # Fetch the qrels file  ... and munge
    input_submission_data = loadRagGenSubmissions(file_paths=args.input_submission_path, max_queries=args.max_queries)
    rag_submissions_by_qid:Dict[str,List[RagGenSubmission]] = defaultdict(list)
    for rag_entry in input_submission_data:
        rag_submissions_by_qid[rag_entry.topic_id].append(rag_entry)
    


    print(f"query_set = {rag_submissions_by_qid.keys()}")

    

    # now emit the input files for RUBRIC/EXAM
    rubric_data:List[QueryWithFullParagraphList] 
    rubric_data = convert_submission(rag_submission_by_qid=rag_submissions_by_qid)
 

    writeQueryWithFullParagraphs(file_path=args.rubric_out_file, queryWithFullParagraphList=rubric_data)
    print(f'Rubric paragraph data written to {args.rubric_out_file}')


if __name__ == "__main__":
    main()


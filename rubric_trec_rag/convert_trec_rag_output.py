from collections import defaultdict
import gzip
import itertools
import json
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel
from exam_pp import data_model
from exam_pp.data_model import writeQueryWithFullParagraphs, QueryWithFullParagraphList,\
    ParagraphData, FullParagraphData, ExamGrades, Grades, ParagraphRankingEntry, merge, Judgment


#created by sushma akoju

import hashlib

# from .pydantic_helper import pydantic_dump

# Laura's implementation for the Generated case: to populate paragraph_ids
def get_md5_hash(input_string: str) -> str:
    
    input_string = input_string.strip()
    # Convert the string to bytes
    input_bytes = input_string.encode('utf-8')

    # Create an MD5 hash object
    md5_hash = hashlib.md5()

    # Update the hash object with the bytes
    md5_hash.update(input_bytes)

    # Get the hexadecimal digest of the hash
    hex_digest = md5_hash.hexdigest()

    return hex_digest


#****************Sushma's implementation from here******************

def parseQueryWithFullParagraphListForGen(line:str) -> QueryWithFullParagraphList:
    # Parse the JSON content of the line
    # print(line)
    data = json.loads(line)
    print(data)
    #QueryWithFullParagraphList.queryId, ParagraphRankingEntry.query_id -> use query_id
    run_id, query_id, query, references, answer = data['run_id'].strip(), \
                                    data['topic_id'].strip(), data['topic'].strip(), data['references'],data['answer']
    
    #ParagraphRankingEntry.paragraphId, FullParagraphData.paragraph_id -> use paragraph_id
    paragraph_id = ""
    
    fullParagraphList:List[FullParagraphData] = list()

    for i,a in enumerate(answer):
        
        this_text = a['text']
        #generate hash for this "text"
        paragraph_id = get_md5_hash(this_text)
        rank = i+1
        #right now we just have one paragraph data per text 
        #we are not including the citations i.e. references listed for each text in the answer for TREC RAG task (Generation)
        
        paragraphRankingEntry = ParagraphRankingEntry(method=run_id, \
            paragraphId = paragraph_id, queryId= query_id, rank=int(rank), score=float(1.0 / rank ))
        paragraph_data = ParagraphData(judgments=list(),rankings=[paragraphRankingEntry])
        fullParagraphData = FullParagraphData(paragraph_id=paragraph_id, text=this_text, \
                                            paragraph=None,paragraph_data=paragraph_data, exam_grades=None, grades=None)
        fullParagraphList.append(fullParagraphData)
    
    return QueryWithFullParagraphList(queryId=query_id,paragraphs=fullParagraphList )

# Path to the benchmarkY3test-qrels-with-text.jsonl.gz file
def parseQueryWithFullParagraphsForGenTask(file_path:Path) -> List[QueryWithFullParagraphList] :
    '''Load JSONL.GZ file with exam annotations in FullParagraph information'''
    # Open the gzipped file

    result:List[QueryWithFullParagraphList] = list()
    try: 
        with gzip.open(file_path, 'rt', encoding='utf-8') as file:
            # return [parseQueryWithFullParagraphList(line) for line in file]
            for line in file:
                result.append(parseQueryWithFullParagraphListForGen(line))
    except  EOFError as e:
        print(f"Warning: Gzip EOFError on {file_path}. Use truncated data....\nFull Error:\n{e}")
    return result
#****************END******************

def convertForGenTask(files:List[Path], outdir:Optional[Path], outfile:Optional[Path], ranking_method:Optional[str], grade_llm:Optional[str], old_grading_prompt:Optional[str], grading_prompt:Optional[str]):

    for infile in files:
        converted= list()
        #modified function call
        for query_paras in parseQueryWithFullParagraphsForGenTask(file_path=infile):
            for para in query_paras.paragraphs:
                if ranking_method is not None:
                    for r in para.paragraph_data.rankings:
                        r.method = ranking_method
                        r.paragraphId = para.paragraph_id

                if grade_llm is not None:
                    if para.exam_grades:
                        for eg in  para.exam_grades:
                            eg.llm=grade_llm
                    if para.grades:
                        for g in para.grades:
                            g.llm=grade_llm

                if grading_prompt is not None:
                    if para.exam_grades:
                        for eg in para.exam_grades:
                            if (eg.prompt_info is None and old_grading_prompt is None) or (eg.prompt_info is not None and eg.prompt_info.get("prompt_class")==old_grading_prompt):  # the old prompt could also have been set to None.
                                if eg.prompt_info is None:
                                    eg.prompt_info = dict()
                                eg.prompt_info["prompt_class"]=grading_prompt
                    if para.grades:
                        for g in para.grades:
                            if (g.prompt_info is None and old_grading_prompt is None) or (g.prompt_info is not None and g.prompt_info.get("prompt_class")==old_grading_prompt):
                                if g.prompt_info is None:
                                    g.prompt_info = dict()
                                g.prompt_info["prompt_class"]=grading_prompt

            converted.append(query_paras)



        out:Path
        if outdir is None and outfile is None:
            print("overwriting original xxx.jsonl.gz files")
            out = infile
        elif outdir is not None:
            print(f" Writing converted files to {outdir}")
            Path(outdir).mkdir(exist_ok=True)
            if outfile is not None:
                out = Path(outdir /  outfile.name)
            else:
                out = outdir.joinpath(Path(infile).name)
        elif outfile is not None:
            out = outfile
        print(f" Writing converted file to {Path(out).absolute}")

        writeQueryWithFullParagraphs(file_path=out, queryWithFullParagraphList=converted)



def main():
    """Entry point for the module."""
    x = parseQueryWithFullParagraphsForGenTask("../data/trec/elect-fifth.gz")
    print(x[0])
    import argparse
    parser = argparse.ArgumentParser(description="Merge *jsonl.gz files")

    subparsers = parser.add_subparsers(dest='command', help="Choose one of the sub-commands")



    # merge_parser = subparsers.add_parser('merge', help="Merge full paragraphs (xxx.jsonl.gz files) with or without grades into a single new file.")
    # merge_parser.add_argument(dest='paragraph_file', type=Path, metavar='xxx.jsonl.gz', nargs='+'
    #                     , help='one or more json files with paragraph with or without exam grades.The typical file pattern is `exam-xxx.jsonl.gz.'
    #                     )
    # merge_parser.add_argument('-o','--out', type=str, metavar='FILE'
    #                     , help=f'output file that merged all input files'
    #                     )
        
    convert_parser = subparsers.add_parser('convert', help="change entries in full paragraphs files (xxx.jsonl.gz)")
    convert_parser.add_argument(dest='paragraph_file', type=str,metavar='xxx.jsonl.gz', nargs='+'
                        , help='one or more json files with paragraph with or without exam grades.The typical file pattern is `exam-xxx.jsonl.gz.'
                        )
    convert_parser.add_argument('--ranking-method', type=str, metavar="NAME", help="Change entry to paragraph_data.rankings[].method to NAME")
    convert_parser.add_argument('--grade-llm', type=str, metavar="NAME", help="Change entry to exam_grades[].llm to NAME")
    convert_parser.add_argument('--grading-prompt', type=str, metavar="NAME", help="Change entry to exam_grades[].llm_info[prompt_class] to NAME, but only when it was previously set to --old-grading-prompt)")
    convert_parser.add_argument('--old-grading-prompt', type=str, metavar="NAME", help="Old value for --grading-prompt.  Can be set to None, to fix legacy configuations.")
    convert_parser.add_argument('-d','--out-dir', type=Path, metavar='DIR'
                        , help=f'output directory that converted files will be written to, using the same basename'
                        )
    convert_parser.add_argument('-o','--out-file', type=Path, metavar='FILE'
                        , help=f'output directory that converted file will be written to (only applies when only a single input file is given)'
                        )

    args = parser.parse_args()

    # if args.command == "merge":
    #     merge(files=args.paragraph_file, out=args.out)

    if args.command == "convert":
        convertForGenTask(files=args.paragraph_file, outdir=args.out_dir, outfile=args.out_file, ranking_method=args.ranking_method, grade_llm=args.grade_llm, old_grading_prompt=args.old_grading_prompt, grading_prompt=args.grading_prompt)

if __name__ == "__main__":
    main()
from collections import defaultdict
import itertools
import json
from pathlib import Path
from typing import Dict, Iterable, List, Iterator
from operator import attrgetter

from exam_pp.data_model import FullParagraphData,  ParagraphRankingEntry, QueryWithFullParagraphList, parseQueryWithFullParagraphs, writeQueryWithFullParagraphs

def export_run_file(run_file:Path, ranking_entries:Iterable[ParagraphRankingEntry]):
    with open(file=run_file,mode='wt',encoding="utf-8") as f:
            f.writelines("\n".join( [  
                                    "\t".join([ranking.queryId, "Q0", ranking.paragraphId, f"{ranking.rank}", f"{ranking.score}", ranking.method  ])
                                    for ranking in ranking_entries])
                                  )

def main(cmdargs=None):
    """Convert graded TREC RAG gen data to run file for trec_eval."""

    import argparse

    desc = f'''Convert graded TREC RAG gen data to run file for trec_eval. \n
              The RUBRIC input will to be a *JSONL.GZ file that follows this structure: \n
              \n  
                  [query_id, [FullParagraphData]] \n
              \n
               where `FullParagraphData` meets the following structure \n
             {FullParagraphData.schema_json(indent=2)}
             '''
    
    parser = argparse.ArgumentParser(description="Convert graded TREC RAG gen data to run file for trec_eval."
                                   , epilog=desc
                                   , formatter_class=argparse.RawDescriptionHelpFormatter
                                   )


    parser.add_argument('-r', '--rubric-graded-file', type=str, metavar='xxx.jsonl.gz', required=True
                        , help='input rubric json file with paragraph/grade information. The typical file pattern is `exam-xxx.jsonl.gz.'
                        )

    parser.add_argument('--run-out', type=Path, metavar='PATH', help='Path to write run files to')


    # Parse the arguments
    args = parser.parse_args(args = cmdargs)  





    # now emit the input files for RUBRIC/EXAM
    rubric_data:List[QueryWithFullParagraphList] 
    rubric_data = parseQueryWithFullParagraphs(args.rubric_graded_file)

    run_entry_per_method:Dict[str,List[ParagraphRankingEntry]] = defaultdict(list)

    for entry in rubric_data:
        for para in entry.paragraphs:
            for rankEntry in para.paragraph_data.rankings:
                run_entry_per_method[rankEntry.method].append(rankEntry)

    runDir:Path = args.run_out
    runDir.mkdir(exist_ok=True)

    for method,rankEntries in run_entry_per_method.items():
        runFile = runDir/(f'{method}-gen.run')
        if(runFile.exists()):
            print(f"Overwriting {runFile.absolute()}")
        else: 
            print(f"Exporting to {runFile.absolute()}")
        export_run_file(run_file=runFile, ranking_entries=sorted(rankEntries, key=attrgetter('queryId','rank')))





if __name__ == "__main__":
    main()


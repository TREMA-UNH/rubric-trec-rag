#!/bin/bash


set -exo pipefail



DATA="./data"
ungraded_gen="rubric-rag24-gen.jsonl.gz"
ungraded_auggen="rubric-rag24-auggen.jsonl.gz"

promptclass="QuestionSelfRatedUnanswerablePromptWithChoices"
max_q="100"


graded_t5_gen="questions-rate--rubric-rag24-gen.jsonl.gz"
graded_llama_gen="questions-rate--llama3--rubric-rag24-gen.jsonl.gz"
final_t5_gen="cut_${max_q}--${graded_t5_gen}"
final_llama_gen="cut_${max_q}--${graded_llama_gen}"




#################################
# Use same number of queries

ungraded="$ungraded_gen"
graded_t5="$graded_t5_gen"
graded_llama="$graded_llama_gen"
final_t5="$final_t5_gen"
final_llama="$final_llama_gen"


python -O -m exam_pp.exam_grading $DATA/$ungraded --max-queries $max_q --restart-paragraphs-file $DATA/$graded_t5 -o $DATA/$final_t5  --model-pipeline text2text --model-name google/flan-t5-large --prompt-class QuestionSelfRatedUnanswerablePromptWithChoices --question-path $DATA/rag24-questions.jsonl.gz  --question-type question-bank



python -O -m exam_pp.exam_grading $DATA/$ungraded --max-queries $max_q --restart-paragraphs-file $DATA/$graded_llama -o $DATA/$final_llama  --model-pipeline llama --model-name meta-llama/Meta-Llama-3-8B-Instruct --prompt-class QuestionSelfRatedUnanswerablePromptWithChoices --question-path $DATA/rag24-questions.jsonl.gz  --question-type question-bank




######################
# Export Run file

ungraded_base="${ungraded%%.*}"
runs="$ungraded_base-runs" 
python -O -m rubric_trec_rag.export_rag_gen_as_run -r $DATA/$final_llama_gen --run-out ./data/$runs



####################
# Produce leaderboards

for final in "$final_t5" "$final_llama"; do
    final_base="${final%%.*}"
    minrating="4"

    # Coverage
    cover_board="cover-leaderboard-$promptclass-minrating-$minrating.solo.$final_base"
    python -O -m exam_pp.exam_evaluation $DATA/$final --question-set question-bank --prompt-class $promptclass --min-self-rating $minrating --leaderboard-out $DATA/$cover_board.tsv
    
    # MAP
    p20_board="P20-leaderboard-$promptclass-minrating-$minrating.solo.$final_base"
    python -O -m exam_pp.exam_evaluation $DATA/$final --question-set question-bank --prompt-class $promptclass -q $DATA/$p20_board.qrels  --min-self-rating $minrating --qrel-leaderboard-out $DATA/$p20_board.tsv --run-dir $DATA/$runs
    
    # NDCG
    ndcg_board="ndcg-leaderboard-$promptclass.solo.$final_base"
	python -O -m exam_pp.exam_evaluation $DATA/$final --question-set question-bank --prompt-class $promptclass --trec-eval-metric "ndcg_cut.20" -q $DATA/$ndcg_board.qrels --min-self-rating $minrating --qrel-leaderboard-out $DATA/$ndcg_board.tsv --run-dir $DATA/$runs     

    paste $DATA/$cover_board.tsv $DATA/$p20_board.tsv $DATA/$ndcg_board.tsv > $DATA/$final_base.tsv
	
done

paste $DATA/${final_t5%%.*}.tsv $DATA/${final_llama%%.*}.tsv > $DATA/cut_${max_q}_gen.tsv

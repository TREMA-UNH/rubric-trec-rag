#!/bin/sh


python -O -m rubric_trec_rag.rag_retrieval_inputs --query-path ./data/topics.rag24.test.txt --query-out ./data/queries-rag24.json  -p ./data/rubric-rag24-retrieval.jsonl.gz  --rag-corpus-db ./data/msmarco.duckdb   ./data/retrieval/*

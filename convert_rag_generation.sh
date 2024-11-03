#!/bin/sh


set -eo pipefail

echo "auggen"

python -O -m rubric_trec_rag.rag_generation_inputs  -p ./data/rubric-rag24-auggen.jsonl.gz  ./data/auggen/*

echo ""
echo "gen"

python -O -m rubric_trec_rag.rag_generation_inputs  -p ./data/rubric-rag24-gen.jsonl.gz  ./data/gen/*

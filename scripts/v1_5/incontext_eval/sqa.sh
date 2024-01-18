#!/bin/bash

python -m llava.incontext_eval.conversions.scienceqa \
    --question-file ./playground/data/eval/scienceqa/problems.json \
    --splits-file ./playground/data/eval/scienceqa/pid_splits.json \
    --output-file ./playground/data/eval/scienceqa/incontext_problems.json \
    --num-examples 3

python -m llava.incontext_eval.model_vqa_science \
    --model-path liuhaotian/llava-v1.5-13b \
    --all-questions-file ./playground/data/eval/scienceqa/problems.json \
    --test-questions-file ./playground/data/eval/scienceqa/incontext_problems.json \
    --image-folder ./playground/data/eval/scienceqa/images/test \
    --answers-file ./playground/data/eval/scienceqa/answers/llava-v1.5-13b.jsonl \
    --single-pred-prompt \
    --temperature 0 \
    --conv-mode vicuna_v1

python llava/eval/eval_science_qa.py \
    --base-dir ./playground/data/eval/scienceqa \
    --result-file ./playground/data/eval/scienceqa/answers/llava-v1.5-13b.jsonl \
    --output-file ./playground/data/eval/scienceqa/answers/llava-v1.5-13b_output.jsonl \
    --output-result ./playground/data/eval/scienceqa/answers/llava-v1.5-13b_result.json

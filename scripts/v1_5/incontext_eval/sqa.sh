#!/bin/bash

# convert scienceQA problems to LLaVA format
python scripts/convert_sqa_to_llava.py \
    convert_to_llava \
    --base-dir ./playground/data/eval/scienceqa \
    --prompt-format "CQM-A" \
    --split train

python scripts/convert_sqa_to_llava.py \
    convert_to_llava \
    --base-dir ./playground/data/eval/scienceqa \
    --prompt-format "CQM-A" \
    --split test

# add in examples from trianing data
python -m llava.incontext_eval.conversions.scienceqa \
    --train-questions-file ./playground/data/eval/scienceqa/llava_train_CQM-A.json \
    --test-questions-file ./playground/data/eval/scienceqa/llava_test_CQM-A.json \
    --output-file ./playground/data/eval/scienceqa/llava_incontext_test_CQM-A.json \
    --num-examples 3

python -m llava.incontext_eval.model_vqa_science \
    --model-path liuhaotian/llava-v1.5-13b \
    --train-questions-file ./playground/data/eval/scienceqa/llava_train_CQM-A.json \
    --test-questions-file ./playground/data/eval/scienceqa/llava_incontext_test_CQM-A.json \
    --train-image-folder ./playground/data/eval/scienceqa/images/train \
    --test-image-folder ./playground/data/eval/scienceqa/images/test \
    --answers-file ./playground/data/eval/scienceqa/answers/llava-v1.5-13b.jsonl \
    --single-pred-prompt \
    --temperature 0 \
    --conv-mode vicuna_v1

python llava/eval/eval_science_qa.py \
    --base-dir ./playground/data/eval/scienceqa \
    --result-file ./playground/data/eval/scienceqa/answers/llava-v1.5-13b.jsonl \
    --output-file ./playground/data/eval/scienceqa/answers/llava-v1.5-13b_output.jsonl \
    --output-result ./playground/data/eval/scienceqa/answers/llava-v1.5-13b_result.json

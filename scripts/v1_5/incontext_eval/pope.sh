#!/bin/bash

# add in examples from trianing data

echo "adding examples into test set"

python -m llava.incontext_eval.conversions.pope \
    --questions-folder ./playground/data/eval/pope/coco \
    --output-folder ./playground/data/eval/pope \
    --num-examples 3

echo "running model"

python -m llava.incontext_eval.model_vqa_loader \
    --model-path liuhaotian/llava-v1.5-13b \
    --question-file ./playground/data/eval/pope/incontext_llava_pope_test.jsonl \
    --examples-file ./playground/data/eval/pope/llava_examples.json \
    --image-folder ./playground/data/eval/pope/val2014 \
    --answers-file ./playground/data/eval/pope/answers/incontext_llava-v1.5-13b.jsonl \
    --temperature 0 \
    --conv-mode vicuna_v1

echo "evaluating predictions"

python llava/eval/eval_pope.py \
    --annotation-dir ./playground/data/eval/pope/coco \
    --question-file ./playground/data/eval/pope/incontext_llava_pope_test.jsonl \
    --result-file ./playground/data/eval/pope/answers/incontext_llava-v1.5-13b.jsonl

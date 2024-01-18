import os
import json
import random
import argparse

def convert_scienceqa(args):
    import pdb; pdb.set_trace()
    train_pids = []
    test_pids = []

    with open(args.splits_file, "r") as f:
        splits = json.load(f)

        train_pids = splits["train"]
        test_pids = set(splits["test"])

    with open(args.question_file, "r") as f:
        questions = json.load(f)

        test_qns = [qn for pid, qn in questions.items() if pid in test_pids]

    for qn in test_qns:
        example_pids = random.sample(train_pids, args.num_examples)

        qn["examples"] = example_pids        

    with open(args.output_file, "w") as f:
        json.dump(test_qns, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--question-file", type=str, default="")
    parser.add_argument("--splits-file", type=str, default="")
    parser.add_argument("--output-file", type=str, default="")
    parser.add_argument("--num-examples", type=int, default=3)

    args = parser.parse_args()

    convert_scienceqa(args)
import os
import json
import random
import argparse

def convert_scienceqa(args):
    with open(args.train_questions_file, "r") as f:
        train_qns = json.load(f)

        text_only_question_idxs = [i for i in range(len(train_qns)) if "image" not in train_qns[i]]
        image_question_idxs = [i for i in range(len(train_qns)) if "image" in train_qns[i]]

    with open(args.test_questions_file, "r") as f:
        test_qns = json.load(f)

    def get_answer(question_index):
        return train_qns[question_index]["conversations"][1]["value"]

    for qn in test_qns:
        example_idxs = [0 for _ in range(args.num_examples)]
        while True:
            if "image" not in qn:
                # no image, only sample from questions with no image
                example_idxs = random.sample(text_only_question_idxs, args.num_examples)
            else:
                example_idxs = random.sample(image_question_idxs, args.num_examples)

            if args.num_examples <= 1:
                break

            # all answers are the same
            if all(get_answer(i) == get_answer(example_idxs[0]) for i in example_idxs):
                continue
    
            break
            

        qn["examples"] = example_idxs        

    with open(args.output_file, "w") as f:
        random.shuffle(test_qns)
        json.dump(test_qns, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-questions-file", type=str, default="")
    parser.add_argument("--test-questions-file", type=str, default="")
    parser.add_argument("--output-file", type=str, default="")
    parser.add_argument("--num-examples", type=int, default=3)

    args = parser.parse_args()

    convert_scienceqa(args)
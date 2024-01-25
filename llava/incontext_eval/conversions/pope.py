import os
import json
import random
import argparse

def convert_pope(args):
    all_questions = []
    with open(os.path.join(args.questions_folder, "coco_pope_adversarial.json"), "r") as f:
        for line in f:
            qn = json.loads(line)
            qn["category"] = "adversarial"
            all_questions.append(qn)
    
    with open(os.path.join(args.questions_folder, "coco_pope_random.json"), "r") as f:
        for line in f:
            qn = json.loads(line)
            qn["category"] = "random"
            all_questions.append(qn)

    with open(os.path.join(args.questions_folder, "coco_pope_popular.json"), "r") as f:
        for line in f:
            qn = json.loads(line)
            qn["category"] = "popular"
            all_questions.append(qn)

    # define an examples-test split because all POPE questions are here
    random.shuffle(all_questions)

    num_example_qns = int(len(all_questions) * 0.2)
    
    example_qns = all_questions[:num_example_qns]
    with open(os.path.join(args.output_folder, "llava_examples.json"), "w") as f:
        for qn in example_qns:
            f.write(json.dumps(qn) + "\n")

    test_qns = all_questions[num_example_qns:]
    for qn in test_qns:
        example_idxs = [0]
        while (
            all(example_qns[i]["label"] == example_qns[example_idxs[0]]["label"] for i in example_idxs)
        ):
            example_idxs = random.sample(list(range(num_example_qns)), args.num_examples)

        qn["examples"] = example_idxs        

    with open(os.path.join(args.output_folder, "incontext_llava_pope_test.jsonl"), "w") as f:
        for qn in test_qns:
            f.write(json.dumps(qn) + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions-folder", type=str, default="")
    parser.add_argument("--output-folder", type=str, default="")
    parser.add_argument("--num-examples", type=int, default=3)

    args = parser.parse_args()

    convert_pope(args)
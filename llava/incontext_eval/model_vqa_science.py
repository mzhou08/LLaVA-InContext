import argparse
import torch
import os
import json
from tqdm import tqdm
import shortuuid

from llava.constants import IMAGE_TOKEN_INDEX, DEFAULT_IMAGE_TOKEN, DEFAULT_IM_START_TOKEN, DEFAULT_IM_END_TOKEN
from llava.conversation import conv_templates, SeparatorStyle
from llava.model.builder import load_pretrained_model
from llava.utils import disable_torch_init
from llava.mm_utils import tokenizer_image_token, get_model_name_from_path, KeywordsStoppingCriteria

from PIL import Image
import math


def split_list(lst, n):
    """Split a list into n (roughly) equal-sized chunks"""
    chunk_size = math.ceil(len(lst) / n)  # integer division
    return [lst[i:i+chunk_size] for i in range(0, len(lst), chunk_size)]


def get_chunk(lst, n, k):
    chunks = split_list(lst, n)
    return chunks[k]


def eval_model(args):
    # Model
    disable_torch_init()
    model_path = os.path.expanduser(args.model_path)
    model_name = get_model_name_from_path(model_path)
    tokenizer, model, image_processor, context_len = load_pretrained_model(model_path, args.model_base, model_name)

    train_questions = json.load(open(os.path.expanduser(args.train_questions_file), "r"))

    incontext_questions = json.load(open(os.path.expanduser(args.test_questions_file), "r"))
    incontext_questions = get_chunk(incontext_questions, args.num_chunks, args.chunk_idx)
    answers_file = os.path.expanduser(args.answers_file)
    os.makedirs(os.path.dirname(answers_file), exist_ok=True)
    ans_file = open(answers_file, "w")

    # take in a line and return well-formatted question, cur_prompt (for logging), and images
    def format_question(line, is_example):
        # import pdb; pdb.set_trace()
        question = line['conversations'][0]
        qs = question['value'].replace('<image>', '').strip()
        cur_prompt = qs

        if 'image' in line:
            image_file = line["image"]
            if is_example:
                image = Image.open(os.path.join(args.train_image_folder, image_file))
            else:
                image = Image.open(os.path.join(args.test_image_folder, image_file))
        
            image_tensor = image_processor.preprocess(image, return_tensors='pt')['pixel_values'][0]
            images = image_tensor.unsqueeze(0).half().cuda()
            if getattr(model.config, 'mm_use_im_start_end', False):
                qs = DEFAULT_IM_START_TOKEN + DEFAULT_IMAGE_TOKEN + DEFAULT_IM_END_TOKEN + '\n' + qs
            else:
                qs = DEFAULT_IMAGE_TOKEN + '\n' + qs

            # Why are we appending the image to the front?
            cur_prompt = '<image>' + '\n' + cur_prompt
        else:
            images = None

        if args.single_pred_prompt:
            qs = qs + '\n' + "Answer with the option's letter from the given choices directly."
            cur_prompt = cur_prompt + '\n' + "Answer with the option's letter from the given choices directly."

        return qs, cur_prompt, images


    for i, line in enumerate(tqdm(incontext_questions)):
        if i == 100:
            raise Exception("Only evaluating 100 examples for debugging")
        
        idx = line["id"]

        example_idxs = line["examples"]
        example_questions = [train_questions[train_idx] for train_idx in example_idxs]
        
        conv = conv_templates[args.conv_mode].copy()

        all_images = []

        for example in example_questions:
            example_qs, _, example_images = format_question(example, is_example=True)
            
            # import pdb; pdb.set_trace()

            # append the example question to the prompt
            conv.append_message(conv.roles[0], example_qs)
            # append the example answer to the prompt
            conv.append_message(conv.roles[1], example["conversations"][1]["value"])
            if example_images is not None:
                all_images.append(
                    example_images.squeeze(0) # removing the first dimension
                )

        # append the actual question to the conversation
        qs, cur_prompt, qs_images = format_question(line, is_example=False)
        conv.append_message(conv.roles[0], qs)
        if qs_images is not None:
            all_images.append(qs_images.squeeze(0))

        # import pdb; pdb.set_trace()

        conv.append_message(conv.roles[1], None)
        prompt = conv.get_prompt()

        input_ids = tokenizer_image_token(prompt, tokenizer, IMAGE_TOKEN_INDEX, return_tensors='pt').unsqueeze(0).cuda()

        stop_str = conv.sep if conv.sep_style != SeparatorStyle.TWO else conv.sep2
        keywords = [stop_str]
        stopping_criteria = [KeywordsStoppingCriteria(keywords, tokenizer, input_ids)] if conv.version == "v0" else None

        # combine all images
        if len(all_images) > 0:
            all_images = torch.stack(all_images)
        else:
            all_images = None

        import pdb; pdb.set_trace()

        with torch.inference_mode():
            output_ids = model.generate(
                input_ids,
                images=all_images,
                do_sample=True if args.temperature > 0 else False,
                temperature=args.temperature,
                max_new_tokens=1024,
                use_cache=True,
                stopping_criteria=stopping_criteria,
            )

        input_token_len = input_ids.shape[1]
        n_diff_input_output = (input_ids != output_ids[:, :input_token_len]).sum().item()
        if n_diff_input_output > 0:
            print(f'[Warning] {n_diff_input_output} output_ids are not the same as the input_ids')
        outputs = tokenizer.batch_decode(output_ids[:, input_token_len:], skip_special_tokens=True)[0]
        outputs = outputs.strip()
        if outputs.endswith(stop_str):
            outputs = outputs[:-len(stop_str)]
        outputs = outputs.strip()

        model_ans = outputs[-2:-1] if len(outputs) > 1 else outputs

        if model_ans != line['conversations'][1]['value'][-2:-1]:
            # print(i)
            continue
            # print(
            #     f"""
            #     Examples: {[example['id'] for example in example_questions]}
            #     {' | '.join([example['conversations'][0]['value'] + "Answer:" + example['conversations'][1]['value'] for example in example_questions])}
            #     Questions: {line['conversations'][0]['value']}
            #     True Answer: {line['conversations'][1]['value']}
            #     Model Prediction: {outputs}
            #     """
            # )
            # import pdb; pdb.set_trace()

        # prompt for answer
        if args.answer_prompter:
            outputs_reasoning = outputs
            input_ids = tokenizer_image_token(prompt + outputs_reasoning + ' ###\nANSWER:', tokenizer, IMAGE_TOKEN_INDEX, return_tensors='pt').unsqueeze(0).cuda()

            with torch.inference_mode():
                output_ids = model.generate(
                    input_ids,
                    images=all_images,
                    do_sample=True if args.temperature > 0 else False,
                    temperature=args.temperature,
                    max_new_tokens=64,
                    use_cache=True,
                    stopping_criteria=[stopping_criteria])

            input_token_len = input_ids.shape[1]
            n_diff_input_output = (input_ids != output_ids[:, :input_token_len]).sum().item()
            if n_diff_input_output > 0:
                print(f'[Warning] {n_diff_input_output} output_ids are not the same as the input_ids')
            outputs = tokenizer.batch_decode(output_ids[:, input_token_len:], skip_special_tokens=True)[0]
            outputs = outputs.strip()
            if outputs.endswith(stop_str):
                outputs = outputs[:-len(stop_str)]
            outputs = outputs.strip()
            outputs = outputs_reasoning + '\n The answer is ' + outputs

        ans_id = shortuuid.uuid()
        ans_file.write(json.dumps({"question_id": idx,
                                   "prompt": cur_prompt,
                                   "text": outputs,
                                   "answer_id": ans_id,
                                   "model_id": model_name,
                                   "metadata": {}}) + "\n")
        ans_file.flush()
    ans_file.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=str, default="facebook/opt-350m")
    parser.add_argument("--model-base", type=str, default=None)
    parser.add_argument("--train-image-folder", type=str, default="")
    parser.add_argument("--test-image-folder", type=str, default="")
    parser.add_argument("--train-questions-file", type=str, default="")
    parser.add_argument("--test-questions-file", type=str, default="tables/question.json")
    parser.add_argument("--answers-file", type=str, default="answer.jsonl")
    parser.add_argument("--conv-mode", type=str, default="llava_v0")
    parser.add_argument("--num-chunks", type=int, default=1)
    parser.add_argument("--chunk-idx", type=int, default=0)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--answer-prompter", action="store_true")
    parser.add_argument("--single-pred-prompt", action="store_true")
    args = parser.parse_args()

    eval_model(args)
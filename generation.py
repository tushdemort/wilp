"DocString"
import os
from dotenv import load_dotenv
import pathlib

import random
import openai

dotenv_path = pathlib.Path('.env')
load_dotenv(dotenv_path=dotenv_path)

key_index = random.randint(0, 4)
key_array = [os.getenv("KEY1"), os.getenv("KEY2"), os.getenv("KEY3"), os.getenv("KEY4"), os.getenv("KEY5")]

openai.api_key = key_array[key_index]


textual_f = '''Do not repeat answers and every question. Please use the following format template for ea h question and answer pair.
Question**:

Answer&&:
---$$$---
'''

mcq_f = '''Please use the format template. Do not repeat answers.
Question**:
---&&&---
A) ANSWER 1
B) ANSWER 2
C) ANSWER 3
D) ANSWER 4
Correct Answer: ANSWER
---$$$---
'''

multi_mcq_f = ''' Please use the format template. Do not repeat answers.
QUESTION:

---&&&---
A) ANSWER 1
B) ANSWER 2
C) ANSWER 3
D) ANSWER 4
Correct Answer:
---$$$---
Make sure atleast two options are correct.
'''


def gen_response(prompt):
    "DocString"
    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {'role': 'system', 'content': "You are an AI used by a university to generate questions for their exams. You strictly follow the prompts and do the tasks"},
            {'role': 'user', 'content': prompt}
        ]
    )
    response=completion["choices"][0]['message']["content"]
    response=response.split('---$$$---')

    '''response = list(filter(('').__ne__, response))

    if ('Question' in response[0]):
        return gen_response(prompt)
    if ('question' in response[0]):
        return gen_response(prompt)
    if ('QUESTION' in response[0]):
        return gen_response(prompt)'''

    return response


def short_answer(context, difficulty):
    "DocString"
    prompt = "Write five question and answers on" + \
        context + textual_f + ' please make sure the difficulty level of the questions is ' + \
        difficulty + ' and the answer should be more than 30 words and less than 50 words'
    response = gen_response(prompt)

    all_ques=[]
    for i in range(0,5):
        response_temp=response[i].split('Question**:')
        response_temp=response_temp[1].split('Answer&&:')
        curr_ques={}
        curr_ques['question']=response_temp[0].replace("\n", "")
        curr_ques['answer']=response_temp[1].replace("\n", "")
        all_ques.append(curr_ques)
    return all_ques


def long_answer(context, difficulty):
    "DocString"
    prompt = "Write five question and answers on" + \
        context + textual_f + ' please make sure the difficulty level of the questions is ' + \
        difficulty + ' and the answer should be more than 80 words and less than 100  words'
    response = gen_response(prompt)

    all_ques=[]
    for i in range(0,5):
        response_temp=response[i].split('Question**:')
        response_temp=response_temp[1].split('Answer&&:')
        curr_ques={}
        curr_ques['question']=response_temp[0].replace("\n", "")
        curr_ques['answer']=response_temp[1].replace("\n", "")
        all_ques.append(curr_ques)
    return all_ques


def mcq(context, difficulty):
    "DocString"
    prompt = "Write a five multiple-choice questions on " + \
        context + mcq_f + ' please make sure the difficulty level of the questions is ' + \
        difficulty + ' In the options you give in the mcqs please " + \
        "make sure to add some red herrings to make the questions challenging'
    response = gen_response(prompt)

    all_ques=[]
    for i in response[0:5]:
        temp=i.split('---&&&---')
        temp[-1]=temp[-1].replace('\n\n', '\n')
        options=temp[-1].split('\n')
        correct=options[5].split('Correct Answer: ')[-1]
        options=options[1:5]
        options_dict={}
        for i in range(0,4):
            label=options[i][0]
            options_dict[label]=options[i][3:]
        curr_ques={}
        question=temp[0].replace("\n", "")
        question=question[11:]
        curr_ques['question']=question
        curr_ques['options']=options_dict
        curr_ques['correct']=correct[0]
        all_ques.append(curr_ques)
    return all_ques


def multi_mcq(context, difficulty):
    "DocString"
    prompt = 'write 5 mcq with more than 1 correct answers on the given context: '+context + \
        multi_mcq_f + ' please make sure the difficulty level of the questions is ' + difficulty
    response = gen_response(prompt)


    all_ques=[]
    for i in response[0:5]:
        temp=i.split('---&&&---')
        temp[-1]=temp[-1].replace('\n\n', '\n')
        options=temp[-1].split('\n')
        correct=options[5].split('Correct Answer: ')[-1]
        options=options[1:5]
        options_dict={}
        for i in range(0,4):
            label=options[i][0]
            options_dict[label]=options[i][3:]
        curr_ques={}
        question=temp[0].replace("\n", "")
        question=question[11:]
        curr_ques['question']=question
        curr_ques['options']=options_dict
        correct_string=''
        for i in correct.split(','):
            correct_string+=i
        correct_string=correct_string.replace(' ', '')
        curr_ques['correct']=correct_string
        all_ques.append(curr_ques)
    return all_ques


def ques_gen(context, ques_type, ques_diff):
    "DocString"
    if ques_type == 'mcq':
        return mcq(context, ques_diff)
    if ques_type == 'short':
        return short_answer(context, ques_diff)
    if ques_type == 'long':
        return long_answer(context, ques_diff)
    return multi_mcq(context, ques_diff)

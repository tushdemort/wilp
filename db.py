"DocString"
import os
import shutil
import json
from operator import add
from datetime import datetime, date
import firebase_admin
from firebase_admin import credentials, firestore, storage
import numpy as np

cred = credentials.Certificate("secret/firebase.json")
firebase_admin.initialize_app(
    cred, {'storageBucket': 'wilp-wheebox.appspot.com'})
db = firestore.client()
bucket = storage.bucket()

def approved_fire(exam_info):
    data = dict(exam_info)
    db.collection('courses').document(data['courseId']).collection('exams').document(data['refId']).update({'approved': True})

def curr_sem():
    "DocString"
    todays_date = date.today()
    month = todays_date.month
    if ((month-1)//6) == 0:
        return f"{todays_date.year}-2"
    return f"{todays_date.year}-1"


def upload(ques_info_element, course_id, prof_id, ques_info):
    "DocString"
    test_dict = {
        'ques': ques_info_element['question'],
        'prof': prof_id,
        'correct': ques_info_element['correct'],
        'diff': ques_info_element['diff'],
        'type': ques_info['type'],
        'topics': ques_info['topics']
    }
    if ques_info['type'] == 'mcq' or ques_info['type'] == 'multi_mcq':
        test_dict['options'] = ques_info_element['options']
    _, k = db.collection('courses').document(
        course_id).collection('ques_bank').add(test_dict)

    update_topics(course_id, ques_info['topics'])

    return k


def upload_one(ques_info, course_id, topics):
    "DocString"
    db.collection('courses').document(
        course_id).collection('ques_bank').add(ques_info)

    update_topics(course_id, ques_info['topics'])


def update_topics(course_id, topics):
    "DocString"
    curr_topics = course_info(course_id)['topics']
    for i in topics:
        if i not in curr_topics:
            curr_topics.append(i)
    db.collection('courses').document(
        course_id).update({'topics': curr_topics})


def course_prof(prof_id):
    "DocString"
    k = db.collection('professors').stream()
    for i in k:
        if str(i.id) == prof_id:
            courses = i.to_dict()['course']
            return courses
    return []


def course_info(course_id):
    "DocString"
    k = db.collection('courses').document(course_id).get()
    k = k.to_dict()
    k['course_id'] = course_id
    return k


def get_topics(course_id):
    "DocString"
    k = course_info(course_id)
    return k['topics']


def get_questions(course_id, topic, type_ques, level, prof_id=None):
    "DocString"
    final = []
    k = db.collection('courses').document(
        course_id).collection('ques_bank').stream()
    for i in k:
        question_data = i.to_dict()
        question_data['id'] = i.id
        if topic in question_data['topics'] and (level == 'ALL' or level == question_data['diff']):
            if prof_id is None:
                final.append(question_data)
            elif question_data['prof'] == prof_id:
                final.append(question_data)
            if type_ques == 'ALL':
                pass
            elif type_ques != question_data['type'] and question_data in final:
                final.remove(question_data)
    return final


def delete_questions(id_ls, course_id):
    "DocString"
    for i in id_ls:
        db.collection('courses').document(course_id).collection(
            'ques_bank').document(i).delete()


def update_questions(q_id, course_id, updated_dict):
    "DocString"
    db.collection('courses').document(course_id).collection(
        'ques_bank').document(q_id).update(updated_dict)


def chor(prof_id):
    "DocString"
    db.collection('chor').document(prof_id).set({'chor': 'Yes'})


def getQuestionById(courseId, questionIdList):
    Collection = db.collection('courses').document(courseId).collection('ques_bank').stream()  # Fetching the collection with questions from the database
    requiredQuestion = []
    question_list = []
    for k in Collection:
        question={k.id: k.to_dict()}
        question_list.append(question)
    for i in questionIdList:
        for k in question_list:
            key = list(k.keys())[0]
            if i == key:
                requiredQuestion.append(k)

    return requiredQuestion


def ques_for_eval(exam_info):
    "DocString"
    questions_paper = {}
    types_exam = list(exam_info['questions'].keys())
    for i in types_exam:
        questions_paper[i] = {}
        levels_type = list(exam_info['questions'][i].keys())
        levels_type.remove('marks')
        for j in levels_type:
            curr_type_level = []
            for topic in exam_info['topics']:
                generated = list(get_questions(
                    exam_info['courseId'], topic, i, j))
                for k in generated:
                    curr_question = {}
                    curr_question['ques'] = k['ques']
                    try:
                        curr_question['options'] = k['options']
                    except:
                        pass
                    curr_question['id'] = k['id']
                    if curr_question not in curr_type_level:
                        curr_type_level.append(curr_question)
            questions_paper[i][j] = curr_type_level

    return questions_paper


def set_paper(exam_info, questions_paper):
    "DocString"

    eval_paper = []
    counter = 0
    types_exam = list(exam_info['questions'].keys())

    for i in types_exam:
        levels_type = list(exam_info['questions'][i].keys())
        levels_type.remove('marks')
        for j in levels_type:
            for k in np.array_split(questions_paper[i][j], exam_info['questions'][i][j]):
                curr_ques_data = {}
                curr_ques_data["questionType"] = i
                curr_ques_data["marks"] = exam_info["questions"][i]["marks"]
                curr_ques_data["questions"] = k
                eval_paper.append(curr_ques_data)
    if len(eval_paper) == exam_info['totalQues']:
        for i in eval_paper:
            i['questions'] = list(i['questions'])
        return eval_paper
    else:
        return 0


def download_storage(exam_id, file_type):
    "Download file to local and then returning the data"
    path = f"exams/{exam_id}"

    isExist = os.path.exists(path)
    if not isExist:
        os.makedirs(path)

    try:
        file_path = f"{path}/{file_type}.json"
        blob = bucket.blob(file_path)
        blob.download_to_filename(file_path)
        return load_json(exam_id, file_type)
    except:
        return 0


def upload_storage(exam_id, json_data, file_type):
    "Uploading file to firebase"
    path = f"exams/{exam_id}/{file_type}.json"

    blob = bucket.blob(path)

    try:
        blob.delete()
    except:
        pass

    try:
        blob.upload_from_filename(path)
        return 1
    except:
        return 0


def create_json(exam_id, json_data, file_type):
    "Uploading data to local"

    path = f"exams/{exam_id}"
    isExist = os.path.exists(path)

    if not isExist:
        os.makedirs(path)

    json_string = json.dumps(json_data)

    with open(f'{path}/{file_type}.json', 'w') as f:
        json.dump(json_string, f, indent=4)
        return 1
    return 0


def load_json(exam_id, file_type):
    "Loading data from local"

    path = f"exams/{exam_id}/{file_type}.json"

    with open(path, 'r') as json_file:
        data = json.load(json_file)
        data = json.loads(data)
        return data
    return 0


def delete_json(exam_id, file_type):
    "Deleting data from local"

    path = f"exams/{exam_id}"
    isExist = os.path.exists(path)

    if isExist:
        os.remove(f'{path}/{file_type}.json')
        return 1
    return 0



def net_fun(exam_info, questions_paper):

    if create_json(exam_info['refId'], exam_info, 'info'):
        if upload_storage(exam_info['refId'], exam_info, 'info'):
            response2 = delete_json(exam_info['refId'], 'info')

    if create_json(exam_info['refId'], questions_paper, 'questions'):
        if upload_storage(exam_info['refId'], questions_paper, 'questions'):
            response1 = delete_json(exam_info['refId'], 'questions')
    clear()
    return response2*response1


def clear():

    dir = 'exams'
    for files in os.listdir(dir):
        path = os.path.join(dir, files)
        try:
            shutil.rmtree(path)
        except OSError:
            os.remove(path)


def exam_fire(exam_info):
    data = dict(exam_info)
    del data['prof_id']
    del data['topics']
    del data['questions']
    data['students'] = {}
    data['approved']=False
    data['created_at']=datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    data['year'] = int(curr_sem().split('-')[0])
    data['sem'] = int(curr_sem().split('-')[1])
    db.collection('courses').document(
        data['courseId']).collection('exams').document(data['refId']).set(data)


def exam_data(exam_info):
    k = db.collection('courses').document(exam_info['courseId']).collection('exams').document(exam_info['refId']).get()
    k = k.to_dict()
    del k['students']
    return k


# def all_exam_data(course_id):

def convert12(time_24):
    final = ""
    if time_24 == "00:00":
        return "12:00 AM"
    if int(time_24[0:2]) > 12:
        end = " PM"
        hour = int(time_24[0:2]) - 12
    elif int(time_24[0:2]) == 12:
        end = " PM"
        hour = int(time_24[0:2])
    else:
        end = " AM"
        hour = int(time_24[0:2])
    if hour < 10:
        final = "0" + str(hour) + time_24[2:5] + end
    else:
        final = str(hour) + time_24[2:5] + end
    return final

def get_exams(courseId):
    Collection = db.collection('courses').document(courseId).collection('exams').get()
    exams=[]
    for i in Collection:
        i = i.to_dict()
        exams.append(i)
    return exams

def get_students(courseId,examId):
    Collection = db.collection('courses').document(courseId).collection('exams').document(examId).get()
    Collection = Collection.to_dict()
    data=Collection['students']
    subjectiveQues=Collection['totalSubjective']
    return data,subjectiveQues

def response_download_storage(exam_id, student_id):
    "Download file to local and then returning the data"
    path = f"exams/{exam_id}"
    new_path=path+'/response'
    isExist = os.path.exists(new_path)
    if not isExist:
        os.makedirs(new_path)

    try:
        file_path = f"{path}/response/{student_id}.json"
        blob = bucket.blob(file_path)
        blob.download_to_filename(file_path)
        return load_json(exam_id, f'response/{student_id}')
    except:
        return 0
def update_eval(courseId,examId,studentId,marks):
    collection=db.collection('courses').document(courseId).collection('exams').document(examId)
    dictionary= collection.get({'students'})
    dictionary= dictionary.to_dict()
    dictionary=dictionary['students']
    dictionary[studentId]+=marks
    collection.update({'students':dictionary})


def create_eval(courseId,examId,studentId):
    collection=db.collection('courses').document(courseId).collection('exams').document(examId)
    dictionary= collection.get({'students'})
    dictionary= dictionary.to_dict()
    dictionary=dictionary['students']
    dictionary[studentId]=0
    collection.update({'students':dictionary})
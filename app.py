"DocString"
import os
import pathlib
from flask import Flask, render_template, request, redirect, abort, session, url_for
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
import google.auth.transport.requests
import requests
from pip._vendor import cachecontrol
import json
import datetime
import time
from db import upload, course_prof, course_info, get_topics, get_questions, net_fun, download_storage, upload_storage, create_json, clear,get_exams, response_download_storage,approved_fire
from db import delete_questions, convert12, update_questions, upload_one, chor, ques_for_eval, set_paper, clear, getQuestionById, exam_fire, exam_data,load_json,get_students,update_eval,create_eval
from generation import ques_gen
from assessment import ai_marks
import uuid

ques_info = {'question': []}

app = Flask(__name__)
app.secret_key = 'jk'

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

GOOGLE_CLIENT_ID = '614245365180-sqfhaa5ncfjkmbid59bmnk44feumdl1k.apps.googleusercontent.com'
client_secrets_file = os.path.join(
    pathlib.Path(__file__).parent, "secret/oauth.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="https://wilp-professor-end.onrender.com/callback"
    # redirect_uri="http://127.0.0.1:5000/callback"
)


@app.route('/login', methods=['GET', 'POST'])
def login():
    "DocString"
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    "DocString"
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(
        session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    session["name"] = id_info.get("name")
    email = id_info.get("email")
    session["id"] = email
    prof_id = session['id'].split('@')[0]
    session['prof_id'] = prof_id
    session['courses'] = course_prof(prof_id)
    if 'bits-pilani.ac.in' not in email:
        session.clear()
    return redirect("/home")


@app.route("/logout")
def logout():
    "DocString"
    session.clear()
    return redirect("/")


def login_is_required(function):
    "DocString"
    def wrapper(*args, **kwargs):
        if 'id' not in session:
            return render_template('home.html')
        return function(*args, **kwargs)
    wrapper.__name__ = function.__name__
    return wrapper


@app.route("/")
@app.route("/home")
def home():
    "DocString"
    if 'id' not in session:
        return render_template('home.html')
    teach = []
    for i in session['courses']:
        teach.append(course_info(i))
    return render_template('dashboard.html', teach=teach)


@app.route("/<course_id>/home_ques")
@login_is_required
def course_home_ques(course_id):
    "DocString"
    if course_id in session['courses']:
        return render_template('ques/home_ques.html', course_id=course_id)
    chor(session['prof_id'])
    return redirect(url_for('home'))


@app.route("/<course_id>/home_paper")
@login_is_required
def course_home_paper(course_id):
    "DocString"
    if course_id in session['courses']:
        return render_template('exam/home_exam.html', course_id=course_id)
    chor(session['prof_id'])
    return redirect(url_for('home'))


@app.route("/<course_id>/gen_ques", methods=['GET', 'POST'])
@login_is_required
def gen_ques(course_id):
    "DocString"

    courses = session['courses']
    topics = get_topics(course_id)

    if course_id in courses:
        which = []
        diff_assign = []
        if request.method == 'POST' and 'content' in request.form:
            content = request.form.get('content')
            ques_info['topics'] = set(request.form.get('topics').split(', '))
            ques_info['type'] = request.form.get('option')
            ques_info['diff'] = request.form.get("dif")
            ques_info['question'] = ques_gen(
                content, ques_info['type'], ques_info['diff'])
            deff = ques_info['diff']
            diff_dflt = {'1': "EASY" == deff,
                         '2': "MEDIUM" == deff, '3': "HARD" == deff}
            length = len(ques_info['question'])
            flag = 0
            while flag == 0:
                ques_info['question'] = []
                ques_info['question'] = ques_gen(
                    content, ques_info['type'], ques_info['diff'])
                for i in range(5):
                    keys = list(ques_info['question'][i])
                    flag = 1
            return render_template('ques/gen_ques.html', questions=ques_info['question'],
                                   ques_type=ques_info['type'], length=length, course_id=course_id,
                                   topics=get_topics(course_id), diff_check=diff_dflt)
        elif request.method == 'POST':
            while True:
                try:
                    for i in range(5):
                        if request.form.get(f'{i}') == 'on':
                            dif_id = "diff"+str(i)
                            diff_assign.append(request.form.get(dif_id))
                            which.append(i)
                    if len(which) > 0:
                        for i in range(len(which)):
                            ques_info['question'][which[i]
                                                  ]['diff'] = diff_assign[i]
                            id_update = upload(
                                ques_info['question'][which[i]], course_id, session['prof_id'], ques_info)
                            updated_dict = {}
                            updated_dict['diff'] = request.form.get(
                                f'diff{str(which[i])}')
                            updated_dict['ques'] = request.form.get(
                                f'question{str(which[i])}')
                            qtype = ques_info['type']
                            if qtype == "mcq" or qtype == "multi_mcq":
                                options = {}
                                options_list = ['A', 'B', 'C', 'D']
                                for j in range(4):
                                    options_get_param = 'answer' + \
                                        str(which[i])+options_list[j]
                                    options[options_list[j]] = request.form.get(
                                        options_get_param)
                                updated_dict['options'] = options
                                if qtype == 'mcq':
                                    updated_dict['correct'] = request.form.get(
                                        f'ans{str(which[i])}')
                                elif qtype == 'multi_mcq':
                                    correct_string = ""
                                    new_option = request.form.getlist(
                                        f'ans{str(which[i])}')
                                    for k in new_option:
                                        correct_string += k
                                    updated_dict['correct'] = correct_string
                            elif qtype == 'short' or qtype == 'long':
                                updated_dict['correct'] = request.form.get(
                                    f'answer2{str(which[i])}')
                            update_questions(
                                f'{id_update.id}', course_id, updated_dict)
                        return render_template('ques/gen_ques.html', questions=[], length=0,
                                               course_id=course_id, topics=get_topics(course_id))
                except:  # pylint: disable=bare-except
                    flag = 0
                    while flag == 0:
                        ques_info['question'] = []
                        ques_info['question'] = ques_gen(
                            content, ques_info['type'], ques_info['diff'])
                        for i in range(5):
                            keys = list(ques_info['question'][i])
                            flag = 1
                    return render_template('ques/gen_ques.html', length=length, course_id=course_id,
                                           diff_check=diff_dflt, questions=ques_info['question'],
                                           topics=get_topics(course_id), ques_type=ques_info['type'])

        else:
            return render_template('ques/gen_ques.html', questions=[], length=0,
                                   course_id=course_id, topics=topics)
    else:
        chor(session['prof_id'])
        return redirect(url_for('home'))


@app.route("/<course_id>/view_ques", methods=['GET', 'POST'])
@login_is_required
def view_ques(course_id):
    "DocString"
    if course_id in session['courses']:
        topics = get_topics(course_id)
        if request.method == 'POST':
            topic = request.form.get('topic')
            level = request.form.get("dif")
            qtype = request.form.get('option')
            question_data = get_questions(
                course_id, topic, qtype, level)
            return render_template('ques/view_ques.html', topics=topics, questions=question_data,
                                   length=len(question_data), ques_type=qtype)
        else:
            return render_template('ques/view_ques.html', topics=topics, length=0)
    else:
        chor(session['prof_id'])
        return redirect(url_for('home'))


@app.route("/<course_id>/edit_ques", methods=['GET', 'POST'])
@login_is_required
def edit_ques(course_id):
    "DocString"
    if course_id in session['courses']:
        topics = get_topics(course_id)
        prof_id = session['prof_id']
        if request.method == 'POST' and 'topic' in request.form:
            topic = request.form.get('topic')
            level = request.form.get("dif")
            qtype = request.form.get('option')
            global question_data
            question_data = get_questions(
                course_id, topic, qtype, level, prof_id)
            return render_template('ques/edit_ques.html',  topics=topics, questions=question_data,
                                   length=len(question_data), ques_type=qtype)
        elif request.method == "POST":
            which = []
            for i in range(len(question_data)):
                updated_dict = {}
                updated_dict['diff'] = request.form.get(f'dif{str(i)}')
                updated_dict['ques'] = request.form.get(f'question{str(i)}')
                qtype = question_data[i]['type']
                if qtype == "multi_mcq" or qtype == "mcq":
                    options = {}
                    options_list = ['A', 'B', 'C', 'D']
                    for j in range(4):
                        options_get_param = 'answer'+str(i)+options_list[j]
                        options[options_list[j]] = request.form.get(
                            options_get_param)
                    updated_dict['options'] = options
                    if qtype == 'mcq':
                        updated_dict['correct'] = request.form.get(
                            f'ans{str(i)}')
                    elif qtype == 'multi_mcq':
                        correct_string = ""
                        new_option = request.form.getlist(
                            f'ans{str(i)}')
                        for k in new_option:
                            correct_string += k
                        updated_dict['correct'] = correct_string
                elif qtype == 'short' or qtype == 'long':
                    updated_dict['correct'] = request.form.get(
                        f'answer2{str(i)}')
                update_questions(
                    question_data[i]['id'], course_id, updated_dict)
                if request.form.get(f'del{i}') == 'on':
                    which.append(question_data[i]['id'])
            delete_questions(which, course_id)
            return render_template('ques/edit_ques.html',  questions=[], length=0,
                                   course_id=course_id, topics=get_topics(course_id))
        else:
            return render_template('ques/edit_ques.html',  topics=topics, length=0)
    else:
        chor(session['prof_id'])
        return redirect(url_for('home'))


@app.route("/<course_id>/new_ques", methods=['GET', 'POST'])
@login_is_required
def new_ques(course_id):
    "DocString"

    topics = get_topics(course_id)
    if course_id in session['courses']:
        if request.method == 'POST':
            ques_info = {}
            ques_info['ques'] = request.form.get('ques')
            ques_info['prof'] = session['prof_id']
            ques_info['type'] = request.form.get('option')
            ques_info['diff'] = request.form.get('dif')
            ques_info['topics'] = set(request.form.get('topics').split(', '))
            if ques_info['type'] == 'mcq':
                option = int(request.form.get('radio'))
                ques_info['options'] = []
                for i in range(4):
                    ques_info['options'].append(request.form.get(f"{i}"))
                ques_info['correct'] = ques_info['options'][option]
            elif ques_info['type'] == 'short' or ques_info['type'] == 'long':
                ques_info['correct'] = request.form.get("correct")
            elif ques_info['type'] == 'multi_mcq':
                ques_info['options'] = []
                ques_info['correct'] = []
                for i in range(4):
                    ques_info['options'].append(request.form.get(f"mmq{i}"))
                checkbox = request.form.getlist('check')
                for i in checkbox:
                    ques_info['correct'].append(ques_info['options'][int(i)])
            upload_one(ques_info, course_id, topics)
        return render_template('ques/new_ques.html', topics=topics)
    else:
        chor(session['prof_id'])
        return redirect(url_for('home'))


@app.route("/<course_id>/set_exam", methods=['GET', 'POST'])
@login_is_required
def set_examination(course_id):
    "DocString"

    types = ['mcq', 'short', 'long', 'multi_mcq']
    levels = ['EASY', 'MEDIUM', 'HARD']
    topics = get_topics(course_id)

    if course_id in session['courses']:
        if request.method == 'POST':
            topics_exam = list(topics)
            if (request.form.get('all_topics')) is None:
                for i in topics:
                    if (request.form.get(i)) is None:
                        topics_exam.remove(i)
            if len(topics_exam) != 0:
                exam_id = str(uuid.uuid1())
                exam_info = {}
                exam_info['refId'] = exam_id
                exam_info['courseId'] = course_id
                exam_info['prof_id'] = session['prof_id']
                exam_info['examType'] = 'Mid-sem' if request.form.get('exam') == 'mid' else 'End-sem'
                exam_info['topics'] = topics_exam
                exam_info['questions'] = {}
                exam_info['totalQues'] = 0
                exam_info['totalSubjective'] = 0
                exam_info['totalMarks'] = 0
                exam_info['totalTime'] = (int(request.form.get('duration')))
                exam_time = request.form.get('time')
                exam_date = request.form.get('date')
                date_time = datetime.datetime(int(exam_date[0:4]), int(exam_date[5:7]), int(exam_date[8:]), int(exam_time[0:2]), int(exam_time[3:]), 00)
                exam_info['date'] = f"{int(exam_date[0:4])}/{int(exam_date[5:7])}/{int(exam_date[8:])}"
                exam_info['time'] = int(time.mktime(date_time.timetuple()))*1000
                for i in ['excel', 'open_book', 'compiler', 'calculator']:
                    exam_info[i] = True if request.form.get(i) == 'true' else False
                exam_info['company'] = "wilp"
                exam_info['subject'] = course_info(course_id)['name']
                for i in types:
                    marks = int(request.form.get(f"{i}-marks"))
                    if marks != 0:
                        exam_info['questions'][i] = {}
                        exam_info['questions'][i]['marks'] = marks
                        for j in levels:
                            total_type_level = int(
                                request.form.get(f"{i}-{j}-total"))
                            if total_type_level != 0:
                                exam_info['questions'][i][j] = total_type_level
                                exam_info['totalQues'] += total_type_level
                                if i == 'short' or i == 'long':
                                    exam_info['totalSubjective'] += total_type_level
                                exam_info['totalMarks'] += total_type_level * \
                                    exam_info['questions'][i]['marks']
                if exam_info['totalQues'] == 0:
                    clear()
                    return redirect(url_for('set_examination', course_id=course_id))
                exam_fire(exam_info)
                questions_paper = ques_for_eval(exam_info)

                if net_fun(exam_info, questions_paper):
                    clear()
                    return redirect(url_for('edit_exam', exam_id=exam_id, course_id=course_id))
                clear()
                return redirect(url_for('set_examination', course_id=course_id))
        clear()
        return render_template('exam/set_exam.html', topics=topics, data={'types': types, 'levels': levels})
    else:
        chor(session['prof_id'])
        return redirect(url_for('home'))


@app.route('/<course_id>/edit_home_exam', methods=['GET', 'POST'])
@login_is_required
def edit_home_exam(course_id):
    all_exam_info=get_exams(course_id)
    unapproved_exams = []
    for i in all_exam_info:
        if i['approved'] == False:
            unapproved_exams.append(i)
    return render_template('exam/edit_home_exam.html', course_id=course_id, all_exam_info=unapproved_exams)


@app.route('/<course_id>/edit_exam/<exam_id>', methods=['GET', 'POST'])
@login_is_required
def edit_exam(course_id, exam_id):
    exam_info = download_storage(exam_id, 'info')
    questions_paper = download_storage(exam_id, 'questions')
    if request.method == 'POST':
        for i in questions_paper:
            for j in questions_paper[i]:
                curr_type_level = list(questions_paper[i][j])
                for k in questions_paper[i][j]:
                    if request.form.get(k['id']) is None:
                        pass
                    else:
                        curr_type_level.remove(k)
                questions_paper[i][j] = curr_type_level

        if net_fun(exam_info, questions_paper):
            clear()
            return redirect(url_for('edit_exam', exam_id=exam_id, course_id=course_id))

    clear()
    return render_template('exam/edit_exam.html', questions_paper=questions_paper, exam_info=exam_info, exam_id=exam_id)


@app.route("/approved/<exam_id>", methods=['GET', 'POST'])
@login_is_required
def approved_exam(exam_id):
    exam_info = download_storage(exam_id, 'info')
    questions_paper = download_storage(exam_id, 'questions')
    eval_paper = set_paper(exam_info, questions_paper)
    if net_fun(exam_info, eval_paper):
        k = exam_data(exam_info)
        k['data'] = download_storage(exam_id, 'questions')
        for i in range(len(k['data'])):
            for j in k['data'][i]['questions']:
                j['question'] = j['ques']
                del j['ques']
        url = "https://exambackend-khqy.onrender.com/api/exams/setExam"
        payload = json.dumps(k)
        headers = {
            'Content-Type': 'application/json'
        }
        del k['created_at']
        requests.request("POST", url, headers=headers, data=payload)
        clear()
        approved_fire(exam_info)
        return redirect(url_for('course_home_paper', course_id=exam_info['courseId']))

    clear()
    return redirect(url_for('home'))


@app.route('/<course_id>/response_home_exam', methods=['GET', 'POST'])
@login_is_required
def response_home_exam(course_id):
    all_exam_info=get_exams(course_id)
    approved_exams = []
    for i in all_exam_info:
        if i['approved'] == True:
            approved_exams.append(i)
    return render_template('exam/response_home_exam.html', course_id=course_id, all_exam_info=approved_exams)



@app.route('/<course_id>/response/<exam_id>', methods=['GET', 'POST'])
@login_is_required
def responses_exam(course_id, exam_id):
    data,subjectiveQues=get_students(course_id, exam_id)
    quesInfo = download_storage(exam_id, 'info')
    if request.method=='POST':
        data,subjectiveQues=get_students(course_id, exam_id)
        for studentId in data:
            response = response_download_storage(exam_id, studentId)
            for i in response['userResponse']:
                quesId=i['quesId']
                quesIdList=[quesId]
                questionData = getQuestionById(course_id, quesIdList)
                type=questionData[0][quesId]['type']
                if type in ['mcq','multi_mcq']:
                    formatted_answer=''.join(sorted(i['response']))
                    formatted_correct=''.join(sorted(questionData[0][quesId]['correct']))
                    if formatted_answer == formatted_correct:
                        i['marks'] = quesInfo['questions'][type]['marks']
                    else:
                        i['marks'] = 0
            create_json(f'{exam_id}/response',response,studentId)
            upload_storage(f'{exam_id}/response', response,studentId)
            clear()
        return redirect(url_for('home'))
    return render_template('exam/responses_exam.html', exam_id=exam_id, course_id=course_id,data=data,subjectiveQues=subjectiveQues)


@app.route('/response', methods=['POST'])
def response_api():
    try:
        request_data = request.get_json()
        examId=request_data['refId']
        studentId=request_data['email']
        studentId=studentId.split('@')[0]
        path=examId+"/response"
        #courseId=request_data['courseId']
        courseId='GRANTH-TUSHAR'
        create_eval(courseId, examId, studentId)
        create_json(path,request_data,studentId)
        upload_storage(path, request_data,studentId)
        clear()
        return 'Success'
    except:
        return 'Failureupdate_eval(course_id, exam_id, student_id,evaluated)'


@app.route("/<course_id>/response/<exam_id>/<student_id>", methods=['GET', 'POST'])
@login_is_required
def student_response(exam_id, student_id, course_id):
    response = response_download_storage(exam_id, student_id)
    quesInfo = download_storage(exam_id, 'info')
    questionIdList = []
    for i in response['userResponse']:
        questionId = i["quesId"]
        questionIdList.append(questionId)

    questionData = getQuestionById(course_id, questionIdList)
    length = len(questionData)

    if request.method == 'POST':
        evaluated=0
        for i in range(length):
            quesId = questionIdList[i]
            try:
                if request.form.get(quesId) != '' and request.form.get(quesId) != None:
                    response['userResponse'][i]['marks'] = request.form.get(quesId)
                    evaluated+=1
            except:
                continue
        update_eval(course_id, exam_id, student_id,evaluated)
        create_json(exam_id, response, f'response/{student_id}')
        upload_storage(exam_id, response, f'response/{student_id}')
        clear()
        return redirect(url_for('responses_exam', exam_id=exam_id, course_id=course_id))

    aiMarks = {}
    for i in range(length):
        quesId = questionIdList[i]
        try:
            if 'marks' not in list(response['userResponse'][i].keys()):
                if questionData[i][quesId]['type'] in ['short', 'long']:
                        question = questionData[i][quesId]['ques']
                        answer = response['userResponse'][i]['response']
                        marks = quesInfo['questions']['long']['marks'] if questionData[i][quesId]['type'] == 'long' else quesInfo['questions']['short']['marks']
                        aiMarks[quesId] = ai_marks(answer, marks, question)
        except:
            continue

    evaluated_marks=[]
    for i in range(length):
        try:
            evaluated_marks.append(response['userResponse'][i]['marks'])
        except:
            evaluated_marks.append('')


    return render_template('exam/student_exam.html', response=response, questionData=questionData, quesInfo=quesInfo, aiMarks=aiMarks, length=length,evaluated_marks=evaluated_marks)



if __name__ == '__main__':
    app.run(debug=True)

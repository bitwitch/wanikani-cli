import copy
from collections import deque
from datetime import datetime
from enum import Enum
import logging
import json
import random
from sys import exit
from textwrap import fill


# third party
import dateutil.parser
from dateutil import tz
import requests

# development only
from pprint import pprint

class States(Enum):
    NORMAL = 0
    LESSON = 1
    REVIEW = 2

# globals
state = States.NORMAL
revQuestions = deque()
revAnswers = {}

# moves an assignment from the lesson to review queue
def startAssignment(baseUrl, apiToken, assignId):
    print('MOVING ASSIGNMENT FROM LESSON TO REVIEW QUEUE')
    pprint(assignId)

    # headers = {
        # 'Wanikani-Revision': '20170710',
        # 'Authorization': 'Bearer ' + apiToken }

    # r = requests.put(f'{baseUrl}/assignments/{assignId}/start', headers=headers)

    # if r.status_code < 200 or r.status_code >= 300:
        # errorString = 'Unable to start assignment.'
        # if 'error' in r.json():
            # errorString += f"\nResponse error: {r.status_code} {r.json()['error']}"
        # logging.error(errorString)
        # print(errorString)

# creates a new review record
def createReview(baseUrl, apiToken, assignId):
    print('CREATING REVIEW')
    pprint(assignId)

# prompts the user with questions, records correct/incorrect responses in answers,
# and calls correctAnswerCallback on each assignment for which all parts have been
# answered correctly 
def reviewBatch(baseUrl, apiToken, questions, answers, correctAnswerCallback):
    while len(questions) > 0:
        random.shuffle(questions)
        q = questions[0]
        assignId = q['assignment']['id']

        print(q['subject']['data']['characters'])
        print(q['type'].upper() + ':', end=' ')

        command = input().lower().strip()

        # only q is used to exit review state, because quit and exit
        # can be actual lesson words
        if command == 'q':
            state = States.NORMAL
            return

        # make sure the command is in the right charset given the question type
        while True:
            correctCharset = checkAnswerCharset(command, q['type'])
            if not correctCharset:
                print(q['subject']['data']['characters'])
                print(q['type'].upper() + ':', end=' ')
                command = input().lower().strip()
            else: break

        if q['type'] == 'meaning':
            meanings = q['subject']['data']['meanings']
            accepted = [m['meaning'].lower() for m in meanings]
        else:
            readings = q['subject']['data']['readings']
            accepted = [r['reading'].lower() for r in readings]
        if command in accepted:
            answers[assignId][ q['type'] ] = True
            questions.popleft()
            print('CORRECT!')
        else:
            if q['type'] == 'meaning':
                answers[assignId]['incorrectMeaning'] += 1
            else:
                answers[assignId]['incorrectReading'] += 1
            print(f"INCORRECT...\nAccepted answers: {', '.join(accepted)}")

        if (answers[assignId]['meaning'] == True):
            if (('reading' in answers[assignId] and 
                    answers[assignId]['reading'] == True) or
                    'reading' not in answers[assignId]):
                print('item complete. if review, create a new record. if lesson, move assignment to review state.')
                correctAnswerCallback(baseUrl, apiToken, assignId)

def lessonLearn(lessons):
    for q in lessons:
        assignId = q['assignment']['id']
        subjectType = q['assignment']['data']['subject_type']
        print(subjectType + ':')
        print(q['subject']['data']['characters'])
        # learn meaning
        print('meaning:')
        for m in q['subject']['data']['meanings']:
            if m['primary']:
                printWait(m['meaning'])
                break
        # meanings = [ m['meaning'] for m in q['subject']['data']['meanings'] ]
        # printWait(', '.join(meanings))
        print('Meaning Mnemonic:')
        printWait(q['subject']['data']['meaning_mnemonic'])
        if subjectType == 'radical': continue
        # learn reading
        print('Reading:')
        for r in q['subject']['readings']:
            if r['primary']:
                printWait(r['reading'])
                break
        # for r in q['subject']['readings']:
            # print(f"{r['type']}: {r['reading']}")
        # print('')
        if 'reading_mnemonic' in q['subject']['data']:
            print('Reading Mnemonic:')
            printWait(q['subject']['data']['meaning_mnemonic'])

def fetchSummary(baseUrl, apiToken):
    headers = {
        'Wanikani-Revision': '20170710',
        'Authorization': 'Bearer ' + apiToken
    }
    r = requests.get(baseUrl + '/summary', headers=headers)

    if r.status_code < 200 or r.status_code >= 300:
        errorString = 'Unable to retrieve summary from API.'
        if 'error' in r.json():
            errorString += f"\nResponse error: {r.status_code} {r.json()['error']}"
        logging.error(errorString)
        print(errorString)
        exit(1)

    return r.json()['data']

def printSummary(baseUrl, apiToken, executionTime):
    summary = fetchSummary(baseUrl, apiToken)

    lessonItemCount = 0
    for lesson in summary['lessons']:
        availableAt = dateutil.parser.isoparse(lesson['available_at'])
        if executionTime > availableAt:
            lessonItemCount += len( lesson['subject_ids'] )
    print(f'You have {lessonItemCount} lessons available.')

    reviewItemCount = 0
    for review in summary['reviews']:
        availableAt = dateutil.parser.isoparse(review['available_at'])
        if executionTime > availableAt:
            reviewItemCount += len( review['subject_ids'] )
    print(f'You have {reviewItemCount} reviews available.')

# assignType is one of: 'r', 'review', 'reviews', 'l', 'lesson', 'lessons'
def fetchAssignments(baseUrl, apiToken, assignType):
    if assignType == 'r' or assignType == 'reviews': assignType = 'review'
    if assignType == 'l' or assignType == 'lesson': assignType = 'lessons'

    headers = {
        'Wanikani-Revision': '20170710',
        'Authorization': 'Bearer ' + apiToken }
    params = { f'immediately_available_for_{assignType}': '' }

    r = requests.get(f'{baseUrl}/assignments', headers=headers, params=params)

    if r.status_code < 200 or r.status_code >= 300:
        errorString = 'Unable to retrieve review assignments from API.'
        if 'error' in r.json():
            errorString += f"\nResponse error: {r.status_code} {r.json()['error']}"
        logging.error(errorString)
        print(errorString)
        return None

    return r.json()['data']

def fetchSubject(baseUrl, apiToken, subjectId):
    headers = {
        'Wanikani-Revision': '20170710',
        'Authorization': 'Bearer ' + apiToken }

    r = requests.get(f'{baseUrl}/subjects/{subjectId}', headers=headers)

    if r.status_code < 200 or r.status_code >= 300:
        errorString = 'Unable to retrieve subject from API.'
        if 'error' in r.json():
            errorString += f"\nResponse error: {r.status_code} {r.json()['error']}"
        logging.error(errorString)
        print(errorString)
        return None

    return r.json()

# checks command to see if it is in the correct charset given the question type
# returns boolean
def checkAnswerCharset(command, qType):
    if qType == 'reading':
        for c in command:
            charcode = ord(c)
            if charcode >= 32 and charcode <= 127:
                print('Careful! This is a reading and you entered arabic letters.')
                return False
    else:
        for c in command:
            charcode = ord(c)
            if charcode < 32 or charcode > 127:
                print('Careful! This is a meaning and you entered non-arabic letters.')
                return False
    return True

def printWait(text):
    print(fill(text, 78))
    print('\npress enter to continue...')
    input()

def _non_serializable(o):
    culprit = f"<<non-serializable: {type(o).__qualname__}>>"
    errorString = (
        'Encountered an unserializable object while writing to database.\n' +
        culprit)
    logging.error(errorString)
    return culprit

def updateDb(filename, data, oldData):
    fp = open(filename, 'w')
    try:
        json.dump(data, fp, default=_non_serializable)
    except Exception as e:
        fp.seek(0)
        json.dump(oldData, fp)
        logging.error(f'Unable to update database.\n{e}') 
        print(f'Unable to update database.\n{e}') 
    finally:
        fp.close()

# Commands 
#-------------------------------------------------------------------------------

def cmdHelp():
    helpString = """\nCOMMANDS
    help           list commands
    lesson         start lessons
    review         start reviews
    quit/exit      exit program
"""
    print(helpString)

def cmdLesson():
    global state
    print('starting lessons...')
    state = States.LESSON

def cmdReview():
    global state
    print('starting reviews...')
    state = States.REVIEW

commands = {
    'help':    cmdHelp,
    'h':       cmdHelp,
    'lesson':  cmdLesson,
    'lessons': cmdLesson,
    'l':       cmdLesson,
    'review':  cmdReview,
    'reviews': cmdReview,
    'r':       cmdReview,
}

# Program states
#-------------------------------------------------------------------------------
def stateLesson(baseUrl, apiToken, assignments):
    global state

    if len(assignments) == 0:
        print('Completed all available lessons!')
        state = States.NORMAL
        return

    # get five assignments from queue (or all if less than 5 left)
    # create a data structure that holds booleans for reading and meaning answers
    lesToLearn = []
    lesQuestions = deque()
    lesAnswers = {}
    lesBatchSize = 5
    for i in range(lesBatchSize):
        if i+1 >= len(assignments): continue
        a = assignments[i]
        s = fetchSubject(baseUrl, apiToken, a['data']['subject_id'])

        lesToLearn.append({ 'assignment': a, 'subject': s })
        lesQuestions.append({ 'type': 'meaning', 'assignment': a, 'subject': s })
        lesAnswers[a['id']] = { 
            'meaning': False,  # user has answered the meaning correctly
            'incorrectMeaning': 0 }
        if a['data']['subject_type'] != 'radical':
            lesQuestions.append({ 'type': 'reading', 'assignment': a, 'subject': s })
            lesAnswers[a['id']] = { 
                'reading': False,  # user has answered the meaning correctly
                'incorrectReading': 0 }

    # learn items in this lesson batch
    lessonLearn(lesToLearn)

    # review items in this lesson batch
    reviewBatch(baseUrl, apiToken, lesQuestions, lesAnswers, startAssignment)

    # remove completed lessons from assignments deque
    for i in range(lesBatchSize):
        assignments.popleft()

def stateReview(baseUrl, apiToken, assignments):
    global state, revQuestions, revAnswers

    if len(assignments) == 0:
        print('Completed all available reviews!')
        state = States.NORMAL
        return

    # get five assignments from queue (or all if less than 5 left)
    # create a data structure that holds booleans for reading and meaning answers
    revQuestions = deque()
    revAnswers = {}
    revBatchSize = 5
    for i in range(revBatchSize):
        if i+1 >= len(assignments): continue

        a = assignments[i]
        s = fetchSubject(baseUrl, apiToken, a['data']['subject_id'])
        
        revAnswers[a['id']] = { 
            'meaning': False,  # user has answered the meaning correctly
            'reading': False,  # user has answered the reading correctly
            'incorrectMeaning': 0,
            'incorrectReading': 0 } 
        revQuestions.append({ 'type': 'meaning', 'assignment': a, 'subject': s })
        revQuestions.append({ 'type': 'reading', 'assignment': a, 'subject': s })

    reviewBatch(baseUrl, apiToken, revQuestions, revAnswers, createReview)

    # remove completed reviews from assignments deque
    for i in range(revBatchSize):
        assignments.popleft()

def stateNormal():
    quit = False
    command = input().strip()
    if command == 'exit' or command == 'quit' or command == 'q':
        quit = True
    elif command in commands:
        commands[command]()
    else:
        print('Unrecognized command')
    return quit

#-------------------------------------------------------------------------------

def main():
    global state

    # NOTE(shaw): could make a user request here to use username in welcome
    # also the user info gives you things like the lesson batch size
    print('\nお帰り, シャさん!')

    fp = open('token', 'r')
    apiToken = fp.read().strip()
    fp.close()

    baseUrl = 'https://api.wanikani.com/v2'

    try:
        fp = open('wk_data.json', 'r')
        oldWkData = json.load(fp)
    except FileNotFoundError:
        fp = open('wk_data.json', 'w')
        emptyDbData = { 'lastExecution': datetime.now(tz.UTC).isoformat() }
        json.dump(emptyDbData, fp)
        oldWkData = emptyDbData 
    finally:
        fp.close()

    # oldWkData is only used as a backup in the case when an error occurs 
    # while writing to the db. otherwise, wkData should always be used
    wkData = copy.deepcopy(oldWkData)

    # start time of this execution
    executionTime = datetime.now(tz.UTC)

    printSummary(baseUrl, apiToken, executionTime)

    cmdHelp()

    reviewsFetched = False
    lessonsFetched = False
    currentReviews = deque()
    currentLessons = deque()

    # main loop
    while True:
        if state == States.LESSON:
            if not lessonsFetched: 
                currentLessons = deque( fetchAssignments(baseUrl, apiToken, 'lessons') )
                print(f'Request returned {len(currentLessons)} lesson assignments.')
                lessonsFetched = True
            else:
               stateLesson(baseUrl, apiToken, currentLessons)
        elif state == States.REVIEW:
            if not reviewsFetched: 
                currentReviews = deque( fetchAssignments(baseUrl, apiToken, 'review') )
                print(f'Request returned {len(currentReviews)} review assignments.')
                reviewsFetched = True
            else:
                stateReview(baseUrl, apiToken, currentReviews)
        else: # normal state
            quit = stateNormal()

        if quit: break

    # update database
    wkData['lastExecution'] = executionTime.isoformat()
    updateDb('wk_data.json', wkData, oldWkData)

if __name__ == '__main__':
    logging.basicConfig(
        filename='error.log',
        filemode='a',          # open for writing, appending to end of file
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%d-%b-%y %H:%M:%S')
    main()



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
    NORMAL  = 0
    LESSON  = 1
    REVIEW  = 2
    SUMMARY = 3

# globals
state = States.NORMAL

def cls():
    print("\x1b[2J\x1b[H")

# moves an assignment from the lesson to review queue
def startAssignment(baseUrl, apiToken, assignId, answer=None):
    # print('moving assignment from lesson to review queue\n')
    headers = {
        'Wanikani-Revision': '20170710',
        'Authorization': 'Bearer ' + apiToken }

    r = requests.put(f'{baseUrl}/assignments/{assignId}/start', headers=headers)

    if r.status_code < 200 or r.status_code >= 300:
        errorString = f'Unable to start assignment. Assignment id: {assignId}'
        if 'error' in r.json():
            errorString += f"\nResponse error: {r.status_code} {r.json()['error']}"
        logging.error(errorString)
        print(errorString)

# creates a new review record
def createReview(baseUrl, apiToken, assignId, answer):
    # print('creating review\n')
    headers = {
        'Wanikani-Revision': '20170710',
        'Authorization': 'Bearer ' + apiToken, 
        'Content-Type': 'application/json; charset=utf-8' }

    payload = {
        'review': {
            'assignment_id': assignId,
            'incorrect_meaning_answers': answer['incorrectMeaning'],
            'incorrect_reading_answers': answer['incorrectReading'] }}

    r = requests.post(f'{baseUrl}/reviews', headers=headers, json=payload)

    if r.status_code < 200 or r.status_code >= 300:
        errorString = f'Unable to create a review record. Assignment id: {assignId}'
        if 'error' in r.json():
            errorString += f"\nResponse error: {r.status_code} {r.json()['error']}"
        logging.error(errorString)
        print(errorString)

# prompts the user with questions, records correct/incorrect responses in answers,
# and calls correctAnswerCallback on each assignment for which all parts have been
# answered correctly 
#
# common callbacks: createReview, startAssignment
#
# returns False normally, returns True if user entered a quit command
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
        if command == 'q': return True

        # make sure the command is in the right charset given the question type
        while True:
            correctCharset = checkAnswerCharset(command, q['type'])
            if not correctCharset:
                print(q['subject']['data']['characters'])
                print(q['type'].upper() + ':', end=' ')
                command = input().lower().strip()
                if command == 'q': return True # quit == True
            else: break

        if q['type'] == 'meaning':
            meanings = q['subject']['data']['meanings']
            accepted = [m['meaning'].lower() for m in meanings]
        else:
            readings = q['subject']['data']['readings']
            accepted = [r['reading'] for r in readings]

        if command in accepted:
            answers[assignId][ q['type'] ] = True
            questions.popleft()
            print('CORRECT!\n')
        else:
            if q['type'] == 'meaning':
                answers[assignId]['incorrectMeaning'] += 1
            else:
                answers[assignId]['incorrectReading'] += 1
            print(f"INCORRECT...\nAccepted answers: {', '.join(accepted)}\n")

        if (answers[assignId]['meaning'] == True and
                (answers[assignId]['reading'] == True or
                 answers[assignId]['subjectType'] == 'radical')):
            correctAnswerCallback(baseUrl, apiToken, assignId, answers[assignId])
    return False # quit == False

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
                print(m['meaning'])
                break
        # meanings = [ m['meaning'] for m in q['subject']['data']['meanings'] ]
        # printWait(', '.join(meanings))
        print('\nMeaning Mnemonic:')
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

def fetchUser(baseUrl, apiToken):
    headers = {
        'Wanikani-Revision': '20170710',
        'Authorization': 'Bearer ' + apiToken
    }
    r = requests.get(baseUrl + '/user', headers=headers)

    if r.status_code < 200 or r.status_code >= 300:
        errorString = 'Unable to retrieve user information from API.'
        if 'error' in r.json():
            errorString += f"\nResponse error: {r.status_code} {r.json()['error']}"
        logging.error(errorString)
        print(errorString)
        exit(1)

    return r.json()['data']

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

def printSummary(baseUrl, apiToken, end='\n'):
    summary = fetchSummary(baseUrl, apiToken)

    executionTime = datetime.now(tz.UTC)

    lessonItemCount = 0
    for lesson in summary['lessons']:
        availableAt = dateutil.parser.isoparse(lesson['available_at'])
        if executionTime > availableAt:
            lessonItemCount += len( lesson['subject_ids'] )
    print(f'\nYou have {lessonItemCount} lessons available.')

    reviewItemCount = 0
    for review in summary['reviews']:
        availableAt = dateutil.parser.isoparse(review['available_at'])
        if executionTime > availableAt:
            reviewItemCount += len( review['subject_ids'] )
    print(f'You have {reviewItemCount} reviews available.{end}')

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
        return []

    return r.json()['data']

# searches the lookup file for the primary meaning of the subject
# and updates the subject dict if found
def lookupCharacters(subject):
    filename = 'radicals_lookup.json'
    try:
        fp = open(filename, 'r')
        radicalsLookup = json.load(fp)
        fp.close()
    except FileNotFoundError:
        logging.error(f'Could not find radical lookup file: {filename}')
        return 
    except json.decoder.JSONDecodeError as e:
        logging.error(f'Could not read radical lookup file: {filename}\n{e}')
        fp.close
        return 
    meaning = ''
    for m in subject['data']['meanings']:
        if m['primary']: meaning = m['meaning'].lower()
    if meaning in radicalsLookup:
        subject['data']['characters'] = radicalsLookup[meaning]

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

    subject = r.json()

    # attempt to handle radicals without unicode characters
    if subject['data']['characters'] == None:
        lookupCharacters(subject)

    return subject

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

# Commands 
#-------------------------------------------------------------------------------

def cmdHelp():
    helpString = """\nCOMMANDS
    help           list commands
    lesson         start lessons
    review         start reviews
    summary        print summary of available lessons and reviews
    quit/exit      exit program
"""
    print(helpString)

def cmdSummary():
    global state
    state = States.SUMMARY

def cmdLesson():
    global state
    print('starting lessons...\n')
    state = States.LESSON

def cmdReview():
    global state
    print('starting reviews...\n')
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
    'summary': cmdSummary,
    's':       cmdSummary,
}

# Program states
#-------------------------------------------------------------------------------
def stateLesson(baseUrl, apiToken, assignments, lesBatchSize=5):
    global state

    if len(assignments) == 0:
        print('Completed all available lessons!\n')
        state = States.NORMAL
        return

    # get five assignments from queue (or all if less than 5 left)
    # create a data structure that holds booleans for reading and meaning answers
    lesToLearn = []
    lesQuestions = deque()
    lesAnswers = {}
    for i in range(lesBatchSize):
        if i+1 > len(assignments): continue
        a = assignments[i]
        s = fetchSubject(baseUrl, apiToken, a['data']['subject_id'])

        lesToLearn.append({ 'assignment': a, 'subject': s })
        lesAnswers[a['id']] = {
            'subjectType': a['data']['subject_type'],
            'meaning': False,  # user has answered the meaning correctly
            'reading': False,  # user has answered the reading correctly
            'incorrectMeaning': 0,
            'incorrectReading': 0 }
        lesQuestions.append({ 'type': 'meaning', 'assignment': a, 'subject': s })
        if a['data']['subject_type'] != 'radical':
            lesQuestions.append({ 'type': 'reading', 'assignment': a, 'subject': s })

    # learn items in this lesson batch
    lessonLearn(lesToLearn)

    # review items in this lesson batch
    quit = reviewBatch(baseUrl, apiToken, lesQuestions, lesAnswers, startAssignment)

    if quit:
        state = States.NORMAL
        print('exiting lessons.\n')
        return

    # remove completed lessons from assignments deque
    for i in range(lesBatchSize):
        if len(assignments) == 0: break
        assignments.popleft()

def stateReview(baseUrl, apiToken, assignments):
    global state

    if len(assignments) == 0:
        print('Completed all available reviews!\n')
        state = States.NORMAL
        return

    # get five assignments from queue (or all if less than 5 left)
    # create a data structure that holds booleans for reading and meaning answers
    revQuestions = deque()
    revAnswers = {}
    revBatchSize = 5
    for i in range(revBatchSize):
        if i+1 > len(assignments): continue

        a = assignments[i]
        s = fetchSubject(baseUrl, apiToken, a['data']['subject_id'])
        
        revAnswers[a['id']] = { 
            'subjectType': a['data']['subject_type'],
            'meaning': False,  # user has answered the meaning correctly
            'reading': False,  # user has answered the reading correctly
            'incorrectMeaning': 0,
            'incorrectReading': 0 }
        revQuestions.append({ 'type': 'meaning', 'assignment': a, 'subject': s })
        if a['data']['subject_type'] != 'radical':
            revQuestions.append({ 'type': 'reading', 'assignment': a, 'subject': s })

    quit = reviewBatch(baseUrl, apiToken, revQuestions, revAnswers, createReview)

    if quit:
        state = States.NORMAL
        print('exiting reviews.\n')
        return

    # remove completed reviews from assignments deque
    for i in range(revBatchSize):
        if len(assignments) == 0: break
        assignments.popleft()

def stateSummary(baseUrl, apiToken):
    global state
    printSummary(baseUrl, apiToken)
    state = States.NORMAL

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

    fp = open('token', 'r')
    apiToken = fp.read().strip()
    fp.close()

    baseUrl = 'https://api.wanikani.com/v2'

    user = fetchUser(baseUrl, apiToken)

    if user['username'] == 'bitwitch':
        print('\nお帰り, シャックン!')
    else:
        print(f"\nお帰りなさい, {user['username']}!")

    lesBatchSize = user['preferences']['lessons_batch_size']

    printSummary(baseUrl, apiToken, end='')

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
                lessonsFetched = True
            else:
                stateLesson(baseUrl, apiToken, currentLessons, lesBatchSize)
        elif state == States.REVIEW:
            if not reviewsFetched:
                currentReviews = deque( fetchAssignments(baseUrl, apiToken, 'review') )
                reviewsFetched = True
            else:
                stateReview(baseUrl, apiToken, currentReviews)
        elif state == States.SUMMARY:
            stateSummary(baseUrl, apiToken)
        else: # normal state
            quit = stateNormal()

        if quit: break

if __name__ == '__main__':
    logging.basicConfig(
        filename='error.log',
        filemode='a',          # open for writing, appending to end of file
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%d-%b-%y %H:%M:%S')
    main()


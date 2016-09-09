
# coding=utf-8

import xml.parsers.expat
import argparse
import sys

PLUGIN_NAME = "Jflap"

of = None  # global output file name


# 3 handler functions
def tm_start_element(name, attrs):
    global STATES, TYPES, current_state_id, seeking_start_state, \
           seeking_end_state, seeking_trans, seeking_read, seeking_write, \
           seeking_move
    # print 'Start element:', name, attrs
    if name == "block":
        string = attrs['id']
        state_placeholder = [int(s) for s in string.split() if s.isdigit()]
        STATES += state_placeholder
        current_state_id = state_placeholder[0]
    if name == "from":
        seeking_start_state = True
    if name == "to":
        seeking_end_state = True
    if name == "read":
        seeking_read = True
    if name == "write":
        seeking_write = True
    if name == "move":
        seeking_move = True
    if name == "initial":
        # print "State #", current_state_id,"is an initial state"
        TYPES[current_state_id] = ["initial"]
    if name == "final":
        # print "State #", current_state_id, "is a final state"
        if TYPES.has_key(current_state_id):
            TYPES[current_state_id] += ["final"]
        else:
            TYPES[current_state_id] = ["final"]
def tm_end_element(name):
    # print 'End element:', name
    pass
def tm_char_data(data):
    global TRANS, current_state_id, \
           current_start_state, current_end_state, \
           seeking_start_state, current_trans, seeking_trans, \
           seeking_end_state, current_read , seeking_read, \
           current_write, seeking_write, current_move, seeking_move
    data_without_space = data.strip()
    if len(data_without_space) > 0:
        # print 'Character data:', repr(data)
        pass
    if seeking_start_state:
        string = data_without_space
        state_placeholder = [int(s) for s in string.split() if s.isdigit()]
        current_start_state = state_placeholder[0]
        seeking_start_state = False
    if seeking_end_state:
        string = data_without_space
        state_placeholder = [int(s) for s in string.split() if s.isdigit()]
        current_end_state = state_placeholder[0]
        seeking_end_state = False
    if seeking_read:
        string = data_without_space
        state_placeholder = [s for s in string.split()]
        # print state_placeholder
        if len(state_placeholder)<1:
            state_placeholder = ['']
        current_read = state_placeholder[0]
        seeking_read = False
    if seeking_write:
        string = data_without_space
        state_placeholder = [s for s in string.split()]
        if len(state_placeholder)<1:
            state_placeholder = ['']
        current_write = state_placeholder[0]
        seeking_write = False
    if seeking_move:
        string = data_without_space
        state_placeholder = [s for s in string.split() if s.isalpha()]
        # print state_placeholder
        current_move = state_placeholder[0]
        if (current_start_state,current_end_state) in TRANS:
            TRANS[current_start_state,current_end_state] += [[current_read, current_write, current_move]]
        else:
            TRANS[current_start_state, current_end_state] = [[current_read, current_write, current_move]]
        seeking_move = False


def tm_TRANSprocessing():
    global TRANS, TRANS2
    TRANS2 = []
    for k in TRANS.iteritems():
        TRANS2.extend([k])
    for k in range(len(TRANS2)):
        trans_list = TRANS2[k][1]
        #print "trans_list is", trans_list
        for j in range(len(trans_list)):
          if trans_list[j][0] == '': trans_list[j][0] = '*'
          if trans_list[j][1] == '': trans_list[j][1] = '*'

def tm_takingInput(filename):
    global INPUTS,INPUTS2
    INPUTS2 = {}
    f = open(filename)
    L = f.readlines()
    for line in L:
        line = line.strip()
        pieces = line.split()
        if len(pieces)==2:
            if not pieces[0].isdigit():
                pieces = ['',pieces[1]]
        if len(pieces)==3:
            pieces = [pieces[0],pieces[2]]
        # print pieces
        INPUTS.extend([pieces])
    for i in range(len(INPUTS)):
        if len(INPUTS[i]) == 0:
            INPUTS2[""] = True
        elif len(INPUTS[i]) == 1:
            if INPUTS[i][0] != 'reject':
                INPUTS2[INPUTS[i][0]] = True
            elif INPUTS[i][0] == 'reject':
                INPUTS2[""] = False
            else:
                print "ERROR", INPUTS[i]
        elif INPUTS[i][1]=='reject':
            INPUTS2[INPUTS[i][0]] = False
        else:
            print "ERROR", INPUTS[i]
            INPUTS2[INPUTS[i][0]] = 'UNDEFINED. ERROR'
    f.close()
    # print 'INPUTS are', INPUTS
    # print 'INPUTS2 are', INPUTS2

def tm_stateTrans2(sState, left, right):
    global BEENTO
    global steps
    THRESHOLD = 25000  # max # of steps...
    TOO_MANY = "Too many steps!"
    possibleTrans = []


    if (sState, left, right) in BEENTO: return "Infinite Loop!"
    BEENTO[ (sState, left, right) ] = True # remember this state!

    # extend the right side as far as we need...
    if len(right)<1: right = right + '*'
    if len(left)<1: left = '*' + left

    # KEY DEBUGGING LINE: the state of the TM each time...
    #print left, "(" + str(sState) + ")", right

    # off on the right side with only blanks...
    #
    #if right == '**' and sState in TYPES:
    #    #print sState, sState in TYPES, 'final' in TYPES[sState]
    #    if sState in TYPES and 'final' in TYPES[sState]:
    #        return True

    if sState in TYPES and 'final' in TYPES[sState]:
        return True

    elif steps >= THRESHOLD:
        print "...",
        return TOO_MANY  # a string...

    elif steps < THRESHOLD:
        N = len(TRANS2)
        num_of_matching_transitions = 0
        for k in range(N):
            cur_trans = TRANS2[k]
            src, dst = cur_trans[0]
            cur_char = right[0]  # current character under the read head
            trans_list = cur_trans[1]

            if src != sState: continue # keep going!

            #print " TR:", cur_trans,
            N2 = len( trans_list )
            for j in range(N2):
              cur_arrow = trans_list[j]
              cur_char_to_read = cur_arrow[0]
              cur_char_to_write = cur_arrow[1]
              cur_dir_to_move = cur_arrow[2]
              if cur_char == cur_char_to_read:
                #print "\t\t\ttr: ", cur_arrow
                num_of_matching_transitions += 1 # are there any matching transitions?
                steps += 1  # global for counting maximum number of steps
                rest_of_right = right[1:]

                if cur_dir_to_move == 'R':
                    s = tm_stateTrans2(dst,left+cur_char_to_write,rest_of_right)
                    if s in [True,TOO_MANY]: return s
                elif cur_dir_to_move == 'L':
                    s = tm_stateTrans2(dst,left[:-1],left[-1]+cur_char_to_write+rest_of_right)
                    if s in [True,TOO_MANY]: return s
                else:  # it's 'S' for "Stay put"
                    s = tm_stateTrans2(dst,left,cur_char_to_write+rest_of_right)
                    if s in [True,TOO_MANY]: return s

        if num_of_matching_transitions == 0:
            return False

    # not sure we should get here, but just in case...
    return False



def tm_checker(filename):
    global steps
    global BEENTO
    count = 0
    tm_takingInput(filename)
    num_inputs = len(INPUTS2)

    # WOW! must find the start state!!
    start_state = 0
    for key in TYPES:
        value = TYPES[key]
        if 'initial' in value: start_state = key

    for i in INPUTS2.iterkeys():
        BEENTO = {}
        steps = 0
        result = tm_stateTrans2(start_state,'',i)
        expected = INPUTS2[i]
        tm_print_result_line( i, result, expected )
        if INPUTS2[i] == result:
            count +=1
    return count, num_inputs

def tm_print_result_line( inpt, result, expected ):
    """ print a nice rendition of a result line """
    if 8 <= len(inpt) <= 15:
        input_w_tabs = inpt + "\t\t"
    elif len(inpt) <= 7:
        input_w_tabs = inpt + "\t\t\t"
    else:
        input_w_tabs = inpt + "\t"

    global of
    if of != None:  # if there is an output file
        print >> of, input_w_tabs + str(result) + "\t" + \
                     str(expected) + "\t",
        if expected == result: print >> of, "correct"
        else: print >> of, " *** INCORRECT *** "
    else:
        print input_w_tabs + str(result) + "\t" + \
                     str(expected) + "\t",
        if expected == result: print "correct"
        else: print " *** INCORRECT *** "


def tm_overall(filename1,filename2):
    global INPUTS, TRANS, STATES, TYPES, TRANS2, count, success, BEENTO, \
           current_state_id, current_start_state, current_end_state, seeking_start_state, \
           seeking_end_state, seeking_trans, current_trans, seeking_read, seeking_write, \
           current_read, current_write, seeking_move, current_move
    STATES = []
    TYPES = {}
    TRANS = {}
    TRANS2 = []
    INPUTS = []
    count = 0
    success = False
    current_state_id = None
    current_start_state = None
    current_end_state = None
    seeking_start_state = False
    seeking_end_state = False
    seeking_trans = False
    current_trans = None
    seeking_read = False
    current_read = None
    seeking_write = False
    current_write = None
    seeking_move = False
    current_move = None

    p = xml.parsers.expat.ParserCreate()

    p.StartElementHandler = tm_start_element
    p.EndElementHandler = tm_end_element
    p.CharacterDataHandler = tm_char_data

    f = open(filename1)
    p.ParseFile(f)
    f.close()

    tm_TRANSprocessing()

    num_states = len(STATES)
    #print "TYPES are", TYPES
    #print "TRANS are", TRANS
    #print "processed TRANS are", TRANS2
    score, out_of  = tm_checker(filename2)
    return score, out_of, num_states



# 3 handler functions
def start_element(name, attrs):
    global STATES, TYPES, current_state_id, seeking_start_state, \
           seeking_end_state, seeking_trans
    # print 'Start element:', name, attrs
    if name == "state":
        string = attrs['id']
        state_placeholder = [int(s) for s in string.split() if s.isdigit()]
        STATES += state_placeholder
        current_state_id = state_placeholder[0]
    if name == "from":
        seeking_start_state = True
    if name == "to":
        seeking_end_state = True
    if name == "read":
        seeking_trans = True
    if name == "initial":
        #print "State #", current_state_id,"is an initial state"
        TYPES[current_state_id] = ["initial"]
    if name == "final":
        # print "State #", current_state_id, "is a final state"
        if TYPES.has_key(current_state_id):
            TYPES[current_state_id] += ["final"]
        else:
            TYPES[current_state_id] = ["final"]

def end_element(name):
    # print 'End element:', name
    pass

def char_data(data):
    global TRANS, current_state_id, \
           current_start_state, current_end_state, \
           seeking_start_state, current_trans, seeking_trans, \
           seeking_end_state

    data_without_space = data.strip()
    if len(data_without_space) > 0:
        state_desc = "seeking_start_state"
        if seeking_end_state: state_desc = "seeking_end_state"
        if seeking_trans: state_desc = "seeking_trans"
        #print 'Data: (', data, ") and state=", state_desc
        pass

    if seeking_start_state:
        string = data_without_space
        state_placeholder = [int(s) for s in string.split() if s.isdigit()]
        current_start_state = state_placeholder[0]
        seeking_start_state = False

    if seeking_end_state:
        string = data_without_space
        state_placeholder = [int(s) for s in string.split() if s.isdigit()]
        current_end_state = state_placeholder[0]
        seeking_end_state = False

    if seeking_trans:
        string = data_without_space
        if string.strip() == '':
          this_trans = 'X'
        else:
          s = string.strip()
          this_trans = str(s)

        if (current_start_state,current_end_state) not in TRANS:
            TRANS[current_start_state,current_end_state] = [this_trans]
        else:
            TRANS[current_start_state,current_end_state] += [this_trans]
        seeking_trans = False


def TRANSprocessing():
    global TRANS, TRANS2
    TRANS2 = []
    for k in TRANS.iteritems():
        TRANS2.extend([k])

def takingInput(filename):
    global INPUTS,INPUTS2
    INPUTS2 = {}
    f = open(filename)
    L = f.readlines()
    for line in L:
        line = line.strip()
        pieces = line.split()
        if len(pieces)==1:
            if not pieces[0].isdigit():
                pieces = ['','reject']
        if len(pieces)==0:
            pieces = ['']
        INPUTS.extend([pieces])
    for i in range(len(INPUTS)):
        if len(INPUTS[i])<2:
            INPUTS2[INPUTS[i][0]] = True
        else:
            INPUTS2[INPUTS[i][0]] = False
    f.close()
##    print 'INPUTS are', INPUTS
##    print 'INPUTS2 are', INPUTS2

def stateTrans2(sState, inputstring):
    # BEENTO should store both the current state AND the inputstring.
    # so when it returns again, it'll def. be a loop.
    global BEENTO

    """
    print
    print "sState = ", sState
    print "inputstring = ", inputstring
    """

    if (inputstring,sState) in BEENTO:
      return False   # already been here!

    BEENTO[ (inputstring,sState) ] = True  # now we've been here!

    if len(inputstring) == 0:  # done!
        for k in range(len(TRANS2)):
            if TRANS2[k][0][0] == sState and TRANS2[k][1] == 'X':
                #print inputstring, 'current state', sState, TRANS2[k], TRANS2[k][1] == 'X'
                newState = TRANS2[k][0][1]
                #print inputstring, 'newState', newState, newState in TYPES, 'final' in TYPES[newState]
                if newState in TYPES and 'final' in TYPES[newState]:
                    return True
        if sState in TYPES and 'final' in TYPES[sState]:
            return True


    # handle the lambdas
    N = len(TRANS2)
    for k in range(N):
        cur_trans = TRANS2[k]
        src, dst = cur_trans[0]
        trans_chars = cur_trans[1]

        if src != sState: continue  # not the right start state

        if 'X' in trans_chars:
            s = stateTrans2(dst,inputstring)
            if s == True: return True

    if len(inputstring) > 0:
        next_char = inputstring[0]
        rest_of_input = inputstring[1:]

        N = len(TRANS2)
        for k in range(N):
            cur_trans = TRANS2[k]
            src, dst = cur_trans[0]
            trans_chars = cur_trans[1]

            if src != sState: continue  # not the right start state

            if next_char in trans_chars:
                s = stateTrans2(dst,rest_of_input)
                if s == True: return True

    return False

def checker(filename):
    global BEENTO, TYPES
    count = 0
    takingInput(filename)
    # find initial state
    initial_state = None
    for k in TYPES.keys():
        if 'initial' in TYPES[k]:
            initial_state = k
    # run all of the inputs
    for i in INPUTS2.iterkeys():
        if initial_state == None:
            print_result_line( i, "No initial state", " " )
        BEENTO = {}
        result = stateTrans2(initial_state,i)
        expected = INPUTS2[i]
        print_result_line( i, result, expected )
        if INPUTS2[i] == result:
            count +=1
    num_inputs = len(INPUTS2)
    return count, num_inputs

def print_result_line( inpt, result, expected ):
    """ print a nice rendition of a result line """
    if len(inpt) <= 7:
        input_w_tabs = inpt + "\t\t"
    else:
        input_w_tabs = inpt + "\t"


    global of
    if of != None:  # if there is an output file
        print >> of, input_w_tabs + str(result) + "\t" + \
                     str(expected) + "\t",
        if expected == result: print >> of, "correct"
        else: print >> of, " *** INCORRECT *** "
    else:
        print input_w_tabs + str(result) + "\t" + \
                     str(expected) + "\t",
        if expected == result: print "correct"
        else: print " *** INCORRECT *** "


def overall(filename1,filename2):
    global INPUTS, TRANS, STATES, TYPES, TRANS2, TRANS3, BEENTO, count, success, \
           current_state_id, current_start_state, current_end_state, seeking_start_state, \
           seeking_end_state, seeking_trans, current_trans
    STATES = []
    TYPES = {}
    TRANS = {}
    TRANS2 = []
    TRANS3 = []
    INPUTS = []
    BEENTO = {}
    count = 0
    current_state_id = None
    current_start_state = None
    current_end_state = None
    seeking_start_state = False
    seeking_end_state = False
    seeking_trans = False
    current_trans = None

    p = xml.parsers.expat.ParserCreate()

    p.StartElementHandler = start_element
    p.EndElementHandler = end_element
    p.CharacterDataHandler = char_data

    f = open(filename1)
    p.ParseFile(f)
    f.close()

    TRANSprocessing()

    num_states = len(STATES)
    #print "STATES are", STATES
    #print "TYPES are", TYPES
    #print "TRANS are", TRANS
    #print "processed TRANS are", TRANS2
    score, num_inputs = checker(filename2)
    return (score,num_inputs,num_states)


#
# this is the test function...
#
def test(student_file, tests_file, f):
    """ reads the jff student_file, e.g., part1.jff
        tests vs. the tests_file, e.g., part1.sols
        f, an open file indicating where
            the output file goes...
    """
    print >> f,  "\n+-+-+-+-+-+-+-+-+\n\n"
    print >> f,  "\n   File to be tested:\n"
    print >> f,  "\n   " + str(student_file) + "\n"
    print >> f,  "Input\t\toutput\texpected ~ result"
    score, num_inputs, num_states = overall(student_file,tests_file)
    print >> f,  "\nHere is the total # correct :", score
    print >> f,  "Here is the total # of tests:", num_inputs
    # Here is the # of states: num_states
    # each is out of 10 points, with -2 for each incorrect answer
    # So, if you miss five, no points remain!
    num_points_missed = min(10, 2*(num_inputs-score))
    print >> f,  "# of pts missed  (out of 10):", num_points_missed
    total_points = 10-num_points_missed
    print >> f,  "\nTotal points for this problem :", total_points
    print >> f,  "\n\n\n"
    return total_points



def tm_test(student_file, tests_file, f):
    """ reads the jff student_file, e.g., part1.jff
        tests vs. the tests_file, e.g., part1.sols
        f, an open file indicating where
            the output file goes...
    """
    print >> f,  "\n+-+-+-+-+-+-+-+-+\n\n"
    print >> f,  "\n   File to be tested:\n"
    print >> f,  "\n   " + str(student_file) + "\n"
    print >> f,  "Input\t\toutput\texpected ~ result"
    score, num_inputs, num_states = tm_overall(student_file,tests_file)
    print >> f,  "\nHere is the total # correct :", score
    print >> f,  "Here is the total # of tests:", num_inputs
    # Here is the # of states: num_states
    # each is out of 10 points, with -2 for each incorrect answer
    # So, if you miss five, no points remain!
    num_points_missed = min(10, 2*(num_inputs-score))
    print >> f,  "# of pts missed  (out of 10):", num_points_missed
    total_points = 10-num_points_missed
    print >> f,  "\nTotal points for this problem :", total_points
    print >> f,  "\n\n\n"
    return total_points


"""
Some directories and names...
"""
import os
import os.path
import sys
import shutil


def testFileParser(filename):
  '''
  Takes a jflap *.soln file and parses the tests in the file
  '''
  global INPUTS, INPUTS2
  INPUTS = []
  INPUTS2 = {}

  takingInput(filename)

  names = []
  for n in INPUTS2.keys():
    if n == '':
      names.append('empty')
    else:
      names.append(n)

  return names

from os.path import splitext

def runTests(cmdPrefix, testFile, timeLimit):
  #The students file is the basename of the test file with the jflap extension
  studentFile = splitext(testFile)[0] + '.jff'
  try:
    #
    # The code below is modified from the overall function (defined above)
    #

    global INPUTS, TRANS, STATES, TYPES, TRANS2, TRANS3, BEENTO, count, success, \
           current_state_id, current_start_state, current_end_state, seeking_start_state, \
           seeking_end_state, seeking_trans, current_trans
    #Resetting a bunch of globals. This is required to allow multiple test files
    #to be run in sequence
    STATES = []
    TYPES = {}
    TRANS = {}
    TRANS2 = []
    TRANS3 = []
    INPUTS = []
    BEENTO = {}
    count = 0
    current_state_id = None
    current_start_state = None
    current_end_state = None
    seeking_start_state = False
    seeking_end_state = False
    seeking_trans = False
    current_trans = None

    p = xml.parsers.expat.ParserCreate()

    p.StartElementHandler = start_element
    p.EndElementHandler = end_element
    p.CharacterDataHandler = char_data

    #Using with syntax to parse the student's file
    with open(studentFile) as f:
      p.ParseFile(f)

    #Don't know what this does the original was not documented
    TRANSprocessing()

    #get the number of states
    num_states = len(STATES)

    #
    # We deviate from overall here so that we can handle the output the way we
    # want to provide data back to the caller. This code is based on checker
    #

    #Load the inputs
    takingInput(testFile)

    #find the initial state
    initial_state = None
    for k in TYPES.keys():
      if 'initial' in TYPES[k]:
        initial_state = k

    if initial_state == None:
      #If we hav eno initial state just die
      summary = {}
      summary['died'] = True
      summary['rawErr'] = "Automaton is missing its initial state"
      summary['timeout'] = False
      return summary, {}

    summary = {}
    summary['rawout'] = ''
    summary['rawErr'] = ''
    summary['failedTests'] = 0
    summary['totalTests'] = 0
    summary['timeout'] = False
    summary['died'] = False
    failedTests = {}

    for i in INPUTS2.iterkeys():
      BEENTO = {}
      result = stateTrans2(initial_state,i)
      summary['totalTests'] += 1
      if INPUTS2[i] != result:
        summary['failedTests'] += 1

        #create a failure report
        report = {}
        report['hint'] = "Expected: " + str(INPUTS2[i]) + " Got: " + str(result)
        if i == '':
          failedTests['empty'] = report
        else:
          failedTests[i]  = report

    return summary, failedTests

  except Exception as e:
    #I don't know what errors the system can throw or how it throws them so I
    #will catch all errors and just report them rather than trying to be smartimport traceback
    import traceback
    tb = traceback.format_exc()
    summary = {}
    summary['died'] = True
    summary['rawErr'] = str(tb)
    summary['timeout'] = False
    return summary, {}

#
# Below is the remains of the old script. It is left here for completeness if
# this script ever needs to be modified it can be tested as it was originally
# designed.
#

# DIR_OF_STUDENTS = "./cs5black_wk12_files"
# DIR_OF_STUDENTS = "./ist380"
# DIR_OF_STUDENTS = "./cs5gold_wk12_files"
#
# # get all subdirs in DIR_OF_STUDENTS
#
# student_dir_names = os.listdir( DIR_OF_STUDENTS )
# student_dir_names.sort()
# total_points = 0
# of = None # output file
# BREAK = True
# # NEXT_TO_GO = "cs5zx"
#
# for student_dir in student_dir_names:
#     #if student_dir < NEXT_TO_GO: continue
#     #student_dir = "cs5sr"
#     print "Student dir: ", student_dir
#     full_pathname_to_student_dir = DIR_OF_STUDENTS + "/" + student_dir
#     # unzip code -- only need to run once
#     """
#     zip_name = "hw12jflap.zip"
#     files_in_dir = os.listdir( full_pathname_to_student_dir )
#     file_name = full_pathname_to_student_dir + "/" + zip_name
#     if zip_name in files_in_dir:
#         print "it's there!"
#         # -o is to force the extraction and not ask for confirmation
#         os.system( ".\unzip.exe -o " + file_name + \
#                    " -d " + full_pathname_to_student_dir )
#     # C:\Users\Owner\Desktop\cs5black_wk12_files>.\unzip.exe
#     # -o cs5black_wk12_files\klund\hw12jflap.zip -d .\cs5black_wk12_files\klund
#     """
#     # add the name "hw12jflap" to the path
#     jflap_dir = full_pathname_to_student_dir + "/hw12jflap"
#     if not os.path.isdir( jflap_dir ):
#         print "No hw12jflap dir present!"
#         os.mkdir( jflap_dir )
#         command = "copy " + full_pathname_to_student_dir + "/*.jff " + \
#                    jflap_dir
#         command = command.replace("/", "\\")
#         print "command is", command
#         os.system( command )
#         print
#     files_in_dir = os.listdir( jflap_dir )
#     #print "  files:", files_in_dir
#     test_file_d = {}
#     test_file_d["part0.jff"] = "part0.sols"
#     test_file_d["part1.jff"] = "part1.sols"
#     test_file_d["part2.jff"] = "part2.sols"
#     test_file_d["part3.jff"] = "part3.sols"
#     test_file_d["part4.jff"] = "part4.sols"
#     test_file_d["extra1.jff"] = "extra1.sols"
#     test_file_d["extra2.jff"] = "extra2.sols"
#     test_file_d["extra3.jff"] = "extra3.sols"
#     print "Opening file of..."
#     output_dir = full_pathname_to_student_dir + "/output.txt"
#     output_dir = "./" + student_dir + ".txt"
#     of = open( output_dir, "w" )
#     print "of is", of
#     f = of
#     print >> f, "\n\nHere are the JFLAP test results."
#     print >> f, "\n\nSee the very bottom for the point total."
#     print >> f, "\n\n"
#     fsms_to_check = [ "part0.jff", "part1.jff", "part2.jff",
#                        "part3.jff", "part4.jff", "extra1.jff"]
#     tms_to_check = [ "extra2.jff", "extra3.jff" ]
#     all_to_check = fsms_to_check + tms_to_check
#     total_points = 0
#     for filename in all_to_check:
#         print "Testing ", student_dir, " file:", filename,
#         print >> f, "\nTesting ", filename, "\n"
#         if filename not in files_in_dir:
#             print " **Not submitted!**"
#             continue
#         student_file = jflap_dir + "/" + filename
#         tests_file = "./sols/" + test_file_d[filename]
#         if filename in fsms_to_check:
#             new_points = test(student_file, tests_file, f)
#         else:
#             new_points = tm_test(student_file, tests_file, f)
#         print "  Score:", new_points
#         total_points += new_points
#     print >> f, "\n\nTOTAL POINTS: ", total_points, "\n\n"
#     print "TOTAL:", total_points
#
#     f.close()
#     # for testing only once...
#     if BREAK == True:
#         print "breaking..."
#         break
#     """
#     # done!
#     """

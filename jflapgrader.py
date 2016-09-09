import argparse
import os
import os.path
import shutil
import sys
import traceback
import xml.parsers.expat

from os.path import splitext

of = None  # global output file name


def tm_start_element(name, attrs):
    global STATES, TYPES, current_state_id, seeking_start_state, \
        seeking_end_state, seeking_trans, seeking_read, seeking_write, \
        seeking_move
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
        TYPES[current_state_id] = ["initial"]
    if name == "final":
        if current_state_id in TYPES:
            TYPES[current_state_id] += ["final"]
        else:
            TYPES[current_state_id] = ["final"]


def tm_end_element(name):
    pass


def tm_char_data(data):
    global TRANS, current_state_id, \
        current_start_state, current_end_state, \
        seeking_start_state, current_trans, seeking_trans, \
        seeking_end_state, current_read, seeking_read, \
        current_write, seeking_write, current_move, seeking_move
    data_without_space = data.strip()
    if len(data_without_space) > 0:
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
        if len(state_placeholder) < 1:
            state_placeholder = ['']
        current_read = state_placeholder[0]
        seeking_read = False
    if seeking_write:
        string = data_without_space
        state_placeholder = [s for s in string.split()]
        if len(state_placeholder) < 1:
            state_placeholder = ['']
        current_write = state_placeholder[0]
        seeking_write = False
    if seeking_move:
        string = data_without_space
        state_placeholder = [s for s in string.split() if s.isalpha()]
        current_move = state_placeholder[0]
        if (current_start_state, current_end_state) in TRANS:
            TRANS[current_start_state, current_end_state] += [[current_read, current_write, current_move]]
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
        for j in range(len(trans_list)):
            if trans_list[j][0] == '':
                trans_list[j][0] = '*'
            if trans_list[j][1] == '':
                trans_list[j][1] = '*'


def tm_takingInput(filename):
    global INPUTS, INPUTS2
    INPUTS2 = {}
    with open(filename) as f:
        L = f.readlines()
        for line in L:
            line = line.strip()
            pieces = line.split()
            if len(pieces) == 2:
                if not pieces[0].isdigit():
                    pieces = ['', pieces[1]]
            if len(pieces) == 3:
                pieces = [pieces[0], pieces[2]]
            INPUTS.append(pieces)
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
            elif INPUTS[i][1] == 'reject':
                INPUTS2[INPUTS[i][0]] = False
            else:
                print "ERROR", INPUTS[i]
                INPUTS2[INPUTS[i][0]] = 'UNDEFINED. ERROR'


def tm_stateTrans2(sState, left, right):
    global BEENTO
    global steps
    THRESHOLD = 25000  # max number of steps...
    TOO_MANY = "Too many steps!"
    possibleTrans = []

    if (sState, left, right) in BEENTO:
        return "Infinite Loop!"
    BEENTO[(sState, left, right)] = True  # remember this state!

    # extend the right side as far as we need...
    if len(right) < 1:
        right = right + '*'
    if len(left) < 1:
        left = '*' + left

    if sState in TYPES and 'final' in TYPES[sState]:
        return True

    elif steps >= THRESHOLD:
        print "..."
        return TOO_MANY  # a string...

    else:
        N = len(TRANS2)
        num_of_matching_transitions = 0
        for k in range(N):
            cur_trans = TRANS2[k]
            src, dst = cur_trans[0]
            cur_char = right[0]  # current character under the read head
            trans_list = cur_trans[1]

            if src != sState:
                continue  # keep going!

            N2 = len(trans_list)
            for j in range(N2):
                cur_arrow = trans_list[j]
                cur_char_to_read = cur_arrow[0]
                cur_char_to_write = cur_arrow[1]
                cur_dir_to_move = cur_arrow[2]
                if cur_char == cur_char_to_read:
                    # Are there any matching transitions?
                    num_of_matching_transitions += 1
                    steps += 1  # global for counting maximum number of steps
                    rest_of_right = right[1:]

                    if cur_dir_to_move == 'R':
                        s = tm_stateTrans2(dst, left + cur_char_to_write, rest_of_right)
                        if s in [True, TOO_MANY]:
                            return s
                    elif cur_dir_to_move == 'L':
                        s = tm_stateTrans2(dst, left[:-1], left[-1] + cur_char_to_write + rest_of_right)
                        if s in [True, TOO_MANY]:
                            return s
                    else:  # it's 'S' for "Stay put"
                        s = tm_stateTrans2(dst, left, cur_char_to_write + rest_of_right)
                        if s in [True, TOO_MANY]:
                            return s

        if num_of_matching_transitions == 0:
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
        if 'initial' in value:
            start_state = key

    for i in INPUTS2.iterkeys():
        BEENTO = {}
        steps = 0
        result = tm_stateTrans2(start_state, '', i)
        expected = INPUTS2[i]
        tm_print_result_line(i, result, expected)
        if INPUTS2[i] == result:
            count += 1
    return count, num_inputs


def tm_print_result_line(inpt, result, expected):
    """Print a nice rendition of a result line"""
    if 8 <= len(inpt) <= 15:
        input_w_tabs = inpt + "\t\t"
    elif len(inpt) <= 7:
        input_w_tabs = inpt + "\t\t\t"
    else:
        input_w_tabs = inpt + "\t"

    global of
    if of is not None:  # if there is an output file
        print >> of, input_w_tabs + str(result) + "\t" + \
            str(expected) + "\t"
        if expected == result:
            print >> of, "correct"
        else:
            print >> of, " *** INCORRECT *** "
    else:
        print input_w_tabs + str(result) + "\t" + \
            str(expected) + "\t"
        if expected == result:
            print "correct"
        else:
            print " *** INCORRECT *** "


def tm_overall(filename1, filename2):
    global INPUTS, TRANS, STATES, TYPES, TRANS2, count, success, BEENTO, \
        current_state_id, current_start_state, current_end_state, \
        seeking_start_state, seeking_end_state, seeking_trans, \
        current_trans, seeking_read, seeking_write, current_read, \
        current_write, seeking_move, current_move
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

    with open(filename1) as f:
        p.ParseFile(f)

    tm_TRANSprocessing()

    num_states = len(STATES)
    score, out_of = tm_checker(filename2)
    return score, out_of, num_states


def start_element(name, attrs):
    global STATES, TYPES, current_state_id, seeking_start_state, \
        seeking_end_state, seeking_trans
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
        TYPES[current_state_id] = ["initial"]
    if name == "final":
        if current_state_id in TYPES:
            TYPES[current_state_id] += ["final"]
        else:
            TYPES[current_state_id] = ["final"]


def end_element(name):
    pass


def char_data(data):
    global TRANS, current_state_id, \
        current_start_state, current_end_state, \
        seeking_start_state, current_trans, seeking_trans, \
        seeking_end_state

    data_without_space = data.strip()
    if len(data_without_space) > 0:
        state_desc = "seeking_start_state"
        if seeking_end_state:
            state_desc = "seeking_end_state"
        elif seeking_trans:
            state_desc = "seeking_trans"

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

        if (current_start_state, current_end_state) not in TRANS:
            TRANS[current_start_state, current_end_state] = [this_trans]
        else:
            TRANS[current_start_state, current_end_state] += [this_trans]
        seeking_trans = False


def TRANSprocessing():
    global TRANS, TRANS2
    TRANS2 = []
    for k in TRANS.iteritems():
        TRANS2.extend([k])


def takingInput(filename):
    global INPUTS, INPUTS2
    INPUTS2 = {}
    with open(filename) as f:
        L = f.readlines()
        for line in L:
            line = line.strip()
            pieces = line.split()
            if len(pieces) == 1:
                if not pieces[0].isdigit():
                    pieces = ['', 'reject']
            if len(pieces) == 0:
                pieces = ['']
            INPUTS.extend([pieces])
        for i in range(len(INPUTS)):
            if len(INPUTS[i]) < 2:
                INPUTS2[INPUTS[i][0]] = True
            else:
                INPUTS2[INPUTS[i][0]] = False


def stateTrans2(sState, inputstring):
    # BEENTO should store both the current state AND the inputstring.
    # so when it returns again, it'll def. be a loop.
    global BEENTO

    if (inputstring, sState) in BEENTO:
        return False  # already been here!

    BEENTO[inputstring, sState] = True  # now we've been here!

    if len(inputstring) == 0:  # done!
        for k in range(len(TRANS2)):
            if TRANS2[k][0][0] == sState and TRANS2[k][1] == 'X':
                newState = TRANS2[k][0][1]
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

        if src != sState:  # wrong start state
            continue

        if 'X' in trans_chars:
            s = stateTrans2(dst, inputstring)
            if s is True:
                return True

    if len(inputstring) > 0:
        next_char = inputstring[0]
        rest_of_input = inputstring[1:]

        N = len(TRANS2)
        for k in range(N):
            cur_trans = TRANS2[k]
            src, dst = cur_trans[0]
            trans_chars = cur_trans[1]

            if src != sState:
                continue  # wrong start state

            if next_char in trans_chars:
                s = stateTrans2(dst, rest_of_input)
                if s is True:
                    return True

    return False


def checker(filename):
    global BEENTO, TYPES
    count = 0
    takingInput(filename)
    # Find initial state
    initial_state = None
    for k in TYPES.keys():
        if 'initial' in TYPES[k]:
            initial_state = k
    # Run all of the inputs
    for i in INPUTS2.iterkeys():
        if initial_state is None:
            print_result_line(i, "No initial state", " ")
        BEENTO = {}
        result = stateTrans2(initial_state, i)
        expected = INPUTS2[i]
        print_result_line(i, result, expected)
        if INPUTS2[i] == result:
            count += 1
    num_inputs = len(INPUTS2)
    return count, num_inputs


def print_result_line(inpt, result, expected):
    """ print a nice rendition of a result line """
    if len(inpt) <= 7:
        input_w_tabs = inpt + "\t\t"
    else:
        input_w_tabs = inpt + "\t"

    global of
    if of is not None:  # if there is an output file
        print >> of, input_w_tabs + str(result) + "\t" + \
            str(expected) + "\t"
        if expected == result:
            print >> of, "correct"
        else:
            print >> of, " *** INCORRECT *** "
    else:
        print input_w_tabs + str(result) + "\t" + \
            str(expected) + "\t"
        if expected == result:
            print "correct"
        else:
            print " *** INCORRECT *** "


def overall(filename1, filename2):
    global INPUTS, TRANS, STATES, TYPES, TRANS2, TRANS3, BEENTO, count, \
        success, current_state_id, current_start_state, current_end_state, \
        seeking_start_state, seeking_end_state, seeking_trans, current_trans
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
    score, num_inputs = checker(filename2)
    return score, num_inputs, num_states


def test(student_file, tests_file, f):
    """
    reads the jff student_file, e.g., part1.jff
    tests vs. the tests_file, e.g., part1.sols

    f, an open file indicating where the output file goes...
    """
    print >> f, "\n+-+-+-+-+-+-+-+-+\n\n"
    print >> f, "\n   File to be tested:\n"
    print >> f, "\n   " + str(student_file) + "\n"
    print >> f, "Input\t\toutput\texpected ~ result"
    score, num_inputs, num_states = overall(student_file, tests_file)
    print >> f, "\nHere is the total # correct :", score
    print >> f, "Here is the total # of tests:", num_inputs
    # Here is the # of states: num_states
    # each is out of 10 points, with -2 for each incorrect answer
    # So, if you miss five, no points remain!
    num_points_missed = min(10, 2 * (num_inputs - score))
    print >> f, "# of pts missed  (out of 10):", num_points_missed
    total_points = 10 - num_points_missed
    print >> f, "\nTotal points for this problem :", total_points
    print >> f, "\n\n\n"
    return total_points


def tm_test(student_file, tests_file, f):
    """
    reads the jff student_file, e.g., part1.jff
    tests vs. the tests_file, e.g., part1.sols

    f, an open file indicating where the output file goes...
    """
    print >> f, "\n+-+-+-+-+-+-+-+-+\n\n"
    print >> f, "\n   File to be tested:\n"
    print >> f, "\n   " + str(student_file) + "\n"
    print >> f, "Input\t\toutput\texpected ~ result"
    score, num_inputs, num_states = tm_overall(student_file, tests_file)
    print >> f, "\nHere is the total # correct :", score
    print >> f, "Here is the total # of tests:", num_inputs
    # Here is the number of states: num_states
    # each is out of 10 points, with -2 for each incorrect answer
    # So, if you miss five, no points remain!
    num_points_missed = min(10, 2 * (num_inputs - score))
    print >> f, "# of pts missed  (out of 10):", num_points_missed
    total_points = 10 - num_points_missed
    print >> f, "\nTotal points for this problem :", total_points
    print >> f, "\n\n\n"
    return total_points


def testFileParser(filename):
    """
    Takes a jflap *.soln file and parses the tests in the file
    """
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


def runTests(cmdPrefix, testFile, timeLimit):
    # The students file is the basename of the test file with the
    # jflap extension
    studentFile = splitext(testFile)[0] + '.jff'
    try:
        # The code below is modified from the overall function
        # (defined above).
        global INPUTS, TRANS, STATES, TYPES, TRANS2, TRANS3, BEENTO, count, \
            success, current_state_id, current_start_state, \
            current_end_state, seeking_start_state, seeking_end_state, \
            seeking_trans, current_trans
        # Resetting a bunch of globals. This is required to allow
        # multiple test files to be run in sequence.
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

        with open(studentFile) as f:
            p.ParseFile(f)

        # Don't know what this does the original was not documented
        TRANSprocessing()

        # get the number of states
        num_states = len(STATES)

        # We deviate from overall here so that we can handle the
        # output the way we want to provide data back to the caller.
        # This code is based on checker

        # Load the inputs
        takingInput(testFile)

        # find the initial state
        initial_state = None
        for k in TYPES.keys():
            if 'initial' in TYPES[k]:
                initial_state = k

        if initial_state is None:
            # If we have no initial state just die.
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
            result = stateTrans2(initial_state, i)
            summary['totalTests'] += 1
            if INPUTS2[i] != result:
                summary['failedTests'] += 1

                # Create a failure report.
                report = {}
                report['hint'] = "Expected: " + str(INPUTS2[i]) + " Got: " + str(result)
                if i == '':
                    failedTests['empty'] = report
                else:
                    failedTests[i] = report

        return summary, failedTests

    except Exception as e:
        # I don't know what errors the system can throw or how it throws
        # them so I will catch all errors and just report them rather
        # than trying to be smart
        tb = traceback.format_exc()
        summary = {}
        summary['died'] = True
        summary['rawErr'] = str(tb)
        summary['timeout'] = False
        return summary, {}

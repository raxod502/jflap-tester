#!/usr/bin/env python3

import os
import re
import sys
import traceback
import xml.parsers.expat

from os.path import splitext

of = None  # global output file name

def takingInput(filename):
    '''
    Parse the specified test file, assigning the resulting data
    structure to the global INPUTS2 variable. This function is
    used only for NFAs, not Turing machines. After processing,
    INPUTS2 will be a dictionary from bitstrings to boolean
    values. See README.md for documentation on the format of test
    files.
    '''
    # We have to continue using the ugly INPUTS2 global unless we want
    # to restructure the control flow of the whole file.
    #
    # It didn't seem like the value of INPUT was used elsewhere, so I
    # didn't bother assigning it in the new version of takingInputs.
    global INPUTS2
    INPUTS2 = {}
    with open(filename) as f:
        # Possible states are "standard" (reading manual test
        # specifications), "reading_words_definition" (reading the
        # definition of the 'words' function), and
        # "reading_check_definition" (reading the definition of the
        # 'check' function).
        state = "standard"
        # Lists of lines in the definitions of the 'words' and 'check'
        # functions.
        words_code_lines = []
        check_code_lines = []
        # This regex is used in two places: to check ahead of time
        # whether 'check' is declared (for fail-fast behavior), and
        # later to determine when 'check' is actually being declared.
        check_def_regex = r'def check\([a-zA-Z_][a-zA-Z0-9_]*\):'
        declares_check = any(re.fullmatch(check_def_regex, line.rstrip()) for line in f)
        # Computing declares_check iterates through the file's lines.
        # To iterate again, we have to reset the reader's position to
        # the beginning.
        f.seek(0)
        # Start line numbering from 1.
        for linum, line in enumerate(f, 1):
            # Trim the trailing newline (and any other trailing
            # whitespace). Note that we can't trim leading whitespace,
            # because this would break any embedded Python function
            # definitions.
            line = line[:-1]
            # Skip empty lines.
            if not line:
                continue
            if state == "reading_words_definition":
                # We assume that function declarations have ended when
                # we find a line that isn't indented by 4 spaces.
                # Since we skip empty lines previously, this means we
                # can have them inside function definitions.
                if line.startswith(" " * 4):
                    words_code_lines.append(line)
                else:
                    state = "standard"
            elif state == "reading_check_definition":
                if line.startswith(" " * 4):
                    check_code_lines.append(line)
                else:
                    state = "standard"
            # If a function declaration has just ended, we want to
            # allow the immediate next line to be a test
            # specification, hence the 'if' instead of an 'elif'.
            if state == "standard":
                # The regex for test specifications is extremely
                # permissive.
                match = re.fullmatch(r'(empty|[0-1]*) ?((-> ?)?([a-z]+))?', line)
                if match:
                    # In the following code, word is the bitstring
                    # input; result is a boolean indicating whether
                    # the input should be accepted; result_word is a
                    # key in result_words that identifies a result
                    # boolean; and result_kword is what is actually in
                    # the test file -- it should be a prefix of
                    # exactly one of the result_kwords.
                    word, result_kword = match.group(1, 4)
                    # Account for the 'empty' special case, so that
                    # word is guaranteed to be a bitstring (assuming
                    # well-formed input).
                    if word == 'empty':
                        word = ''
                    # If the desired result is specified manually:
                    if result_kword:
                        matches = []
                        for result_word, result in result_words.items():
                            if result_word.startswith(result_kword):
                                matches.append(result_word)
                        if not matches:
                            print("Error on line {}: invalid result specifier.".format(linum))
                            print("You provided '{}', but this does not match any of the valid result specifiers, which are: {}"
                                  .format(result_kword, result_words.keys()))
                            exit(1)
                        elif len(matches) > 1:
                            print("Error on line {}: ambiguous result specifier.".format(linum))
                            print("You provided '{}', but this could match any of: {}"
                                  .format(result_kword, matches))
                            exit(1)
                        else:
                            INPUTS2[word] = result_words[matches[0]]
                    # If the desired result is not specified manually,
                    # then the test file *must* declare 'check':
                    # Otherwise, we will have no way of determining
                    # what the desired result should be.
                    elif not declares_check:
                        print("Error on line {}: result specifier not given."
                              .format(linum))
                        print("If you don't provide a result specifier, then you must define 'check'.")
                        exit(1)
                    else:
                        # Leave the desired result for later computation.
                        INPUTS2[word] = None
                elif re.fullmatch(r'def words\(\):', line):
                    # Only allow one definition of each function.
                    if words_code_lines:
                        print("Error on line {}: duplicate definition of 'words'."
                              .format(linum))
                        exit(1)
                    else:
                        words_code_lines.append(line)
                        state = "reading_words_definition"
                elif re.fullmatch(check_def_regex, line):
                    if check_code_lines:
                        print("Error on line {}: duplicate definition of 'check'."
                              .format(linum))
                        exit(1)
                    else:
                        check_code_lines.append(line)
                        state = "reading_check_definition"
                    continue
                else:
                    print("Error on line {}: malformed line.".format(linum))
                    print("You provided: '{}'.".format(line))
                    print("This is not a valid test case or definition start.")
                    exit(1)
        # Using a custom namespace is the preferred way to extract a
        # declared variable from an 'exec' call. Note that this is
        # usually done in a different way in Python 2, but as of
        # Python 3 'exec' cannot modify local variables.
        #
        # Note that this also has the effect of preventing the code in
        # the test file from reading from or writing to the actual
        # global or local namespaces of this script, which is good.
        #
        # We do, however, want to make 'all_bitstrings' available to
        # the test file's inline functions (in particular, to
        # 'words'), hence the initial value of 'namespace'.
        namespace = {'all_bitstrings': all_bitstrings}
        # If one of the lists is empty, then the corresponding call is
        # a no-op. There's no need to check first.
        exec('\n'.join(words_code_lines), namespace)
        exec('\n'.join(check_code_lines), namespace)
        if words_code_lines:
            # If 'words' is declared, then it will produce inputs with
            # potentially unspecified desired results. So 'check' must
            # also be declared in order for the desired results to be
            # determined for these inputs. There are a few edge cases
            # in which you could declare 'words' and not need to
            # declare 'check' (like if 'words' returns an empty list,
            # or all the inputs returned by 'words' also have their
            # desired results manually specified), but these are silly
            # and there's no real reason to special-case them.
            if not check_code_lines:
                print("Error: you defined 'words', but not 'check'.")
                exit(1)
            for word in namespace['words']():
                # Allow overriding 'check' with manually specified
                # test cases.
                if word not in INPUTS2:
                    INPUTS2[word] = None
        if check_code_lines:
            for word, result in INPUTS2.items():
                # Only call 'check' if the desired result has not been
                # manually specified.
                if result is None:
                    INPUTS2[word] = namespace['check'](word)


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
    for k in TRANS.items():
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
                    print("ERROR", INPUTS[i])
            elif INPUTS[i][1] == 'reject':
                INPUTS2[INPUTS[i][0]] = False
            else:
                print("ERROR", INPUTS[i])
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
        print("...")
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

    for i in INPUTS2.keys():
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
        print(input_w_tabs + str(result) + "\t" + \
            str(expected) + "\t", file=of)
        if expected == result:
            print("correct", file=of)
        else:
            print(" *** INCORRECT *** ", file=of)
    else:
        print(input_w_tabs + str(result) + "\t" + \
            str(expected) + "\t")
        if expected == result:
            print("correct")
        else:
            print(" *** INCORRECT *** ")


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
    for k in TRANS.items():
        TRANS2.extend([k])


def all_bitstrings(length):
    if length >= 0:
        yield ''
    current = '0'
    while len(current) <= length:
        yield current
        for j in range(len(current)):
            i = len(current) - 1 - j
            if current[i] == '0':
                current = current[:i] + '1' + '0' * j
                break
            elif i == 0:
                current = '1' + '0' * len(current)

result_words = {'accepted': True,
                'rejected': False,
                'yes': True,
                'no': False}

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
    for k in list(TYPES.keys()):
        if 'initial' in TYPES[k]:
            initial_state = k
    # Run all of the inputs
    for i in INPUTS2.keys():
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
        print(input_w_tabs + str(result) + "\t" + \
            str(expected) + "\t", file=of)
        if expected == result:
            print("correct", file=of)
        else:
            print(" *** INCORRECT *** ", file=of)
    else:
        print(input_w_tabs + str(result) + "\t" + \
            str(expected) + "\t")
        if expected == result:
            print("correct")
        else:
            print(" *** INCORRECT *** ")


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
    print("\n+-+-+-+-+-+-+-+-+\n\n", file=f)
    print("\n   File to be tested:\n", file=f)
    print("\n   " + str(student_file) + "\n", file=f)
    print("Input\t\toutput\texpected ~ result", file=f)
    score, num_inputs, num_states = overall(student_file, tests_file)
    print("\nHere is the total # correct :", score, file=f)
    print("Here is the total # of tests:", num_inputs, file=f)
    # Here is the # of states: num_states
    # each is out of 10 points, with -2 for each incorrect answer
    # So, if you miss five, no points remain!
    num_points_missed = min(10, 2 * (num_inputs - score))
    print("# of pts missed  (out of 10):", num_points_missed, file=f)
    total_points = 10 - num_points_missed
    print("\nTotal points for this problem :", total_points, file=f)
    print("\n\n\n", file=f)
    return total_points


def tm_test(student_file, tests_file, f):
    """
    reads the jff student_file, e.g., part1.jff
    tests vs. the tests_file, e.g., part1.sols

    f, an open file indicating where the output file goes...
    """
    print("\n+-+-+-+-+-+-+-+-+\n\n", file=f)
    print("\n   File to be tested:\n", file=f)
    print("\n   " + str(student_file) + "\n", file=f)
    print("Input\t\toutput\texpected ~ result", file=f)
    score, num_inputs, num_states = tm_overall(student_file, tests_file)
    print("\nHere is the total # correct :", score, file=f)
    print("Here is the total # of tests:", num_inputs, file=f)
    # Here is the number of states: num_states
    # each is out of 10 points, with -2 for each incorrect answer
    # So, if you miss five, no points remain!
    num_points_missed = min(10, 2 * (num_inputs - score))
    print("# of pts missed  (out of 10):", num_points_missed, file=f)
    total_points = 10 - num_points_missed
    print("\nTotal points for this problem :", total_points, file=f)
    print("\n\n\n", file=f)
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
    for n in list(INPUTS2.keys()):
        if n == '':
            names.append('empty')
        else:
            names.append(n)

    return names


def runTests(jffFile, testFile):
    '''
    Runs the tests defined in testFile on the NFA defined in jffFile.
    If a test fails, prints an explanatory error message and exits
    immediately.
    '''
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

    with open(jffFile, 'rb') as f:
        p.ParseFile(f)

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
    for k in list(TYPES.keys()):
        if 'initial' in TYPES[k]:
            initial_state = k

    if initial_state is None:
        print('Error: NFA has no initial state.')
        exit(1)

    for word, expected_result in INPUTS2.items():
        BEENTO = {}
        result = stateTrans2(initial_state, word)
        if result != expected_result:
            print('Error: failed test.')
            print("The input string '{}' should have been {}, but it was {}."
                  .format(word,
                          'accepted' if expected_result else 'rejected',
                          'accepted' if result else 'rejected'))
            exit(1)

    if INPUTS2:
        print('{} tests passed. Congratulations!'.format(len(INPUTS2)))
    else:
        print('No tests specified.')

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('usage: jflapgrader.py <jff-filename>')
        exit(1)
    jffFile = sys.argv[1]
    if not jffFile.endswith('.jff'):
        print('Error: filename must end in .jff.')
        exit(1)
    # It would be preferable to just catch an exception instead of
    # checking at the beginning, but the control flow in this codebase
    # makes it really hard to tell what files may or may not be
    # opened, and where. This way, I'm sure to only catch the error
    # conditions I anticipate.
    if not os.path.isfile(jffFile):
        print('Error: ' + jffFile + ' does not exist.')
        exit(1)
    testFile = splitext(jffFile)[0] + '.test'
    if not os.path.isfile(testFile):
        print('Error: ' + testFile + ' does not exist.')
        exit(1)
    runTests(jffFile, testFile)

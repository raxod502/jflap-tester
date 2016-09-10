# JFLAP Tester

This is a command-line script designed for testing [NFAs][nfa] and [Turing machines][turing] created in [JFLAP]. The code for parsing and running JFLAP files is based on the [autograder] created by [Harvey Mudd College][hmc]'s Computer Science department. You can find the repository containing the original version of the autograder [here][hmc-grader].

## Dependencies

You will need to have Python 3 installed and available on your `$PATH` as `python3`.

## Usage

> ```
> $ python3 test.py [--tm] <jff-filename>
> ```
> 
> You can also run `test.py` as an executable.

The test file must be in the same directory as the `.jff` file. It must also have the same filename as the `.jff` file, but with the `.test` extension. For instance, the test file for `hw1/nfa1.jff` should be named at `hw1/nfa1.test`.

Provide the `--tm` flag if your `.jff` file contains a Turing machine; otherwise, it is assumed to contain an NFA.

For convenience, you may want to add the following aliases to your `.bashrc` or `.zshrc`:

```
alias jtest='python3 "/path/to/test.py"'
alias tmtest='python3 "/path/to/test.py" --tm'
```

You may then test NFAs and Turing machines, respectively, with the following commands:

```
$ jtest my-nfa.jff
$ tmtest my-tm.jff
```

## Test file format

The test file specifies a list of test cases. Each one should consist of a bitstring (the input word) as well as the expected output (accept or reject). Any of the following formats are fine (and they are all equivalent):

```
0110 -> accept
0110 ->accept
0110-> accept
0110 accept
0110accept
```

Of course, you may also replace `accept` with `reject`. The words `yes` and `no` are equivalent to `accept` and `reject` (or `accepted` and `rejected`), so you can use these as well. Furthermore, you can specify an expected result using a prefix of any length, so `accepted`, `accept`, `acc`, and `a` are all acceptable. You can also leave off the bitstring in order to signify the empty string, or you can write `empty`. Any of the following will work (and they are all equivalent):

```
empty -> reject
-> reject
reject
```

Empty lines are ignored. Comments are not allowed currently.

In addition to explicit test cases, you can embed some Python code. In particular, you can define two functions, `check` and `words`. There is no need to identify the beginning or end of the function definitions: this is determined automatically. A function definition begins with the appropriate `def` statement, and ends at the first line that either has only whitespace or is not indented by four spaces. (Note that this means you cannot use two-space indentation or blank lines inside a function definition.) As long as you keep this in mind, you can put test cases directly before and after a function definition, and otherwise interperse definitions any test cases in any order.

The `check` function should take one argument (of any name), which is a bitstring (possibly empty), and return either `False` (for `reject`) or `True` (for `accept`). (Note: only these values are permissible; the return value is *not* currently cast to a boolean.) If you define `check`, you may leave the expected results off of some of your test cases, and they will be determined automatically by calling `check`. Thus the following formats for test cases will be allowed:

```
0110
empty
```

Note that in the corner case of defining a test case for the empty string but having the expected result be determined automatically by `check`, you *must* write the bitstring as `empty` instead of leaving it blank (otherwise there is no way to distinguish between this and a blank line that should be ignored).

If you provide explicit expected results for some of your test cases, though, these will override `check`.

The `words` function should take no arguments and return an iterable of bitstrings. (The generator pattern is quite useful for this function.) For convenience, it has access to the `all_bitstrings` function, which takes an integer and returns an iterable of all bitstrings of length not more than the provided argument (in lexicographic order). The bitstrings returned by `words` are used as additional test cases, and the expected results for these test cases are determined using `check` (so you must also define `check` if you define `words`), unless you override the expected results with explicit test cases.

Here is an example test file. It tests whether an NFA or Turing machine accepts exactly those strings that are composed of only zeros and have a length that is a power of two.

```
def words():
    for word in all_bitstrings(8):
        yield word
    for length in range(75):
        yield '0' * length

def check(word):
    for c in word:
        if c != '0': return False
    n = 1
    while True:
          if n == len(word): return True
          elif n > len(word): return False
          else: n *= 2
```

Notice that `words` is designed to test a number of general bitstrings (to ensure that bitstrings containing ones are rejected), as well as to test longer bitstrings that are composed of only zeros (up to lengths for which it would be impractical to test *every* bitstring).

On the other hand, you could test only a small selection of bitstrings that are interesting to you:

```
def check(word):
    for c in word:
        if c != '0': return False
    n = 1
    while True:
          if n == len(word): return True
          elif n > len(word): return False
          else: n *= 2

empty
0
00
000
0000
00001
```

Or you could specify the desired results manually:

```
empty rejected
0 accepted
00 accepted
000 rejected
0000 accepted
00001 rejected
```

## Output

If a test fails, `test.py` will halt immediately, print the result of the failing test, and exit with a non-zero return code. If another error occurs (such as an improperly formatted or missing test file), an error message will be printed and `test.py` will exit with a non-zero return code. Otherwise, if all tests pass and there are no errors, the total number of tests will be printed and `test.py` will exit with a zero return code.

## Contributing

Please feel free to create an issue or pull request if you find a problem.

[nfa]: https://en.wikipedia.org/wiki/Nondeterministic_finite_automaton
[turing]: https://en.wikipedia.org/wiki/Turing_machine
[jflap]: http://www.jflap.org/
[autograder]: https://github.com/CSGreater-Developers/HMC-Grader/blob/f7ce1fe866fcde521c0a2dcb5102a75fae223142/app/plugins/autograder/jflapgrader.py
[hmc]: https://www.hmc.edu/
[hmc-grader]: https://github.com/CSGreater-Developers/HMC-Grader

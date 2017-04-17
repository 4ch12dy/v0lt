import itertools
import os
from v0ltlib.utils.v0lt_utils import *
from v0ltlib.tools.bruteforce import Bruteforce

class InputForm:
    """
    Enumeration regarding the password input
    STDIN means the password is given to the program with a scanf/fgets function
    ARGV  means it is given as parameter
    """

    STDIN = 1
    ARGV = 2

class StopAt:
    """
    HIGHEST_COUNT will test all possible values before selecting the one that
    matches best.
    FIRST_CHANGE means the counter with stop directly when the instruction count
    differ.
    """
    HIGHEST_COUNT = 1
    FIRST_CHANGE = 2

class InstructionCounter:
    """
    Password cracker using instruction counting tool based on Intel Pin

    :param pin_path:    Absolute path of the pin executable
    :param binary:      Binary to analyze
    :param binary_args: Arguments for binary to analyze
    :param verbose:     If True, prints debug messages
    :param arch:        32 or 64 bits
    :param input_form:  InputForm parameter matching the password input method
    :param stop_at:     StopAt parameter for password length guessing
    :param length:      Predefined password length with the \0 or \n
    :param charset:     Charset to use for bruteforcing
    """

    PIN64_COMMAND = '{0}pin -t {0}source/tools/ManualExamples/obj-intel64/inscount0.so -- '
    PIN32_COMMAND = '{0}pin -t {0}source/tools/ManualExamples/obj-ia32/inscount0.so -- '
    OUTPUT_FILE = 'inscount.out'
    TMP_BRUTE = 'tmp_bruteforce'
    PIN_STRING_BEGIN = 'Count '
    USUAL_CHARSET = "._abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789{}[]-=+*^%$@!."

    def __init__(self,
                 pin_path,
                 binary,
                 binary_args="",
                 verbose=False,
                 arch=64,
                 input_form=InputForm.ARGV,
                 stop_at=StopAt.HIGHEST_COUNT,
                 length=-1,
                 charset=USUAL_CHARSET):

        self.binary = binary
        self.binary_args = binary_args
        self.arch = arch
        self.input_form = input_form
        self.stop_at = stop_at
        self.length = length
        self.charset = charset

        pin_executable = pin_path + "pin"
        assert(os.path.isfile(pin_executable) and os.access(pin_executable, os.X_OK))
        assert(os.path.isfile(binary) and os.access(binary, os.X_OK))

        config['is_debug'] = verbose

        if arch == 32:
            self.cmd = self.PIN32_COMMAND.format(pin_path)
        else:
            self.cmd = self.PIN64_COMMAND.format(pin_path)

    def clean_temp(self):
        """
        Clean temporary files
        """
        tmp = [self.TMP_BRUTE, self.OUTPUT_FILE, 'pin.log']
        [ os.remove(f) for f in tmp if os.path.isfile(f) ]

    def run_pin(self, string):
        """
        Run pin with the specified command
        """

        if self.input_form == InputForm.ARGV:
            cmd = '{0} {1} {2} {3}'.format(self.cmd, self.binary, self.binary_args, string)
            os.system(cmd)
        else:
            cmd = '/bin/bash -c "{0} {1} {2} <<< {3}"'.format(self.cmd, self.binary, self.binary_args, string)
            os.system(cmd)

    def get_pass_length(self):
        """
        Determine the password's length

        :returns: The guessed length
        """

        last = -1
        diff = 0
        max_i = -1

        for i in range(2, 100):

            string = 'A' * i
            self.run_pin(string)

            try:
                with open(self.OUTPUT_FILE, 'r') as f:
                    count = f.read()[len(self.PIN_STRING_BEGIN):]
                    count = int(count)
                    if last < 0:
                        last = count
                        diff = 0
                    else:
                        if count - last > diff:
                            if self.stop_at == StopAt.FIRST_CHANGE:
                                success('Pass length guessed: {0}'.format(i))
                                return i
                            diff = count - last
                            max_i = i
                            debug("! New max")
                        last = count
                    debug("Length {0}: {1} (max diff: {2})".format(i, count, diff))
            except Exception as e:
                smth_went_wrong('get_pass_length', e)
                return -1

        success('Pass length guessed: {0}'.format(max_i))
        self.clean_temp()
        return max_i + 1

    def Accurate(self):
        """
        Counter that will try to determine the password accurately by
        bruteforcing every char with the complete charset
        """

        if self.length < 0:
            warning("no length specified - guessing")
            self.length = self.get_pass_length()
            if self.length < 0:
                return None

        begin_with = ''
        for i in range(0, self.length):
            bf = Bruteforce(self.charset,
                            final_length=self.length,
                            begin_with=begin_with,
                            max_iterations=len(self.charset))

            last = -1
            diff = 0
            max_c = -1
            for bruted in bf.generate():
                self.clean_temp()
                self.run_pin(bruted)

                with open(self.OUTPUT_FILE, "r") as f:
                    count = f.read()
                    count = count[len(self.PIN_STRING_BEGIN):]
                    count = int(count)
                    if last < 0:
                        last = count
                    else:
                        if count - last > diff:
                            max_c = bruted[i]
                            diff = count - last
                            debug("! New max")
                    debug('testing {0} ({1} - max diff: {2})'.format(bruted.rstrip(), count, diff))

            success("char guessed: {0}".format(max_c))
            begin_with = begin_with + max_c

        success("pass found: {0}".format(begin_with))
        return begin_with


    def Fast(self):
        """
        Counter that will try to determine the password by checking the first
        count change. Faster, but often mistaking
        """

        if self.length < 0:
            warning("no length specified - guessing")
            self.length = self.get_pass_length()
            if self.length < 0:
                return None

        begin_with = ''
        for i in range(0, self.length):
            found = False
            bf = Bruteforce(self.charset,
                            final_length=self.length,
                            begin_with=begin_with,
                            max_iterations=len(self.charset))

            iterations = -1
            for bruted in bf.generate():
                self.clean_temp()
                debug('testing {0}'.format(bruted.rstrip()))
                self.run_pin(bruted)

                with open(self.OUTPUT_FILE, "r") as f:
                    count = f.read()
                    count = count[len(self.PIN_STRING_BEGIN):]
                    count = int(count)
                    if iterations < 0:
                        iterations = count
                    else:
                        if iterations < count:
                            success("char found: {0}".format(bruted[i]))
                            begin_with = begin_with + bruted[i]
                            found = True
                            break
            if not found:
                fail("char not found")
                return begin_with

        success("pass found: {0}".format(begin_with))
        return begin_with




#!/usr/bin/env python

import sys
assert sys.version_info >= (3,0), 'Script requires Python 3.0 or greater to run'

import argparse
import threading

from lib.utils import globals
from lib.system import environment
from lib.system import calculations


def parse_the_command_line(): 
    parser = argparse.ArgumentParser(description=
                                     'Do WCET calculation using super blocks '
                                     'analysis')
    
    parser.add_argument('program_file',
                        help='a file containing program information'
                        ' (with .txt extension)')

    parser.add_argument('--repeat',
                        type=int,
                        help='repeat the calculation this many times',
                        default=1,
                        metavar='<INT>')
    
    parser.add_argument('--max-loop-bound',
                        type=int,
                        help='set the maximum possible value for automatically '
                        'generated loop bounds',
                        default=10,
                        metavar='<INT>')
    
    parser.add_argument('--folded',
                        action='store_true',
                        help='fold super blocks before constraint solving',
                        default=False)
    
    parser.add_argument('--functions',
                        nargs='*',
                        help='analyse these functions only')
    
    globals.add_common_command_line_arguments(parser)
    globals.args = vars(parser.parse_args())
    globals.set_filename_prefix(globals.args['program_file'])
    

if __name__ == '__main__': 
    threading.stack_size(67108864) # 64MB stack
    sys.setrecursionlimit(2**20)
    
    parse_the_command_line()
    program = environment.create_program_from_input_file() 
    program.delete_unlisted_functions(globals.args['functions'])
    calculations.calculate_wcet_using_integer_linear_programming(program)

            
    
    
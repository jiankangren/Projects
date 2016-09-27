#!/usr/bin/env python3

import sys
assert sys.version_info >= (3,0), 'Script requires Python 3.0 or greater to run'

import argparse

from lib.utils import globals
from lib.utils import dot
from lib.system import environment
from lib.system.directed_graphs import InstrumentationPointGraph
from lib.system.vertices import is_basic_block


def parse_the_command_line(): 
    parser = argparse.ArgumentParser(description=
                                     'Instrument program to collect execution '
                                     'profiles at run time')
    
    parser.add_argument('program_file',
                        help='a file containing program information'
                        ' (with .txt extension)')
    
    parser.add_argument('--instrument',
                        choices=['vertices', 'edges', 'mixed'],
                        required=True,
                        help='instrument vertices, edges, or both')
    
    parser.add_argument('--repeat',
                        type=int,
                        help='repeat the calculation this many times',
                        default=1,
                        metavar='<INT>')
    
    parser.add_argument('--functions',
                        nargs='*',
                        help='analyse these functions only')
    
    globals.add_common_command_line_arguments(parser)
    globals.args = vars(parser.parse_args())
    globals.set_filename_prefix(globals.args['program_file'])


if __name__ == '__main__': 
    parse_the_command_line()
    program = environment.create_program_from_input_file()

    for control_flow_graph in program:
        print('======> function', control_flow_graph.name)
        for repetition in range(1, globals.args['repeat']+1):
            if globals.args['instrument'] == 'vertices':
                control_flow_graph.instrument_all_basic_blocks()
            elif globals.args['instrument'] == 'edges':
                control_flow_graph.instrument_all_control_flow_edges()
            elif globals.args['instrument'] == 'mixed':
                control_flow_graph.instrument_all_basic_blocks()
                control_flow_graph.instrument_all_control_flow_edges()
            else:
                assert False
            
            instrumentation_point_graph = InstrumentationPointGraph.\
                                            instrument_but_maintain_path_reconstructibility\
                                                (control_flow_graph)
            dot.make_file(control_flow_graph)
            print('IPG: {}'.format(', '.join(str(vertex.program_point) 
                                            for vertex in control_flow_graph
                                            if control_flow_graph.program_point_data.get_instrumented(vertex.program_point)
                                            and vertex.program_point)))
            
            for _, abstract_vertices in control_flow_graph.get_loop_nesting_tree().\
                                        level_by_level_iterator\
                                        (abstract_vertices_only=True):
                for abstract_vertex in abstract_vertices:
                    if is_basic_block(abstract_vertex.program_point):
                        subgraph = control_flow_graph.get_super_block_subgraph(abstract_vertex)
                        instrumented_program_points = subgraph.choose_instrumentation_points_for_profiling()
                        print('Super: {}'.format(', '.join(str(program_point) 
                                                           for program_point in instrumented_program_points)))
            
            print()

        
    

import abc
import os
import timeit
import subprocess
import decimal
import re

from lib.utils import globals
from lib.utils import debug
from lib.system.vertices import ProgramPointVertex, RegularExpressionVertex
from lib.system import directed_graphs


def calculate_wcet_using_instrumentation_point_graph(program):
    
    for repetition in range(1, globals.args['repeat']+1):
        debug.verbose_message('Repetition {}'.format(repetition), __name__)
        for control_flow_graph in program:
            loop_nesting_tree = control_flow_graph.get_loop_nesting_tree()
            program_point_data = control_flow_graph.program_point_data
            program_point_data.create_timing_data(True)
            
            ilp_for_control_flow_graph = IntegerLinearProgramForControlFlowGraph\
                                                (control_flow_graph,
                                                 loop_nesting_tree,
                                                 program_point_data)
            ilp_for_control_flow_graph.solve()
            
            instrumentation_point_graph = control_flow_graph.get_instrumentation_point_graph() 
            ilp_for_instrumentation_point_graph = IntegerLinearProgramForInstrumentationPointGraph\
                                                   (instrumentation_point_graph,
                                                    loop_nesting_tree,
                                                    program_point_data)
            ilp_for_instrumentation_point_graph.solve()
            
            assert ilp_for_instrumentation_point_graph.wcet == ilp_for_control_flow_graph.wcet
            
            print('==========> {} <=========='.format(control_flow_graph.name))
            print('Standard calculation:')
            print('WCET              = {}'.format(ilp_for_control_flow_graph.wcet))
            print('#Variables        = {}'.format(len(ilp_for_control_flow_graph.variables)))
            print('#Constraints      = {}'.format(len(ilp_for_control_flow_graph.constraints)))
            print('Construction time = {}'.format(ilp_for_control_flow_graph.construction_time))
            print('Solve time        = {}'.format(ilp_for_control_flow_graph.solve_time))
            print('-' * 25)
            print('Instrumentation point graph calculation:')
            print('WCET              = {}'.format(ilp_for_instrumentation_point_graph.wcet))
            print('#Variables        = {}'.format(len(ilp_for_instrumentation_point_graph.variables)))
            print('#Constraints      = {}'.format(len(ilp_for_instrumentation_point_graph.constraints)))
            print('Construction time = {}'.format(ilp_for_instrumentation_point_graph.construction_time))
            print('Solve time        = {}'.format(ilp_for_instrumentation_point_graph.solve_time))    


def calculate_wcet_using_integer_linear_programming(program):
    
    for repetition in range(1, globals.args['repeat']+1):
        debug.verbose_message('Repetition {}'.format(repetition), __name__)
        for control_flow_graph in program:
            # The reason we grab the loop-nesting tree here and not inside the
            # constraint system is because we time how long it takes to 
            # construct the constraint system.  Since the loop-nesting tree is
            # built on the fly, it may happen that a portion of the time to
            # construct the constraint system is unfairly attributed to that
            # activity.
            loop_nesting_tree = control_flow_graph.get_loop_nesting_tree()
            control_flow_graph.create_timing_data(True)
            ilp_for_control_flow_graph = IntegerLinearProgramForControlFlowGraph\
                                            (control_flow_graph,
                                             loop_nesting_tree)
            ilp_for_control_flow_graph.solve()
              
            ilp_for_super_block_graph = IntegerLinearProgramForSuperBlockGraph\
                                            (control_flow_graph,
                                             loop_nesting_tree)
            ilp_for_super_block_graph.solve()
            
            assert ilp_for_super_block_graph.wcet == ilp_for_control_flow_graph.wcet
           
            print('==========> {} <=========='.format(control_flow_graph.name))
            print('Standard calculation:')
            print('WCET              = {}'.format(ilp_for_control_flow_graph.wcet))
            print('#Variables        = {}'.format(len(ilp_for_control_flow_graph.variables)))
            print('#Constraints      = {}'.format(len(ilp_for_control_flow_graph.constraints)))
            print('Construction time = {}'.format(ilp_for_control_flow_graph.construction_time))
            print('Solve time        = {}'.format(ilp_for_control_flow_graph.solve_time))
            print('-' * 25)
            print('Super block calculation:')
            print('WCET              = {}'.format(ilp_for_super_block_graph.wcet))
            print('#Variables        = {}'.format(len(ilp_for_super_block_graph.variables)))
            print('#Constraints      = {}'.format(len(ilp_for_super_block_graph.constraints)))
            print('Construction time = {}'.format(ilp_for_super_block_graph.construction_time))
            print('Solve time        = {}'.format(ilp_for_super_block_graph.solve_time))
            
            if globals.args['folded']:
                ilp_with_folding = IntegerLinearProgramForSuperBlockGraphWithFolding\
                                    (control_flow_graph,
                                     loop_nesting_tree)
                ilp_with_folding.solve()
                
                assert ilp_with_folding.wcet == ilp_for_control_flow_graph.wcet
                print('-' * 25)
                print('Super block calculation with folding:')
                print('WCET              = {}'.format(ilp_with_folding.wcet))
                print('#Variables        = {}'.format(len(ilp_with_folding.variables)))
                print('#Constraints      = {}'.format(len(ilp_with_folding.constraints)))
                print('Construction time = {}'.format(ilp_with_folding.construction_time))
                print('Solve time        = {}'.format(ilp_with_folding.solve_time))


edge_variable_prefix = 'E_'
vertex_variable_prefix = 'V_'
def get_variable_for_program_point(program_point, variables):
    if ProgramPointVertex.is_basic_block(program_point):
        variable = '{}{}'.format(vertex_variable_prefix,
                                 program_point)
    else:
        variable = '{}{}_{}'.format(edge_variable_prefix, 
                                    program_point[0],
                                    program_point[1])
    variables.add(variable)
    return variable


transition_variable_prefix = 'T_'
def get_variable_for_edge_between_program_points(program_point_one, 
                                                 program_point_two, 
                                                 variables):
    variable = transition_variable_prefix
    if ProgramPointVertex.is_basic_block(program_point_one):
        variable += '{}'.format(program_point_one)
    else:
        variable += '{}_{}'.format(program_point_one[0], program_point_one[1])
    variable += '.'
    if ProgramPointVertex.is_basic_block(program_point_two):
        variable += '{}'.format(program_point_two)
    else:
        variable += '{}_{}'.format(program_point_two[0], program_point_two[1])
    variables.add(variable)
    return variable


wcet_variable_prefix   = 'W_'
def get_vertex_wcet_variable(vertex_id):
    return '{}{}'.format(wcet_variable_prefix, vertex_id)


def get_new_line(num=1):
    return '\n' * num



class ConstraintSystem:
    
    """
    Any constraint system that solves to a WCET estimate must, at the least,
    generate an objective function, structural constraints and execution
    count constraints on program points in loops.
    """
    
    __metaclass__ = abc.ABCMeta
    
    def __init__(self):
        self._filename = None
        self._wcet = None
        self._solve_time = None
        self._construction_time = None
        self._variable_execution_counts = {}
        self._constraints = set()
        self._variables = set()
    
    
    @property
    def wcet(self):
        return self._wcet
    
    
    @property
    def solve_time(self):
        return self._solve_time
    
    
    @property
    def construction_time(self):
        return self._construction_time
    
    
    @property
    def variables(self):
        return self._variables
    
    
    @property
    def constraints(self):
        return self._constraints

   

class SolverError(Exception):
    
    """
    Exception to catch when a call to a solver fails.
    """
    
    def __init__(self, message):
        Exception.__init__(self, message)
         


class IntegerLinearProgram(ConstraintSystem):  
    
    """
    A constraint system that contains linear constraints only.
    """    
          
    def _create_integer_constraint(self):
        self.int_constraint = 'int'
        counter = len(self._variables)
        for variable in self._variables:
            self.int_constraint += ' {}'.format(variable)
            if counter > 1:
                self.int_constraint += ','
            counter -= 1
        self.int_constraint += ';'
        
        
    def _write_to_file(self):
        with open(self._filename, 'w') as the_file:
            the_file.write(self.obj_function)
            the_file.write(get_new_line(2))
            for constraint in self._constraints:
                the_file.write(constraint)
                the_file.write(get_new_line())
            the_file.write(get_new_line())
            the_file.write(self.int_constraint)
            the_file.write(get_new_line())
    
    
    def solve(self):
        self._write_to_file()
        
        # Launch lp_solve with the created file
        command = 'lp_solve {}'.format(self._filename) 
        start = timeit.default_timer()
        process = subprocess.Popen(command,
                                   shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, _  = process.communicate()
        end = timeit.default_timer()
        self._solve_time = end - start
        
        if process.returncode != 0:
            raise SolverError('Running {} failed'.format(command))
        
        # Grab the WCET estimate and the execution counts of program
        # points in the control flow graph
        stdout = stdout.decode()
        for line in stdout.split(os.linesep):
            line = line.strip()
            # Process if the line is not whitespace and has digits in it
            if line and re.search('\d+', line):
                lexemes = re.split('\s+', line)
                if len(lexemes) == 2:
                    self._variable_execution_counts[lexemes[0]] =\
                        int(decimal.Decimal(lexemes[1]))
                else:
                    self._wcet = int(round(float(lexemes[-1])))
    
        # We only need the ILP file for debugging purposes        
        if not globals.args['debug'] and os.path.exists(self._filename):
            os.remove(self._filename)
            
                
    def output(self, function_name):
        print()
        print('wcet({})={}'.format(function_name, self._wcet))
        for variable in sorted(self._variable_execution_counts.keys()):
            if self._variable_execution_counts[variable] > 0:
                print('{} = {}'.format(variable, 
                                       self._variable_execution_counts[variable]))

    
    
class IntegerLinearProgramForControlFlowGraph(IntegerLinearProgram):
    
    """
    The integer linear program derived from a control flow graph, execution 
    times of basic blocks and upper bounds on loop header execution counts.
    """
    
    def __init__(self, 
                 control_flow_graph, 
                 loop_nesting_tree,
                 program_point_data):
        ConstraintSystem.__init__(self)
        self._filename = '{}.{}.cfg.ilp'.format(globals.args['filename_prefix'], 
                                                control_flow_graph.name)
        start = timeit.default_timer()
        self.__create_objective_function(control_flow_graph,
                                         program_point_data)
        self.__create_structural_constraints(control_flow_graph)
        self.__create_loop_bound_constraints(control_flow_graph,
                                             loop_nesting_tree,
                                             program_point_data)
        self._create_integer_constraint()
        end = timeit.default_timer()
        self._construction_time = end - start
        
        
    def __create_objective_function(self, 
                                    control_flow_graph,
                                    program_point_data):
        self.obj_function = 'max: '
        counter = len(control_flow_graph.basic_block_vertices)
        for vertex in control_flow_graph:
            if ProgramPointVertex.is_basic_block(vertex.program_point):
                vertex_variable = get_variable_for_program_point(vertex.program_point,
                                                               self._variables) 
                self.obj_function += '{} {}'.format\
                                        (program_point_data.get_wcet(vertex.program_point), 
                                         vertex_variable)
                if counter > 1:
                    self.obj_function += ' + '
                counter -= 1
        self.obj_function += ';'


    def __create_structural_constraints(self, control_flow_graph):
        for vertex in control_flow_graph:
            if vertex.number_of_predecessors() == 1:
                pred_vertex = control_flow_graph.get_vertex\
                                (vertex.get_ith_predecessor_edge(0).vertex_id)
                if pred_vertex.number_of_successors() == 1:
                    constraint = get_variable_for_program_point\
                                    (vertex.program_point, self._variables)
                    constraint += ' = '
                    constraint += get_variable_for_program_point\
                                    (pred_vertex.program_point, self._variables)
                    constraint += ';'
                    self._constraints.add(constraint)                    
            else:
                vertex_variable = get_variable_for_program_point\
                                        (vertex.program_point,
                                         self._variables)
                constraint = vertex_variable
                constraint += ' = '
                counter = vertex.number_of_predecessors()
                for pred_edge in vertex.predecessor_edge_iterator():
                    pred_vertex = control_flow_graph.\
                                    get_vertex(pred_edge.vertex_id)
                    pred_vertex_variable = get_variable_for_program_point\
                                            (pred_vertex.program_point,
                                             self._variables)
                    constraint += pred_vertex_variable
                    if counter > 1:
                        constraint += ' + '
                    counter -= 1 
                constraint += ';'
                self._constraints.add(constraint)
                
            if vertex.number_of_successors() > 1:
                vertex_variable = get_variable_for_program_point\
                                        (vertex.program_point,
                                         self._variables)
                constraint = vertex_variable
                constraint += ' = '
                counter = vertex.number_of_successors()
                for succ_edge in vertex.successor_edge_iterator():
                    succ_vertex = control_flow_graph.\
                                    get_vertex(succ_edge.vertex_id)
                    succ_vertex_variable = get_variable_for_program_point\
                                            (succ_vertex.program_point,
                                             self._variables)
                    constraint += succ_vertex_variable
                    if counter > 1:
                        constraint += ' + '
                    counter -= 1 
                constraint += ';'
                self._constraints.add(constraint)     
            
            
    def __create_loop_bound_constraints(self, 
                                        control_flow_graph,
                                        loop_nesting_tree,
                                        program_point_data):
        
        def create_local_loop_bound_constraint(abstract_vertex):
            constraint = get_variable_for_program_point(abstract_vertex.program_point,
                                                        self._variables)
            if (abstract_vertex.program_point == 
                loop_nesting_tree.root_vertex.program_point):
                constraint += ' = {};'.format(max
                                              (program_point_data.get_loop_bound
                                               (abstract_vertex.program_point)))
            else:
                loop_body = loop_nesting_tree.\
                                get_loop_body_for_program_point(abstract_vertex.
                                                                program_point)
                header = control_flow_graph.get_vertex_for_program_point\
                                (abstract_vertex.program_point)
                loop_entry_predecessor_vertices = set()
                for pred_edge in header.predecessor_edge_iterator():
                    pred_tree_vertex = loop_nesting_tree.get_vertex(pred_edge.vertex_id)
                    if pred_tree_vertex not in loop_body:
                        loop_entry_predecessor_vertices.add(pred_tree_vertex)
                       
                constraint += ' <= ' 
                counter = len(loop_entry_predecessor_vertices)
                for pred_vertex in loop_entry_predecessor_vertices:
                    constraint += '{} {}'.format(max
                                                 (program_point_data.get_loop_bound
                                                  (abstract_vertex.program_point)),
                                                 get_variable_for_program_point
                                                 (pred_vertex.program_point,
                                                  self._variables))
                    if counter > 1:
                        constraint += ' + '
                    counter -= 1 
                constraint += ';'
            self._constraints.add(constraint)
            
        
        def create_global_loop_bound_constraint(abstract_vertex):
            constraint = get_variable_for_program_point(abstract_vertex.program_point,
                                                        self._variables)
            constraint += ' <= '
            constraint += '{};'.format(sum
                                       (program_point_data.get_loop_bound
                                        (abstract_vertex.program_point)))
            self._constraints.add(constraint)
            
        
        for level, tree_vertices in loop_nesting_tree.\
                                    level_by_level_iterator\
                                        (abstract_vertices_only=True):
            for abstract_vertex in tree_vertices:
                if ProgramPointVertex.is_basic_block(abstract_vertex.program_point):
                    create_local_loop_bound_constraint(abstract_vertex)
                    if level > 1:
                        create_global_loop_bound_constraint(abstract_vertex)                 
            
    

class IntegerLinearProgramForSuperBlockGraph(IntegerLinearProgram):
    
    """
    The integer linear program derived from a super block graph.
    """
    
    def __init__(self, control_flow_graph, loop_nesting_tree):
        ConstraintSystem.__init__(self)
        self._filename = '{}.{}.super.ilp'.format(globals.args['filename_prefix'], 
                                                  control_flow_graph.name)
        self.__loop_exit_edges = set()
        start = timeit.default_timer()
        self.__create_objective_function(control_flow_graph)
        self.__create_constraints(control_flow_graph,
                                             loop_nesting_tree)
        self._create_integer_constraint()
        end = timeit.default_timer()
        self._construction_time = end - start
                
        
    def __create_objective_function(self, control_flow_graph):
        self.obj_function = 'max: '
        counter = len(control_flow_graph.basic_block_vertices)
        for _, subgraph in control_flow_graph.super_block_graph_iterator():
            for super_vertex in subgraph:
                for induced_vertex in super_vertex.vertices:
                    if ProgramPointVertex.is_basic_block(induced_vertex.program_point)\
                    and not induced_vertex.abstract:
                        vertex_variable = get_variable_for_program_point\
                                            (induced_vertex.program_point,
                                             self._variables)   
                        cfg_vertex = control_flow_graph.get_vertex_for_program_point\
                                        (induced_vertex.program_point)
                        self.obj_function += '{} {}'.format(cfg_vertex.wcet,
                                                            vertex_variable)
                        if counter > 1:
                            self.obj_function += ' + '
                        counter -= 1
        self.obj_function += ';'
        
        
    def __create_constraints(self, control_flow_graph, loop_nesting_tree):        
        for level, tree_vertices in loop_nesting_tree.level_by_level_iterator\
                                    (abstract_vertices_only=True):
            for abstract_vertex in tree_vertices:
                if ProgramPointVertex.is_basic_block(abstract_vertex.program_point):
                    subgraph = control_flow_graph.get_super_block_subgraph\
                                (abstract_vertex)
                    for super_vertex in subgraph:
                        self.__create_intra_super_block_constraints(super_vertex)
                                
                        if super_vertex.number_of_predecessors() > 1:
                            self.__create_predecessor_super_block_constraints\
                                (subgraph, super_vertex)
                            
                        if super_vertex.number_of_successors() > 1\
                        and not super_vertex.representative.abstract:
                            self.__create_successor_super_block_constraints\
                                (control_flow_graph, subgraph, super_vertex)
                                
                    self.__create_loop_bound_constraints(control_flow_graph, 
                                                         loop_nesting_tree, 
                                                         level, 
                                                         abstract_vertex)
                            
                            
    def __create_intra_super_block_constraints(self, 
                                               super_vertex):
        for induced_vertex in super_vertex.vertices:
            if induced_vertex != super_vertex.representative\
            and not induced_vertex.abstract:
                if ProgramPointVertex.is_basic_block(induced_vertex.program_point)\
                or induced_vertex.program_point in self.__loop_exit_edges:
                    constraint = get_variable_for_program_point\
                                        (induced_vertex.program_point,
                                         self._variables)
                    constraint += ' = '
                    constraint += get_variable_for_program_point\
                                        (super_vertex.representative.program_point,
                                         self._variables)
                    constraint += ';'
                    self._constraints.add(constraint)
                
                
    def __create_predecessor_super_block_constraints(self,
                                                     subgraph, 
                                                     super_vertex):
        
        if super_vertex.representative.abstract:  
            # An abstract vertex in its own super block
            constraint = ''
            counter = super_vertex.number_of_successors()
            for succ_edge in super_vertex.successor_edge_iterator():
                super_succ_vertex = subgraph.get_vertex(succ_edge.vertex_id)
                constraint += get_variable_for_program_point(super_succ_vertex.
                                                           representative.
                                                           program_point,
                                                           self._variables)
                if counter > 1:
                    constraint += ' + '
                counter -= 1
        else:   
            constraint = get_variable_for_program_point(super_vertex.
                                                      representative.
                                                      program_point,
                                                      self._variables)
            
        constraint += ' = '
        counter = super_vertex.number_of_predecessors()
        for pred_edge in super_vertex.predecessor_edge_iterator():
            super_pred_vertex = subgraph.get_vertex\
                                (pred_edge.vertex_id)
            constraint += get_variable_for_program_point(super_pred_vertex.
                                                       representative.
                                                       program_point,
                                                       self._variables)
            if counter > 1:
                constraint += ' + '
            counter -= 1
        constraint += ';'
        self._constraints.add(constraint)
        
        
    def __create_successor_super_block_constraints(self,
                                                   control_flow_graph,
                                                   subgraph,
                                                   super_vertex):        
        for _, partition in super_vertex.successor_edge_partition_iterator():
            if len(partition) > 1:
                constraint = get_variable_for_program_point(super_vertex.
                                                          representative.
                                                          program_point,
                                                          self._variables)
                constraint += ' = '
                counter = len(partition)
                for succ_edge in partition:
                    super_succ_vertex = subgraph.get_vertex(succ_edge.vertex_id)
                    constraint += get_variable_for_program_point\
                                        (super_succ_vertex.
                                         representative.
                                         program_point,
                                         self._variables)
                    if counter > 1:
                        constraint += ' + '
                    counter -= 1
                constraint += ';'
                self._constraints.add(constraint)
    
    
    def __create_loop_bound_constraints(self,
                                        control_flow_graph,
                                        loop_nesting_tree,
                                        level,
                                        abstract_vertex):
        
        def get_subgraph_of_outer_loop(subgraph, super_vertex):
            for _, candidate_subgraph in control_flow_graph.\
                                            super_block_graph_iterator():
                if subgraph.root_vertex.vertex_id !=\
                    candidate_subgraph.root_vertex.vertex_id\
                and candidate_subgraph.has_vertex_for_program_point(super_vertex.
                                                                    representative.
                                                                    program_point):
                    return candidate_subgraph
        
        def create_local_loop_bound_constraint(abstract_vertex):
            header = control_flow_graph.get_vertex_for_program_point\
                                            (abstract_vertex.program_point)
            subgraph = control_flow_graph.get_super_block_subgraph(abstract_vertex)
            constraint = get_variable_for_program_point(abstract_vertex.
                                                      program_point,
                                                      self._variables)
            if abstract_vertex.program_point == loop_nesting_tree.root_vertex.program_point:
                constraint += ' = {};'.format(max(header.loop_bound))
            else:
                constraint += ' <= ' 
                loop_exit_super_blocks = [super_vertex for super_vertex in subgraph
                                          if super_vertex.is_loop_exit_edge]
                parent_subgraph = get_subgraph_of_outer_loop(subgraph,
                                                             loop_exit_super_blocks[0])                             
                
                counter = len(loop_exit_super_blocks)
                for succ_vertex in loop_exit_super_blocks:
                    succ_vertex_in_parent_subgraph =\
                        parent_subgraph.get_vertex_for_program_point\
                            (succ_vertex.representative.program_point)
                    constraint += '{} {}'.format(max(header.loop_bound),
                                                 get_variable_for_program_point
                                                 (succ_vertex_in_parent_subgraph.
                                                  representative.
                                                  program_point,
                                                  self._variables))
                    self.__loop_exit_edges.add(succ_vertex.
                                               representative.
                                               program_point)
                    if counter > 1:
                        constraint += ' + '
                    counter -= 1 
                constraint += ';'
            self._constraints.add(constraint)
            
        
        def create_global_loop_bound_constraint(abstract_vertex):
            header = control_flow_graph.get_vertex_for_program_point\
                                            (abstract_vertex.program_point)
            constraint = get_variable_for_program_point(abstract_vertex.program_point,
                                                      self._variables)
            constraint += ' <= '
            constraint += '{};'.format(sum(header.loop_bound))
            self._constraints.add(constraint)
        
        create_local_loop_bound_constraint(abstract_vertex)
        if level > 1:
            create_global_loop_bound_constraint(abstract_vertex) 
                    
        
        
class IntegerLinearProgramForSuperBlockGraphWithFolding(IntegerLinearProgram):
    
    """
    The integer linear program derived after pre-solving execution times of
    super blocks.
    """
    
    def __init__(self, control_flow_graph, loop_nesting_tree):
        ConstraintSystem.__init__(self)
        self._filename = '{}.{}.folded.super.ilp'.\
                            format(globals.args['filename_prefix'], 
                                   control_flow_graph.name)
        start = timeit.default_timer()
        self.__create_objective_function(control_flow_graph)
        self.__create_constraints(control_flow_graph,
                                  loop_nesting_tree)
        self._create_integer_constraint()
        end = timeit.default_timer()
        self._construction_time = end - start
                
        
    def __create_objective_function(self, control_flow_graph):
        self.obj_function = 'max: '
        for _, subgraph in control_flow_graph.super_block_graph_iterator():
            for super_vertex in subgraph:
                super_block_wcet = 0
                for induced_vertex in super_vertex.vertices:
                    if ProgramPointVertex.is_basic_block(induced_vertex.program_point)\
                    and not induced_vertex.abstract:
                        cfg_vertex = control_flow_graph.get_vertex_for_program_point\
                                        (induced_vertex.program_point)
                        super_block_wcet += cfg_vertex.wcet
                
                vertex_variable = get_variable_for_program_point\
                                    (super_vertex.representative.program_point,
                                     self._variables)
                self.obj_function += '{} {}'.format(super_block_wcet,
                                                    vertex_variable)
                self.obj_function += ' + '
        strip_index = self.obj_function.rfind('+')
        self.obj_function = self.obj_function[:strip_index]
        self.obj_function += ';'
        
        
    def __create_constraints(self, control_flow_graph, loop_nesting_tree):        
        for level, tree_vertices in loop_nesting_tree.level_by_level_iterator\
                                    (abstract_vertices_only=True):
            for abstract_vertex in tree_vertices:
                if ProgramPointVertex.is_basic_block(abstract_vertex.program_point):
                    subgraph = control_flow_graph.get_super_block_subgraph\
                                (abstract_vertex)
                    for super_vertex in subgraph:
                        if super_vertex.number_of_predecessors() > 1:
                            self.__create_predecessor_super_block_constraints\
                                (subgraph, super_vertex)
                            
                        if super_vertex.number_of_successors() > 1\
                        and not super_vertex.representative.abstract:
                            self.__create_successor_super_block_constraints\
                                (control_flow_graph, subgraph, super_vertex)
                                
                    self.__create_loop_bound_constraints(control_flow_graph, 
                                                         loop_nesting_tree, 
                                                         level, 
                                                         abstract_vertex)
                
                
    def __create_predecessor_super_block_constraints(self,
                                                     subgraph, 
                                                     super_vertex):
        if super_vertex.representative.abstract:  
            # An abstract vertex in its own super block
            constraint = ''
            counter = super_vertex.number_of_successors()
            for succ_edge in super_vertex.successor_edge_iterator():
                super_succ_vertex = subgraph.get_vertex(succ_edge.vertex_id)
                constraint += get_variable_for_program_point(super_succ_vertex.
                                                           representative.
                                                           program_point,
                                                           self._variables)
                if counter > 1:
                    constraint += ' + '
                counter -= 1
        else:   
            constraint = get_variable_for_program_point(super_vertex.
                                                      representative.
                                                      program_point,
                                                      self._variables)
            
        constraint += ' = '
        counter = super_vertex.number_of_predecessors()
        for pred_edge in super_vertex.predecessor_edge_iterator():
            super_pred_vertex = subgraph.get_vertex\
                                (pred_edge.vertex_id)
            constraint += get_variable_for_program_point(super_pred_vertex.
                                                       representative.
                                                       program_point,
                                                       self._variables)
            if counter > 1:
                constraint += ' + '
            counter -= 1
        constraint += ';'
        self._constraints.add(constraint)
        
        
    def __create_successor_super_block_constraints(self,
                                                   control_flow_graph,
                                                   subgraph,
                                                   super_vertex):        
        for _, partition in super_vertex.successor_edge_partition_iterator():
            if len(partition) > 1:
                constraint = get_variable_for_program_point(super_vertex.
                                                          representative.
                                                          program_point,
                                                          self._variables)
                constraint += ' = '
                counter = len(partition)
                for succ_edge in partition:
                    super_succ_vertex = subgraph.get_vertex(succ_edge.vertex_id)
                    constraint += get_variable_for_program_point\
                                        (super_succ_vertex.
                                         representative.
                                         program_point,
                                         self._variables)
                    if counter > 1:
                        constraint += ' + '
                    counter -= 1
                constraint += ';'
                self._constraints.add(constraint)
    
    
    def __create_loop_bound_constraints(self,
                                        control_flow_graph,
                                        loop_nesting_tree,
                                        level,
                                        abstract_vertex):
        
        def get_subgraph_of_outer_loop(subgraph, super_vertex):
            for _, candidate_subgraph in control_flow_graph.\
                                            super_block_graph_iterator():
                if subgraph.root_vertex.vertex_id !=\
                    candidate_subgraph.root_vertex.vertex_id\
                and candidate_subgraph.has_vertex_for_program_point(super_vertex.
                                                                    representative.
                                                                    program_point):
                    return candidate_subgraph
        
        def create_local_loop_bound_constraint(abstract_vertex):
            loop_exit_edge_in_parent_subgraph = {}
            subgraph = control_flow_graph.get_super_block_subgraph(abstract_vertex)
            header = control_flow_graph.get_vertex_for_program_point\
                                            (abstract_vertex.program_point)
            super_vertex = subgraph.get_vertex_for_program_point(header.program_point)
            constraint = get_variable_for_program_point(super_vertex.
                                                      representative.
                                                      program_point,
                                                      self._variables)
            if abstract_vertex.program_point == loop_nesting_tree.root_vertex.program_point:
                constraint += ' = {};'.format(max(header.loop_bound))
            else:
                constraint += ' <= ' 
                loop_exit_super_blocks = [super_vertex for super_vertex in subgraph
                                          if super_vertex.is_loop_exit_edge]
                parent_subgraph = get_subgraph_of_outer_loop(subgraph,
                                                             loop_exit_super_blocks[0])                             
                
                counter = len(loop_exit_super_blocks)
                for succ_vertex in loop_exit_super_blocks:
                    succ_vertex_in_parent_subgraph =\
                        parent_subgraph.get_vertex_for_program_point\
                            (succ_vertex.representative.program_point)
                    constraint += '{} {}'.format(max(header.loop_bound),
                                                 get_variable_for_program_point
                                                 (succ_vertex_in_parent_subgraph.
                                                  representative.
                                                  program_point,
                                                  self._variables))
                    loop_exit_edge_in_parent_subgraph[succ_vertex] =\
                        succ_vertex_in_parent_subgraph
                    if counter > 1:
                        constraint += ' + '
                    counter -= 1 
                constraint += ';'
            self._constraints.add(constraint)
            
            # We need intra super block constraints on loop-exit edges.
            for super_vertex_one, super_vertex_two in loop_exit_edge_in_parent_subgraph.items():
                constraint = get_variable_for_program_point(super_vertex_one.
                                                          representative.
                                                          program_point, self._variables)
                constraint += ' = '
                constraint += get_variable_for_program_point(super_vertex_two.
                                                           representative.
                                                           program_point, self._variables)
                constraint += ';'
                self._constraints.add(constraint)
            
        
        def create_global_loop_bound_constraint(abstract_vertex):
            subgraph = control_flow_graph.get_super_block_subgraph(abstract_vertex)
            header = control_flow_graph.get_vertex_for_program_point\
                                            (abstract_vertex.program_point)
            super_vertex = subgraph.get_vertex_for_program_point(header.program_point)
            constraint = get_variable_for_program_point(super_vertex.
                                                      representative.
                                                      program_point,
                                                      self._variables)
            constraint += ' <= '
            constraint += '{};'.format(sum(header.loop_bound))
            self._constraints.add(constraint)
        
        create_local_loop_bound_constraint(abstract_vertex)
        if level > 1:
            create_global_loop_bound_constraint(abstract_vertex) 
            
            

class IntegerLinearProgramForInstrumentationPointGraph(IntegerLinearProgram):
    
    """
    The integer linear program derived from a control flow graph, execution 
    times of basic blocks and upper bounds on loop header execution counts.
    """
    
    def __init__(self, 
                 instrumentation_point_graph, 
                 loop_nesting_tree,
                 program_point_data):
        ConstraintSystem.__init__(self)
        self._filename = '{}.{}.ipg.ilp'.format(globals.args['filename_prefix'], 
                                                instrumentation_point_graph.name)
        start = timeit.default_timer()
        self.__create_objective_function(instrumentation_point_graph,
                                         program_point_data)
        self.__create_structural_constraints(instrumentation_point_graph)
        self.__create_loop_bound_constraints(instrumentation_point_graph,
                                             loop_nesting_tree)
        self._create_integer_constraint()
        end = timeit.default_timer()
        self._construction_time = end - start
        
        
    def __evaluate_wcet_of_edge(self,
                                instrumentation_point_graph,
                                program_point_data,
                                edge):
        depth_first_search = directed_graphs.DepthFirstSearch(edge.path_expression,
                                                              edge.path_expression.root_vertex,
                                                              False)
        evaluations = {}
        for path_expression_vertex in depth_first_search.post_order:
            if isinstance(path_expression_vertex, ProgramPointVertex):
                vertex = instrumentation_point_graph.get_vertex_for_program_point\
                            (path_expression_vertex.program_point)
                evaluations[path_expression_vertex] = program_point_data.get_wcet(vertex.program_point)
            else:
                if path_expression_vertex.operator == RegularExpressionVertex.SEQUENCE:
                    wcet = 0
                    for succ_edge in path_expression_vertex.successor_edge_iterator():
                        path_expression_succ_vertex = edge.path_expression.get_vertex(succ_edge.vertex_id)
                        wcet += evaluations[path_expression_succ_vertex]
                    evaluations[path_expression_vertex] = wcet
        return evaluations[edge.path_expression.root_vertex]
        
        
    def __create_objective_function(self, 
                                    instrumentation_point_graph,
                                    program_point_data):
        self.obj_function = 'max: '
        
        counter = instrumentation_point_graph.number_of_vertices()
        for vertex in instrumentation_point_graph:
            vertex_variable = get_variable_for_program_point(vertex.program_point,
                                                             self._variables) 
            self.obj_function += '{} {}'.format(program_point_data.get_wcet(vertex.program_point), 
                                                vertex_variable)
            if counter > 1:
                self.obj_function += ' + '
            counter -= 1
        
        self.obj_function += ' + '
        
        counter = instrumentation_point_graph.number_of_edges()
        for vertex in instrumentation_point_graph:
            for succ_edge in vertex.successor_edge_iterator():
                succ_vertex = instrumentation_point_graph.get_vertex(succ_edge.vertex_id)
                wcet_of_edge = self.__evaluate_wcet_of_edge(instrumentation_point_graph, 
                                                            program_point_data,
                                                            succ_edge)
                vertex_variable = get_variable_for_edge_between_program_points(vertex.program_point,
                                                                               succ_vertex.program_point,
                                                                               self._variables) 
                self.obj_function += '{} {}'.format(wcet_of_edge, vertex_variable)
                if counter > 1:
                    self.obj_function += ' + '
                counter -= 1        
        self.obj_function += ';'
        
    def __create_structural_constraints(self, instrumentation_point_graph):
        for vertex in instrumentation_point_graph:
            constraint = get_variable_for_program_point(vertex.program_point, 
                                                        self._variables)
            constraint += ' = '
            counter = vertex.number_of_successors()
            for succ_edge in vertex.successor_edge_iterator():
                succ_vertex = instrumentation_point_graph.get_vertex\
                                (succ_edge.vertex_id)
                constraint += get_variable_for_edge_between_program_points(vertex.program_point,
                                                                           succ_vertex.program_point,
                                                                           self._variables) 
                if counter > 1:
                    constraint += ' + '
                counter -= 1
            constraint += ';'
            self._constraints.add(constraint)
            
            constraint = get_variable_for_program_point(vertex.program_point, 
                                                        self._variables)
            constraint += ' = '
            counter = vertex.number_of_predecessors()
            for pred_edge in vertex.predecessor_edge_iterator():
                pred_vertex = instrumentation_point_graph.get_vertex\
                                (pred_edge.vertex_id)
                constraint += get_variable_for_edge_between_program_points(pred_vertex.program_point,
                                                                           vertex.program_point,
                                                                           self._variables) 
                if counter > 1:
                    constraint += ' + '
                counter -= 1
            constraint += ';'
            self._constraints.add(constraint)
            
            
    def __create_loop_bound_constraints(self, 
                                        instrumentation_point_graph, 
                                        loop_nesting_tree):

        
        def create_local_loop_bound_constraint(abstract_vertex):
            vertices = instrumentation_point_graph.get_destinations_of_loopback_edges\
                        (abstract_vertex)
            
            constraint = ''
            counter = len(vertices)
            for vertex in vertices:
                constraint += get_variable_for_program_point(vertex.program_point,
                                                             self._variables)
                if counter > 1:
                    constraint += ' + '
                counter -= 1
                
            if abstract_vertex.program_point == loop_nesting_tree.root_vertex.program_point:
                constraint += ' = 1;'
            else:
                pass
            self._constraints.add(constraint)
            
        
        def create_global_loop_bound_constraint(abstract_vertex):
            pass
            
        
        for level, tree_vertices in loop_nesting_tree.\
                                    level_by_level_iterator\
                                        (abstract_vertices_only=True):
            for abstract_vertex in tree_vertices:
                if ProgramPointVertex.is_basic_block(abstract_vertex.program_point):
                    create_local_loop_bound_constraint(abstract_vertex)
                    if level > 1:
                        create_global_loop_bound_constraint(abstract_vertex)
                


    
            
    
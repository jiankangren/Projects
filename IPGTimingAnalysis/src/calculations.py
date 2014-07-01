import vertices
import debug
import config
import os
import subprocess
import shlex
import decimal
import abc

class LpSolve:
    comma        = ","
    edgePrefix   = "e_"
    equals       = " = "
    fileSuffix   = "ilp"
    int_         = "int"
    ltOrEqual    = " <= "
    max_         = "max: "
    plus         = " + "
    semiColon    = ";"
    vertexPrefix = "v_"
    
    @staticmethod
    def getEdgeVariable (edgeID):
        return "%s%d" % (LpSolve.edgePrefix, edgeID)
    
    @staticmethod
    def getVertexVariable (vertexID):
        return "%s%d" % (LpSolve.vertexPrefix, vertexID)
    
    @staticmethod
    def getComment (comment):
        return "// " + comment + "\n"
    
    @staticmethod
    def getNewLine (num=1):
        return "\n" * num  
    
class ILP():
    def __init__(self, filename, variable_prefix):
        self.filename                    = filename
        self.variable_prefix             = variable_prefix
        self.wcet                        = -1
        self.variable_execution_counts = {}
        
    def solve(self):
        debug.debug_message("Solving ILP", __name__, 10)
        cmd  = "lp_solve %s" % self.filename 
        proc = subprocess.Popen(cmd, 
                                shell=True, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE)
        if proc.wait() != 0:
            debug.exitMessage("Running '%s' failed" % cmd)
        for line in proc.stdout.readlines():
            if line.startswith("Value of objective function"):
                lexemes     = shlex.split(line)
                self._wcet = long(decimal.Decimal(lexemes[-1])) 
            elif line.startswith(LpSolve.edgePrefix) or line.startswith(LpSolve.vertexPrefix):
                lexemes = shlex.split(line)
                assert len(lexemes) == 2, "Incorrectly detected variable execution count line '%s'" % line
                prefix = lexemes[0][:2]
                if prefix == self.variable_prefix:
                    variable = int(lexemes[0][2:])
                    count    = int(lexemes[1]) 
                    self.variable_execution_counts[variable] = count
                    
    @abc.abstractmethod
    def print_execution_counts(self):
        pass
        
class CreateIPGILP (ILP):
    def __init__ (self, data, ipg, lnt, miniIPGs):
        filename = "%s.%s.%s.%s" % (config.Arguments.basepath + os.sep + config.Arguments.basename, ipg.name, "ipg", LpSolve.fileSuffix)
        ILP.__init__(self, filename, LpSolve.edgePrefix)
        with open(filename, 'w') as self.__outfile:
            self.__createObjectiveFunction(data, ipg)
            self.__createStructuralConstraints(ipg)
            self.__createRelativeCapacityConstraints(data, lnt, miniIPGs)
            self.__createIntegerConstraints(ipg)
        
    def print_execution_counts (self, ipg):
        for edgeID, count in self.variable_execution_counts.iteritems():
                debug.debug_message("Execution count of variable %s = %d" % (LpSolve.getEdgeVariable(edgeID), count), __name__, 10)
        basic_block_execution_counts = {}
        for v in ipg:
            for succID in v.getSuccessorIDs():                
                succe  = v.getSuccessorEdge(succID)
                edgeID = succe.getEdgeID() 
                if self.variable_execution_counts[edgeID]:
                    for bbID in succe.edge_label:
                        if bbID not in basic_block_execution_counts:
                            self.basic_block_execution_counts[bbID] = 0
                        self.basic_block_execution_counts[bbID] += self.variable_execution_counts[edgeID]
        for vertexID, count in self.basic_block_execution_counts.iteritems():
                debug.debug_message("Execution count of variable %s = %d" % (LpSolve.getVertexVariable(vertexID), count), __name__, 10)

    def __createObjectiveFunction (self, data, ipg):
        self.__outfile.write(LpSolve.max_)
        counter = ipg.numOfEdges()
        for v in ipg:
            for succID in v.getSuccessorIDs():                
                succe          = v.getSuccessorEdge(succID)
                edgeID         = succe.getEdgeID()
                transitionWCET = data.get_ipg_edge_wcet(v.vertexID, succID)
                self.__outfile.write("%d %s" % (transitionWCET, LpSolve.getEdgeVariable(edgeID)))
                if counter > 1:
                    self.__outfile.write(LpSolve.plus)
                counter -= 1
        self.__outfile.write(LpSolve.semiColon)
        self.__outfile.write(LpSolve.getNewLine(2))

    def __createStructuralConstraints (self, ipg):
        for v in ipg:
            self.__outfile.write(LpSolve.getComment("Vertex %d" % v.vertexID))
            # Analyse the predecessors
            self.__outfile.write(LpSolve.getVertexVariable(v.vertexID))
            self.__outfile.write(LpSolve.equals)
            counter = v.numberOfPredecessors()
            for predID in v.getPredecessorIDs():                    
                prede  = v.getPredecessorEdge(predID)
                edgeID = prede.getEdgeID()
                self.__outfile.write(LpSolve.getEdgeVariable(edgeID))
                if counter > 1:
                    self.__outfile.write(LpSolve.plus)
                counter -= 1
            self.__outfile.write(LpSolve.semiColon)
            self.__outfile.write(LpSolve.getNewLine())  
            # Flow in, flow out w.r.t to predecessors and successors
            counter = v.numberOfPredecessors()
            for predID in v.getPredecessorIDs():                    
                prede  = v.getPredecessorEdge(predID)
                edgeID = prede.getEdgeID()
                self.__outfile.write(LpSolve.getEdgeVariable(edgeID))
                if counter > 1:
                    self.__outfile.write(LpSolve.plus)
                counter -= 1
            self.__outfile.write(LpSolve.equals)   
            # Analyse the successors
            counter = v.numberOfSuccessors()
            for succID in v.getSuccessorIDs():
                succe  = v.getSuccessorEdge(succID)
                edgeID = succe.getEdgeID()
                self.__outfile.write(LpSolve.getEdgeVariable(edgeID))
                if counter > 1:
                    self.__outfile.write(LpSolve.plus)
                counter -= 1
            self.__outfile.write(LpSolve.semiColon)
            self.__outfile.write(LpSolve.getNewLine(2))
            
    def __createRelativeCapacityConstraints (self, data, lnt, miniIPGs):
        for level, the_vertices in lnt.levelIterator(True):
            for v in the_vertices:
                if isinstance(v, vertices.HeaderVertex):
                    # Get iteration edges for this header
                    if level > 0:
                        self.__createInnerLoopRelativeCapacityConstraint(data, lnt, miniIPGs, v)
                    else:
                        headerID = v.headerID
                        self.__outfile.write(LpSolve.getComment("Relative capacity constraint for entry vertex %d" % (headerID)))
                        iterationEdgeIDs = miniIPGs.getMiniIPG(headerID).getIterationEdgeIDs()
                        assert len(iterationEdgeIDs) == 1, "There should be exactly one iteration edge for the entry vertex %d. There are %d." % (headerID, len(iterationEdgeIDs))
                        edgeID = iter(iterationEdgeIDs).next()
                        self.__outfile.write(LpSolve.getEdgeVariable(edgeID))
                        self.__outfile.write(LpSolve.equals)
                        self.__outfile.write("1")
                        self.__outfile.write(LpSolve.semiColon)
                        self.__outfile.write(LpSolve.getNewLine(2))
                        
    def __createInnerLoopRelativeCapacityConstraint (self, data, lnt, miniIPGs, v):
        debug.debug_message("Analysing header %d" % v.headerID, __name__, 1)
        headerID       = v.headerID
        miniIPG        = miniIPGs.getMiniIPG(headerID)
        entryIpoints   = set([])
        ieDestinations = miniIPG.getIterationEdgeDestinations()
        decrementBound = {}
        for succID in v.getSuccessorIDs():
            if succID in ieDestinations:
                entryIpoints.add(succID)
                if self.__inLoopExit(succID, miniIPG, lnt, headerID):
                    decrementBound[succID] = False
                else:
                    decrementBound[succID] = True
        for ancestorv in lnt.getAllProperAncestors(v.vertexID):
            # Get the loop bound w.r.t. the ancestor loop
            ancestorHeaderID = ancestorv.headerID
            self.__outfile.write(LpSolve.getComment("Relative capacity constraint for header %d w.r.t to header %d" % (headerID, ancestorHeaderID)))
            bound = data.get_loop_bound(headerID, ancestorHeaderID)
            # Write out the relative edges
            outerMiniIPG        = miniIPGs.getMiniIPG(ancestorHeaderID)
            outerIpoints        = set([])
            ieOuterDestinations = outerMiniIPG.getIterationEdgeDestinations()
            for succID in ancestorv.getSuccessorIDs():
                if succID in ieOuterDestinations:
                    outerIpoints.add(succID)
            if len(outerIpoints) == 0:
                debug.debug_message("Loop with header %d does not have Ipoints at its nesting level which are at entry Ipoints" % (ancestorHeaderID), __name__, 1)
                ieOuterSources = outerMiniIPG.getIterationEdgeSources()
                for succID in ancestorv.getSuccessorIDs():
                    if succID in ieOuterSources:
                        outerIpoints.add(succID)
            # Write out the entry Ipoints
            for entryID in entryIpoints:
                self.__outfile.write(LpSolve.getVertexVariable(entryID))
                self.__outfile.write(LpSolve.ltOrEqual)
                counter = len(outerIpoints)
                for vertexID in outerIpoints:
                    if decrementBound[entryID] and not lnt.isDoWhileLoop(headerID):
                        self.__outfile.write("%d %s" % (bound - 1, LpSolve.getVertexVariable(vertexID)))
                    else:
                        self.__outfile.write("%d %s" % (bound, LpSolve.getVertexVariable(vertexID)))
                    if counter > 1:
                        self.__outfile.write(LpSolve.plus)
                    counter -= 1
                self.__outfile.write(LpSolve.semiColon)
                self.__outfile.write(LpSolve.getNewLine())
            self.__outfile.write(LpSolve.getNewLine())
    
    def __inLoopExit (self, ipointID, miniIPG, lnt, headerID):
        for exitID in lnt.getLoopExits(headerID):
            if ipointID in miniIPG.getReachableSet(exitID):
                return True
        return False
            
    def __createIntegerConstraints (self, ipg):
        self.__outfile.write(LpSolve.int_)
        counter = ipg.numOfEdges()
        for v in ipg:
            for succID in v.getSuccessorIDs():                
                succe  = v.getSuccessorEdge(succID)
                edgeID = succe.getEdgeID()
                self.__outfile.write(" %s" % LpSolve.getEdgeVariable(edgeID))
                if counter > 1:
                    self.__outfile.write(LpSolve.comma)
                counter -= 1
        self.__outfile.write(LpSolve.semiColon)
        self.__outfile.write(LpSolve.getNewLine())
                
class CreateICFGILP (ILP):
    def __init__ (self, data, icfg, lnt):
        filename = "%s.%s.%s.%s" % (config.Arguments.basepath + os.sep + config.Arguments.basename, icfg.name, "icfg", LpSolve.fileSuffix)
        ILP.__init__(self, filename, LpSolve.vertexPrefix)
        
        self.__vertexIDToExecutionCount = {}
        with open(filename, 'w') as self.__outfile:
            self.__createObjectiveFunction(data, icfg)
            self.__createStructuralConstraints(icfg)
            self.__createRelativeCapacityConstraints(data, lnt, icfg)
            self.__createIntegerConstraints(icfg)

    def print_execution_counts (self, icfg):
        for vertexID, count in self.variable_execution_counts.iteritems():
            if not icfg.isIpoint(vertexID):
                debug.debug_message("Execution count of variable %s = %d" % (LpSolve.getVertexVariable(vertexID), count), __name__, 10)

    def __createObjectiveFunction (self, data, icfg):
        self.__outfile.write(LpSolve.max_)        
        counter = icfg.numOfVertices()
        for v in icfg:        
            vertexWCET = data.get_basic_block_wcet(v.vertexID)
            self.__outfile.write("%d %s" % (vertexWCET, LpSolve.getVertexVariable(v.vertexID)))
            if counter > 1:
                self.__outfile.write(LpSolve.plus)
            counter -= 1
        self.__outfile.write(LpSolve.semiColon)
        self.__outfile.write(LpSolve.getNewLine(2))
            
    def __createStructuralConstraints (self, icfg):
        for v in icfg:
            self.__outfile.write(LpSolve.getComment("Vertex %d" % v.vertexID))
            # Flow into vertex w.r.t. predecessors
            self.__outfile.write(LpSolve.getVertexVariable(v.vertexID))
            self.__outfile.write(LpSolve.equals)
            counter = v.numberOfPredecessors()
            for predID in v.getPredecessorIDs():                    
                prede  = v.getPredecessorEdge(predID)
                edgeID = prede.getEdgeID()
                self.__outfile.write(LpSolve.getEdgeVariable(edgeID))
                if counter > 1:
                    self.__outfile.write(LpSolve.plus)
                counter -= 1
            self.__outfile.write(LpSolve.semiColon)
            self.__outfile.write(LpSolve.getNewLine())     
            # Flow in, flow out w.r.t to predecessors and successors
            counter = v.numberOfPredecessors()
            for predID in v.getPredecessorIDs():                    
                prede  = v.getPredecessorEdge(predID)
                edgeID = prede.getEdgeID()
                self.__outfile.write(LpSolve.getEdgeVariable(edgeID))
                if counter > 1:
                    self.__outfile.write(LpSolve.plus)
                counter -= 1
            self.__outfile.write(LpSolve.equals)
            counter = v.numberOfSuccessors()
            for succID in v.getSuccessorIDs():
                succe  = v.getSuccessorEdge(succID)
                edgeID = succe.getEdgeID()
                self.__outfile.write(LpSolve.getEdgeVariable(edgeID))
                if counter > 1:
                    self.__outfile.write(LpSolve.plus)
                counter -= 1
            self.__outfile.write(LpSolve.semiColon)
            self.__outfile.write(LpSolve.getNewLine(2))       
            
    def __createRelativeCapacityConstraints (self, data, lnt, icfg):
        for level, the_vertices in lnt.levelIterator(True):
            for v in the_vertices:
                if isinstance(v, vertices.HeaderVertex):
                    # Get iteration edges for this header
                    if level > 0:
                        self.__createInnerLoopRelativeCapacityConstraint(data, icfg, lnt, v)
                    else:
                        headerID = v.headerID
                        self.__outfile.write(LpSolve.getComment("Relative capacity constraint for entry vertex %d" % (headerID)))
                        self.__outfile.write(LpSolve.getVertexVariable(icfg.getEntryID()))
                        self.__outfile.write(LpSolve.equals)
                        self.__outfile.write("1")
                        self.__outfile.write(LpSolve.semiColon)
                        self.__outfile.write(LpSolve.getNewLine(2))
                        
    def __createInnerLoopRelativeCapacityConstraint (self, data, icfg, lnt, v):
        debug.debug_message("Analysing header %d" % v.headerID, __name__, 1)
        headerID         = v.headerID
        parentv          = lnt.getVertex(v.getParentID())
        relativeHeaderID = headerID
        for ancestorv in lnt.getAllProperAncestors(v.vertexID):
            # Get the loop bound w.r.t. the ancestor loop
            ancestorHeaderID = ancestorv.headerID
            bound = data.get_loop_bound(headerID, ancestorHeaderID)
            self.__outfile.write(LpSolve.getComment("Relative capacity constraint for header %d w.r.t to header %d" % (headerID, ancestorHeaderID)))
            self.__outfile.write(LpSolve.getComment("Bound = %d" % bound))
            self.__outfile.write(LpSolve.getVertexVariable(headerID))
            self.__outfile.write(LpSolve.ltOrEqual)
            # Write out the relative edges
            relativeEdgeIDs = self.__getLoopEntryEdges(icfg, lnt, relativeHeaderID)
            counter         = len(relativeEdgeIDs)
            for edgeID in relativeEdgeIDs:
                self.__outfile.write("%d %s" % (bound, LpSolve.getEdgeVariable(edgeID)))
                if counter > 1:
                    self.__outfile.write(LpSolve.plus)
                counter -= 1
            parentv          = lnt.getVertex(v.getParentID())
            relativeHeaderID = parentv.headerID
            self.__outfile.write(LpSolve.semiColon)
            self.__outfile.write(LpSolve.getNewLine(2))
            
    def __getLoopEntryEdges (self, icfg, lnt, headerID):
        edgeIDs = []
        v       = icfg.getVertex(headerID)
        for predID in v.getPredecessorIDs():
            if not lnt.isLoopBackEdge(predID, headerID):
                prede = v.getPredecessorEdge(predID)
                edgeIDs.append(prede.getEdgeID())
        assert edgeIDs, "Unable to find loop-entry edges into loop with header %d" % headerID
        return edgeIDs
    
    def __createIntegerConstraints (self, icfg):
        self.__outfile.write(LpSolve.int_)
        counter = icfg.numOfVertices() + icfg.numOfEdges()
        for v in icfg:
            self.__outfile.write(" %s" % LpSolve.getVertexVariable(v.vertexID))
            if counter > 1:
                self.__outfile.write(LpSolve.comma)
            counter -= 1
            for succID in v.getSuccessorIDs():
                succe  = v.getSuccessorEdge(succID)
                edgeID = succe.getEdgeID()
                self.__outfile.write(" %s" % LpSolve.getEdgeVariable(edgeID))
                if counter > 1:
                    self.__outfile.write(LpSolve.comma)
                counter -= 1
        self.__outfile.write(LpSolve.semiColon)
        self.__outfile.write(LpSolve.getNewLine())
    
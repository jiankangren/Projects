import edges
import vertices
import debug
import arm
import config
import random
import os
import shlex
import gzip

newTrace = "=>"
endTrace = "<="

class Generatetraces:
    maxNumberOfCalls  = 20
    maxLoopIterations = 10
    
    def __init__ (self, program, numberOftraces=1):
        self.__program = program
        filename       = config.Arguments.basepath + os.sep + config.Arguments.basename + ".traces"
        with open(filename, 'w') as self.__outfile:
            for trace in xrange(1, numberOftraces+1):
                debug.debug_message("Generating trace #%d" % trace, 1)
                self.__outfile.write("%s\n" % newTrace)
                self.__generateTrace() 
                self.__outfile.write("\n%s\n" % endTrace)
    
    def __generateTrace (self):
        # To keep track of loop tail iteration count
        self.__functionToTailCount = {}
        # To keep trace of the number of function calls
        self.__numberOfCalls = 0
        callg = self.__program.getCallGraph()
        rootv = callg.getVertex(callg.getRootID())
        self.__currentCallv = rootv
        self.__currentCFG  = self.__program.getCFG(rootv.getName())
        self.__currentLNT   = self.__program.getLNT(rootv.getName())
        self.__currentv     = self.__currentCFG.getVertex(self.__currentCFG.getEntryID())
        self.__vertexID     = self.__currentv.vertexID
        self.__callStack    = []
        while True: 
            self.__outfile.write("%d " % self.__vertexID)
            if self.__vertexID == self.__currentCFG.getExitID():
                if callg.getVertexWithName(self.__currentCFG.getName()) == rootv:
                    # End of the program reached
                    break
                else:
                    # End of function call
                    debug.debug_message("Returning from %s" % self.__currentCallv.getName(), 5)
                    self.__currentCallv, self.__currentCFG, self.__currentLNT, self.__currentv = self.__callStack.pop()
                    self.__vertexID  = self.__currentv.vertexID
                    # Go past the call site
                    self.__chooseSuccessorInICFG()
            elif self.__currentLNT.isLoopTail(self.__vertexID):
                tupleIndex = self.__currentCFG.getName(), self.__vertexID
                if tupleIndex not in self.__functionToTailCount:
                    self.__functionToTailCount[tupleIndex] = 1
                    self.__chooseSuccessorInICFG()
                elif self.__functionToTailCount[tupleIndex] < Generatetraces.maxLoopIterations:
                    self.__functionToTailCount[tupleIndex] += 1
                    self.__chooseSuccessorInICFG()
                else:
                    self.__chooseNonLoopBackEdgeSuccessorInICFG()
            elif self.__currentCFG.isCallSite(self.__vertexID):
                # Make the call. First save state then move to the callee ICFG
                self.__callStack.append((self.__currentCallv, self.__currentCFG, self.__currentLNT, self.__currentv))
                succID              = self.__currentCallv.getSuccessorWithCallSite(self.__vertexID)
                self.__currentCallv = callg.getVertex(succID)
                calleeName          = self.__currentCallv.getName()
                debug.debug_message("Calling %s" % self.__currentCallv.getName(), 5)
                self.__currentCFG  = self.__program.getICFG(calleeName)
                self.__currentLNT   = self.__program.getLNT(calleeName)
                self.__currentv     = self.__currentCFG.getVertex(self.__currentCFG.getEntryID())
                self.__vertexID     = self.__currentv.vertexID
            else:
                self.__chooseSuccessorInICFG()
    
    def __chooseSuccessorInICFG (self):
        succIndex = random.randint(0, self.__currentv.numberOfSuccessors() - 1)
        succID    = self.__currentv.getSuccessorIDs()[succIndex]
        self.__currentv = self.__currentCFG.getVertex(succID)
        self.__vertexID = self.__currentv.vertexID
        
    def __chooseNonLoopBackEdgeSuccessorInICFG (self):
        succIDs = [succID for succID in self.__currentv.getSuccessorIDs() if not self.__currentLNT.isLoopBackEdge(self.__vertexID, succID)]
        succIndex = random.randint(0, len(succIDs) - 1)
        succID    = succIDs[succIndex]
        self.__currentv = self.__currentCFG.getVertex(succID)
        self.__vertexID = self.__currentv.vertexID
        
class TraceInformation:
    def __init__ (self, program):
        self._program    = program
        self._allruns    = set([])
        self._initialiseOptionalPathInformation()
        self._initialiseRequiredPathInformation()
        
    def _initialiseOptionalPathInformation (self):
        self._executionCountsThisRun = {}
        self._relativeExecutionCountsThisRun = {}
        for cfg in self._program.getcfgs():
            pathg        = self._program.getPathInfoGraph(cfg.name)
            lnt          = self._program.getLNT(cfg.name)
            self._executionCountsThisRun[pathg] = {}
            self._relativeExecutionCountsThisRun[pathg] = {}
            for v in pathg:
                self._executionCountsThisRun[pathg][v.vertexID] = 0
            for headerID in lnt.getHeaderIDs():
                self._executionCountsThisRun[pathg][headerID] = 0
                self._relativeExecutionCountsThisRun[pathg][headerID] = 0
    
    def _initialiseRequiredPathInformation (self):
        self._longestTime = 0
        self._executionTimes = {}
        for cfg in self._program.getcfgs():
            functionName = cfg.getName()
            for v in cfg:
                self._executionTimes[(functionName, v.getOriginalVertexID())] = 0
            
    def _endOfFunction (self, cfg, lnt, pathg):
        functionName = cfg.getName()
        debug.debug_message("Falsifying conjectures in %s" % functionName, 10)
        # Mutual inclusion and mutual exclusion
        for v in pathg:
            vertexID       = v.vertexID
            executionCount = self._executionCountsThisRun[pathg][vertexID]
            # Capacity execution counts 
            for succe in v.getSuccessoredges(edges.PathInformationEdgeType.CAPACITY_BOUNDS):
                if executionCount < succe.lower:
                    debug.debug_message("Falsifying conjecture that %s executes at least %d times. Found %d instead"  % (v.__str__(), succe.lower, executionCount), 1)
                    succe.lower = executionCount
                if executionCount > succe.upper:
                    debug.debug_message("Falsifying conjecture that %s executes at most %d times. Found %d instead"  % (v.__str__(), succe.upper, executionCount), 1)
                    succe.upper = executionCount
            # If this vertex has been triggered in this run
            if executionCount > 0:
                # Falsify execution implication conjectures
                mutualExclusionCandiates = set([])
                falsified = set([])
                for succe in v.getSuccessoredges(edges.PathInformationEdgeType.INCLUSION):
                    succID = succe.vertexID
                    if self._executionCountsThisRun[pathg][succID] == 0:
                        succv = pathg.getVertex(succID)
                        debug.debug_message("When %s executes, %s does not always execute (EXECUTION DEPENDENCE FALSIFIED)" % (v.__str__(), succv.__str__()), 1)
                        falsified.add(succID)
                        if not succv.hasSuccessorEdge(vertexID, edges.PathInformationEdgeType.INCLUSION):
                            mutualExclusionCandiates.add(succID)
                for succID in falsified:
                    v.removeSuccessorEdge(succID, edges.PathInformationEdgeType.INCLUSION)
                # Falsify mutual-exclusion conjectures
                falsified = set([])
                for succe in v.getSuccessoredges(edges.PathInformationEdgeType.EXCLUSION):
                    succID = succe.vertexID
                    if self._executionCountsThisRun[pathg][succID] > 0:
                        succv = pathg.getVertex(succID)
                        debug.debug_message("When %s executes, %s may execute (EXCLUSIVITY FALSIFIED)" % (v.__str__(), succv.__str__()), 1)
                        falsified.add(succID)
                for succID in falsified:
                    v.removeSuccessorEdge(succID, edges.PathInformationEdgeType.EXCLUSION) 
                    succv = pathg.getVertex(succID)
                    succv.removeSuccessorEdge(vertexID, edges.PathInformationEdgeType.EXCLUSION)
                # Add mutual-exclusion conjectures
                for succID in mutualExclusionCandiates:
                    succv = pathg.getVertex(succID)
                    v.addSuccessorEdge(succID, edges.PathInformationEdgeType.EXCLUSION)
                    succv.addSuccessorEdge(vertexID, edges.PathInformationEdgeType.EXCLUSION)
                    debug.debug_message("New conjecture: %s and %s are MUTUALLY EXCLUSIVE" % (v.__str__(), succv.__str__()), 1)
        
        for headerID in lnt.getHeaderIDs():
            programPoint   = list(pathg.getLoopMonitoredProgramPoints(headerID))[0]
            pathv          = pathg.getProgramPointVertex(programPoint)
            succe          = pathv.getSuccessoredges(edges.PathInformationEdgeType.LOOP_BOUNDS)[0]
            executionCount = self._executionCountsThisRun[pathg][headerID]
            if executionCount > succe.upper:
                debug.debug_message("Falsifying conjecture that %d executes at most %d times. Found %d instead"  % (headerID, succe.upper, executionCount), 1)
                succe.upper = executionCount
            self._executionCountsThisRun[pathg][headerID] = 0
        
        for v in pathg:
            vertexID = v.vertexID
            self._executionCountsThisRun[pathg][vertexID] = 0
    
    def _end (self):
        for cfg in self._program.getcfgs():
            functionName = cfg.getName()
            pathg        = self._program.getPathInfoGraph(functionName)            
            debug.verbose_message(
"""%s
FUNCTION '%s'
%s""" \
% ('*' * 100, functionName, '*' * 100), __name__)
            for vertexID1, vertexID2 in pathg.mutualInclusionPairs():
                v1 = pathg.getVertex(vertexID1)
                v2 = pathg.getVertex(vertexID2)
                succe1 = v1.getSuccessoredges(edges.PathInformationEdgeType.CAPACITY_BOUNDS)[0]
                succe2 = v2.getSuccessoredges(edges.PathInformationEdgeType.CAPACITY_BOUNDS)[0]
                if succe1.lower > 0 and succe2.lower > 0:
                    debug.verbose_message("  IGNORING MUTUAL INCLUSION: %s and %s" % (v1.__str__(), v2.__str__()), __name__)
                    v1.removeSuccessorEdge(vertexID2, edges.PathInformationEdgeType.INCLUSION)
                    v2.removeSuccessorEdge(vertexID1, edges.PathInformationEdgeType.INCLUSION)
            
            for v in pathg:
                vertexID = v.vertexID
                succe = v.getSuccessoredges(edges.PathInformationEdgeType.CAPACITY_BOUNDS)[0]
                if succe.lower == 0 and succe.upper == 0:
                    for succe in v.getSuccessoredges(edges.PathInformationEdgeType.INCLUSION):
                        succID = succe.vertexID
                        succv  = pathg.getVertex(succID)
                        succv.removeSuccessorEdge(vertexID, edges.PathInformationEdgeType.INCLUSION)
                        debug.verbose_message("  IGNORING MUTUAL INCLUSION BECAUSE OF DEAD CODE: %s and %s" % (v.__str__(), succv.__str__()), __name__)
                    for succe in v.getSuccessoredges(edges.PathInformationEdgeType.EXCLUSION):
                        succID = succe.vertexID
                        succv  = pathg.getVertex(succID)
                        succv.removeSuccessorEdge(vertexID, edges.PathInformationEdgeType.EXCLUSION)
                        debug.verbose_message("  IGNORING MUTUAL EXCLUSION BECAUSE OF DEAD CODE: %s and %s" % (v.__str__(), succv.__str__()), __name__)
                    v.removeAllSuccessors()
    
    def _normaliseData (self):
        for tupleKey in self._executionTimes.keys():
            self._executionTimes[tupleKey] *= pow(10,-3)
        self._longestTime *= pow(10,-3)
        
    def __computeInnerRelativeBounds (self, pathg, lnt, pathv, headerv):
        for succID in headerv.getSuccessorIDs():
            succv = lnt.getVertex(succID)
            if isinstance(succv, vertices.HeaderVertex):
                innerHeaderID     = succv.getHeaderID()
                innerProgramPoint = list(pathg.getLoopMonitoredProgramPoints(innerHeaderID))[0]
                innerPathv        = pathg.getProgramPointVertex(innerProgramPoint)
                succe             = innerPathv.getSuccessoredges(edges.PathInformationEdgeType.LOOP_BOUNDS)[0]
                executionCount    = self._relativeExecutionCountsThisRun[pathg][innerHeaderID]
                if executionCount > succe.relative:
                    debug.debug_message("Falsifying conjecture that %d executes at most %d times relative to its innermost enclosing loop. Found %d instead"  % (innerHeaderID, succe.relative, executionCount), 1)
                    succe.relative = executionCount
                self._relativeExecutionCountsThisRun[pathg][innerHeaderID] = 0
    
    def __analyseProgramPoint (self, pathg, lnt, pathv):
        vertexID = pathv.vertexID
        self._executionCountsThisRun[pathg][vertexID] += 1
        if pathv.isEffectiveHeaderCounter():
            for headerID in pathv.getHeaderIDsForWhichToCount():
                self._relativeExecutionCountsThisRun[pathg][headerID] += 1
                self._executionCountsThisRun[pathg][headerID] += 1
        headerv = lnt.getVertex(lnt.getVertex(pathv.getHeaderID()).getParentID())
        self.__computeInnerRelativeBounds(pathg, lnt, pathv, headerv)
              
    def _analyseCFGVertex (self, pathg, lnt, vertexID):
        pathv = pathg.isMonitoredVertex(vertexID)
        if pathv:
            self.__analyseProgramPoint(pathg, lnt, pathv)
            
    def _analyseCFGEdge (self, pathg, lnt, predID, succID):
        pathv = pathg.isMonitoredEdge(predID, succID)
        if pathv:
            self.__analyseProgramPoint(pathg, lnt, pathv)
            
    def getExecutionTime (self, functionName, vertexID):
        tupleKey = (functionName, vertexID)
        assert tupleKey in self._executionTimes
        return self._executionTimes[tupleKey]
    
    def getLongestTime (self):
        return self._longestTime      
            
    def _outputConjectures (self): 
        for cfg in self._program.getcfgs():
            functionName = cfg.getName()
            pathg        = self._program.getPathInfoGraph(functionName)
            debug.verbose_message(
"""%s
FUNCTION '%s'
%s""" \
% ('*' * 100, functionName, '*' * 100), __name__)
            
            for v in pathg:
                for succe in v.getSuccessoredges(edges.PathInformationEdgeType.CAPACITY_BOUNDS):
                    if succe.lower == 0 and succe.upper == 0:
                        debug.verbose_message("  NEVER EXECUTES: %s" % (v.__str__(),), __name__)
                    elif succe.lower > 0:
                        debug.verbose_message("  ALWAYS EXECUTES: %s, at least %d time(s), at most %d time(s)" % (v.__str__(), succe.lower, succe.upper), __name__)
                    else:
                        debug.verbose_message("  MAY EXECUTE: %s, at most %d time(s)" % (v.__str__(), succe.upper), __name__)
                    
            
            debug.verbose_message(
"""%s
DEPENDENT EXECUTION CONJECTURES
%s""" \
    % ('-' * 50, '-' * 50), __name__)
            for vertexID1, vertexID2 in pathg.mutualInclusionPairs():
                v1 = pathg.getVertex(vertexID1)
                v2 = pathg.getVertex(vertexID2)
                debug.verbose_message("  MUTUALLY INCLUSIVE: %s and %s" % (v1.__str__(), v2.__str__()), __name__)
            for vertexID1, vertexID2 in pathg.mutualExclusionPairs():
                v1 = pathg.getVertex(vertexID1)
                v2 = pathg.getVertex(vertexID2)
                debug.verbose_message("  MUTUALLY EXCLUSIVE: %s and %s" % (v1.__str__(), v2.__str__()), __name__)
            for vertexID1, vertexID2 in pathg.executionDependencies():
                v1 = pathg.getVertex(vertexID1)
                v2 = pathg.getVertex(vertexID2)
                debug.verbose_message("  ONE-WAY DEPENDENCY: %s on %s" % (v1.__str__(), v2.__str__()), __name__)
                
    def _outputCBMCConjectures (self): 
        for cfg in self._program.getcfgs():
            functionName = cfg.getName()
            pathg        = self._program.getPathInfoGraph(functionName)
            lnt          = self._program.getLNT(functionName)
            print(
"""%s
FUNCTION '%s'
%s""" \
% ('*' * 100, functionName, '*' * 100))
            
            print "#ifdef CBMC"
            
            for lntv in lnt:
                if isinstance(lntv, vertices.HeaderVertex):
                    headerID = lntv.getHeaderID()
                    if headerID != cfg.getEntryID():
                        loopBody = lnt.getLoopBody(headerID)
                        v        = cfg.getVertex(headerID)
                        forwardedges = []
                        for succID in v.getSuccessorIDs():
                            if succID in loopBody:
                                forwardedges.append((headerID, succID))
                        count = 1
                        lhs   = ""
                        for edge in forwardedges:
                            lhs += "__count_%d_%d " % (edge[0], edge[1])
                            if count < len(forwardedges):
                                lhs += " + "
                        relativeBound = 0
                        for programPoint in pathg.getLoopMonitoredProgramPoints(headerID):
                                pathv = pathg.getProgramPointVertex(programPoint)
                                succe = pathv.getSuccessoredges(edges.PathInformationEdgeType.LOOP_BOUNDS)[0]
                                relativeBound = max(relativeBound, succe.relative)
                        print("assert(%s <= %d); // Loop counter property" % (lhs, relativeBound))
            
            for v in pathg:
                programPoint = v.getProgramPoint()
                if isinstance(programPoint, tuple):
                    programPointStr = "__count_%d_%d" % (programPoint[0], programPoint[1])
                else:
                    programPointStr = "__count_%d" % programPoint
                for succe in v.getSuccessoredges(edges.PathInformationEdgeType.CAPACITY_BOUNDS):
                    if succe.lower == 0 and succe.upper == 0:
                        print("assert(%s == 0); // Dead code" % (programPointStr))
                    elif succe.lower > 0:
                        print("assert(%s >= %d); // Lower capacity constraint" % (programPointStr, succe.lower))
                        print("assert(%s <= %d); // Upper capacity constraint" % (programPointStr, succe.upper))
                    else:
                        print("assert(%s <= %d); // Upper capacity constraint" % (programPointStr, succe.upper))
            
            for vertexID1, vertexID2 in pathg.mutualInclusionPairs():
                v1 = pathg.getVertex(vertexID1)
                v2 = pathg.getVertex(vertexID2)
                programPoint1 = v1.getProgramPoint()
                if isinstance(programPoint1, tuple):
                    programPoint1Str = "__count_%d_%d" % (programPoint1[0], programPoint1[1])
                else:
                    programPoint1Str = "__count_%d" % programPoint1
                programPoint2 = v2.getProgramPoint()
                if isinstance(programPoint2, tuple):
                    programPoint2Str = "__count_%d_%d" % (programPoint2[0], programPoint2[1])
                else:
                    programPoint2Str = "__count_%d" % programPoint2
                print("assert(%s > 0 ==> %s > 0); // Mutual inclusion" % (programPoint1Str, programPoint2Str))
                print("assert(%s > 0 ==> %s > 0); // Mutual inclusion" % (programPoint2Str, programPoint1Str))
            for vertexID1, vertexID2 in pathg.mutualExclusionPairs():
                v1 = pathg.getVertex(vertexID1)
                v2 = pathg.getVertex(vertexID2)
                programPoint1 = v1.getProgramPoint()
                if isinstance(programPoint1, tuple):
                    programPoint1Str = "__count_%d_%d" % (programPoint1[0], programPoint1[1])
                else:
                    programPoint1Str = "__count_%d" % programPoint1
                programPoint2 = v2.getProgramPoint()
                if isinstance(programPoint2, tuple):
                    programPoint2Str = "__count_%d_%d" % (programPoint2[0], programPoint2[1])
                else:
                    programPoint2Str = "__count_%d" % programPoint2
                print("assert(%s > 0 ==> %s == 0); // Mutual exclusion" % (programPoint1Str, programPoint2Str))
                print("assert(%s > 0 ==> %s == 0); // Mutual exclusion" % (programPoint2Str, programPoint1Str))
            for vertexID1, vertexID2 in pathg.executionDependencies():
                v1 = pathg.getVertex(vertexID1)
                v2 = pathg.getVertex(vertexID2)
                programPoint1 = v1.getProgramPoint()
                if isinstance(programPoint1, tuple):
                    programPoint1Str = "__count_%d_%d" % (programPoint1[0], programPoint1[1])
                else:
                    programPoint1Str = "__count_%d" % programPoint1
                programPoint2 = v2.getProgramPoint()
                if isinstance(programPoint2, tuple):
                    programPoint2Str = "__count_%d_%d" % (programPoint2[0], programPoint2[1])
                else:
                    programPoint2Str = "__count_%d" % programPoint2
                print("assert(%s > 0 ==> %s > 0); // Execution dependence" % (programPoint1Str, programPoint2Str))
            print "#endif"
            
class Parsetraces (TraceInformation):
    def __init__ (self, basename, tracefile, program):
        TraceInformation.__init__(self, program)
        self.__initialise()
        self.__parse(tracefile)
        self._end()
        self._outputConjectures()      
        self.__assignRandomWCETs()
        
    def __assignRandomWCETs (self):
        for cfg in self._program.getcfgs():
            functionName = cfg.getName()
            for v in cfg:
                self._executionTimes[(functionName, v.getOriginalVertexID())] = random.randint(1,100)

    def __initialise (self):
        self.__currentContextv = None
        self.__currentCFG      = None
        self.__currentLNT      = None
        self.__predBB          = None
        self.__currentBB       = None
        self.__currentHeaderID = None
        self.__currentPathg    = None
        self.__stack           = []
        self.__contextg        = self._program.getContextGraph()
        rootv                  = self.__contextg.getVertex(self.__contextg.getRootID())
        self.__rootCFG         = self._program.getCFG(rootv.getName())
        self.__entryToCFG      = {}        
        for cfg in self._program.getcfgs():
            self.__entryToCFG[cfg.getEntryID()] = cfg
    
    def __reset (self):
        self.__currentContextv = self.__contextg.getVertex(self.__contextg.getRootID())
        self.__currentCFG      = self._program.getCFG(self.__currentContextv.getName())
        self.__currentLNT      = self._program.getLNT(self.__currentContextv.getName())
        self.__currentPathg    = self._program.getPathInfoGraph(self.__currentContextv.getName())
        self.__predBB          = None
        self.__currentBB       = None
        
    def __parse (self, tracefile):
        runID = 0
        with open(tracefile, 'r') as f:
            for line in f:
                if line.startswith(newTrace):
                    runID += 1
                    debug.debug_message("=====> Run %d" % runID, 1)
                    self._allruns.add(runID)
                    self.__reset()
                elif line.startswith(endTrace):
                    self.__handleReturn()
                else:
                    lexemes = shlex.split(line)
                    for lex in lexemes:
                        nextID = int(lex)
                        if nextID == self.__rootCFG.getEntryID():
                            self.__currentBB = self.__currentCFG.getVertex(nextID)
                        else:
                            found = False
                            for succID in self.__currentBB.getSuccessorIDs():
                                if succID == nextID:
                                    self.__predBB    = self.__currentBB
                                    self.__currentBB = self.__currentCFG.getVertex(succID)
                                    # We have switched basic blocks in the current CFG
                                    self._analyseCFGEdge(self.__currentPathg, self.__currentLNT, self.__predBB.vertexID, self.__currentBB.vertexID)
                                    found = True
                                    break
                            if not found:
                                if self.__currentBB.vertexID == self.__currentCFG.getExitID():
                                    succIDs = self.__currentBB.getSuccessorIDs()
                                    assert len(succIDs) == 1
                                    succv            = self.__currentCFG.getVertex(succIDs[0])
                                    self.__predBB    = self.__currentBB
                                    self.__currentBB = succv
                                    # Since we have switched basic blocks in the current CFG, analyse the super blocks
                                    self._analyseCFGEdge(self.__currentPathg, self.__currentLNT, self.__predBB.vertexID, self.__currentBB.vertexID)             
                                else:
                                    self.__handleCall(nextID)    
                        # We have switched basic blocks in the current CFG
                        self._analyseCFGVertex(self.__currentPathg, self.__currentLNT, self.__currentBB.vertexID)
                            
    def __handleReturn (self):
        debug.debug_message("Returning because of basic block %d" % self.__currentBB.vertexID, 1)
        self._endOfFunction(self.__currentCFG, self.__currentLNT, self.__currentPathg)
        if self.__stack:
            (self.__currentContextv, self.__currentCFG, self.__currentLNT, self.__predBB, self.__currentBB, self.__currentPathg) = self.__stack.pop()
            
    def __handleCall (self, nextID):
        callerFrame = (self.__currentContextv, self.__currentCFG, self.__currentLNT, self.__predBB, self.__currentBB, self.__currentPathg)
        self.__stack.append(callerFrame)
        newContextID           = self.__currentContextv.getSuccessorWithCallSite(self.__currentBB.vertexID)
        self.__currentContextv = self.__contextg.getVertex(newContextID)
        self.__currentCFG      = self.__entryToCFG[nextID]
        self.__currentLNT      = self._program.getLNT(self.__currentCFG.getName())
        self.__currentPathg    = self._program.getPathInfoGraph(self.__currentCFG.getName())
        self.__predBB          = None
        self.__currentBB       = self.__currentCFG.getVertex(self.__currentCFG.getEntryID())
        
class Gem5Parser (TraceInformation):
    def __init__ (self, program, traceFiles):
        debug.verbose_message("Parsing gem5 traces", __name__)
        TraceInformation.__init__(self, program)
        self.__initialise()
        self.__parse(traceFiles)
        self._end()
        self._normaliseData()
        self._outputConjectures()
        self._outputCBMCConjectures()
        
    def __initialise (self):
        self.__currentContextv = None
        self.__currentCFG      = None
        self.__currentLNT      = None
        self.__predBB          = None
        self.__currentBB       = None
        self.__currentHeaderID = None
        self.__currentPathg    = None
        self.__time1           = None
        self.__stack           = []
        self.__contextg        = self._program.getContextGraph()
        rootv                  = self.__contextg.getVertex(self.__contextg.getRootID())
        self.__rootCFG         = self._program.getCFG(rootv.getName())
        self.__firstAddr       = self.__rootCFG.getFirstInstruction().getAddress()
        lastbb                 = self.__rootCFG.getVertex(self.__rootCFG.getExitID())
        for instruction in reversed(lastbb.getInstructions()):
            if instruction.getOp() not in arm.armInstructionSet.Nops:
                self.__lastAddr = instruction.getAddress()
                break
        assert self.__lastAddr, "Unable to find last address"
        debug.debug_message("Start address of root function '%s' is %s" % (rootv.getName(), hex(self.__firstAddr)), 1)    
        debug.debug_message("End address of root function '%s' is %s" % (rootv.getName(), hex(self.__lastAddr)), 1)
        
    def __parse (self, traceFiles):
        runID = 0
        for filename in traceFiles:
            parsing = False 
            with gzip.open(filename, 'r') as f:
                runID += 1
                self._allruns.add(runID)
                debug.debug_message("Analysing gem5 trace file '%s'" % filename, 1)
                for line in f:
                    lexemes  = shlex.split(line)
                    PCLexeme = lexemes[-1]
                    assert len(PCLexeme) == 11, "Unable to parse program counter %s" % PCLexeme
                    try:
                        time     = int(lexemes[0][:-1])
                        PCLexeme = PCLexeme[5:]
                        PC       = int(PCLexeme, 16)
                        if PC == self.__firstAddr:
                            self.__time1           = time
                            startTime              = time
                            parsing                = True
                            self.__currentContextv = self.__contextg.getVertex(self.__contextg.getRootID())
                            self.__currentCFG      = self._program.getCFG(self.__currentContextv.getName())
                            self.__currentLNT      = self._program.getLNT(self.__currentContextv.getName())
                            self.__currentPathg    = self._program.getPathInfoGraph(self.__currentContextv.getName())
                            self.__predBB          = None
                            self.__currentBB       = self.__currentCFG.getVertex(self.__currentCFG.getEntryID())
                            self._analyseCFGVertex(self.__currentPathg, self.__currentLNT, self.__currentBB.vertexID)     
                        if parsing:
                            self.__parseAddress (time, PC, runID)
                        if PC == self.__lastAddr:
                            # Stop parsing
                            parsing = False
                            # Compute the HWMT
                            totalTime = time - startTime
                            self._longestTime = max(self._longestTime, totalTime)
                            # Falsify conjectures
                            self._endOfFunction(self.__currentCFG, self.__currentLNT, self.__currentPathg)
                    except ValueError:
                        debug.exit_message("Cannot cast %s into an integer: it is not a hexadecimal string" % PCLexeme)

    def __getCFGWithAddress (self, address):
        for cfg in self._program.getcfgs():
            firstAddress = cfg.getFirstInstruction().getAddress()
            if firstAddress == address:
                return cfg
        assert False, "Unable to find CFG with start address %s" % hex(address)
    
    def __analyseWCETOfBasicBlock (self, executionTime):
        tupleKey = (self.__currentCFG.getName(), self.__currentBB.getOriginalVertexID())
        assert tupleKey in self._executionTimes
        self._executionTimes[tupleKey] = max(self._executionTimes[tupleKey], executionTime)    
        
    def __parseAddress (self, time, address, runID):
        if address == self.__lastAddr:
            self.__analyseWCETOfBasicBlock(time - self.__time1)
        if not self.__currentBB.hasAddress(address):
            # Instructions in the current basic block have finished. Analyse its execution time
            self.__analyseWCETOfBasicBlock(time - self.__time1)
            # Move the time marker forward to the current time to reflect that we are transitioning
            # to a new basic block
            self.__time1 = time
            # Make the switch to the next basic block
            if self.__currentCFG.isCallSite(self.__currentBB.vertexID):
                self.__handleCall(address)
            elif self.__currentCFG.getExitID() == self.__currentBB.vertexID:
                self.__handleReturn()
                # Since we have switched basic blocks in the current CFG, analyse the super blocks
                self._analyseCFGEdge(self.__currentPathg, self.__currentLNT, self.__predBB.vertexID, self.__currentBB.vertexID) 
            else:
                for succID in self.__currentBB.getSuccessorIDs():
                    succv = self.__currentCFG.getVertex(succID)
                    if succv.hasAddress(address):
                        self.__predBB    = self.__currentBB
                        self.__currentBB = succv
                        break
                # Since we have switched basic blocks in the current CFG, analyse the super blocks
                self._analyseCFGEdge(self.__currentPathg, self.__currentLNT, self.__predBB.vertexID, self.__currentBB.vertexID)     
            debug.debug_message("Now in CFG '%s' at basic block %d" % (self.__currentCFG.getName(), self.__currentBB.vertexID), 10)   
            self._analyseCFGVertex(self.__currentPathg, self.__currentLNT, self.__currentBB.vertexID)     
            
    def __handleReturn (self):
        if self.__currentCFG.getExitID() == self.__currentBB.vertexID and self.__currentCFG != self.__rootCFG:
            # Falsify conjectures
            self._endOfFunction(self.__currentCFG, self.__currentLNT, self.__currentPathg)
            (self.__currentContextv, self.__currentCFG, self.__currentLNT, self.__predBB, self.__currentBB, self.__currentPathg) = self.__stack.pop()
            succIDs = self.__currentBB.getSuccessorIDs()
            assert len(succIDs) == 1
            succv            = self.__currentCFG.getVertex(succIDs[0])
            self.__predBB    = self.__currentBB
            self.__currentBB = succv
    
    def __handleCall (self, address):
        callerFrame = (self.__currentContextv, self.__currentCFG, self.__currentLNT, self.__predBB, self.__currentBB, self.__currentPathg)
        self.__stack.append(callerFrame)
        newContextID           = self.__currentContextv.getSuccessorWithCallSite(self.__currentBB.vertexID)
        self.__currentContextv = self.__contextg.getVertex(newContextID)
        self.__currentCFG      = self.__getCFGWithAddress(address)
        self.__currentLNT      = self._program.getLNT(self.__currentCFG.getName())
        self.__predBB          = None
        self.__currentBB       = self.__currentCFG.getVertex(self.__currentCFG.getEntryID())
        self.__currentPathg    = self._program.getPathInfoGraph(self.__currentCFG.getName())
        assert self.__currentBB.hasAddress(address), "Calling into '%s' because of address %s but basic block does not contain an instruction with that address" % (self.__currentCFG.getName(), hex(address))      
        

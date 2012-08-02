import DirectedGraph, Vertices

# Class to mode instructions inside basic blocks
class Instruction ():    
    def __init__ (self, address, string):
        self.address = address
        self.string = string
        
    def getAddress (self):
        return self.address
    
    def getString (self):
        return self.string
    
    def containsLabel (self):
        return ":" in self.string
    
    def isNop (self):
        return "nop" in self.string
    
    def __str__(self):
        return self.address + " : " + self.string

class BasicBlock (Vertices.Vertex):
    def __init__ (self, vertexID):
        Vertices.Vertex.__init__(self, vertexID)
        self.instructions = {}
    
    def addInstruction (self, instr):
        address = instr.getAddress()
        assert address not in self.instructions, "Basic block " + str(self.vertexID) + " already has instruction with address " + str(address)
        self.instructions[address] = instr
        
    def getFirstInstruction (self):
        return sorted(self.instructions.iteritems())[0]
    
    def getLastInstruction (self):
        return sorted(self.instructions.iteritems())[len(self.instructions) - 1]
    
    def numberOfInstructions (self):
        return len(self.instructions)
    
    def getInstructions (self):
        return sorted(self.instructions.iteritems())
        
    def __str__ (self):
        string = "Vertex ID = " + str(self.vertexID) + "\n"
        string += "\t" + Vertices.Vertex.predecessorStr(self)
        string += "\t" + Vertices.Vertex.successorStr(self)
        string += "\t" + 40 * "=" + "\n"   
        for address, instr in sorted(self.instructions.iteritems()):
            string += "\t" + instr.__str__() + "\n"   
        string += "\t" + 40 * "=" + "\n"      
        return string
        
class CFG (DirectedGraph.DirectedGraph):    
    def __init__ (self):
        DirectedGraph.DirectedGraph.__init__(self)
        self.entryID = DirectedGraph.dummyVertexID
        self.exitID = DirectedGraph.dummyVertexID
        
    def addVertex (self, bbID):
        assert bbID not in self.vertices, "Adding basic block %s which is already in graph" % bbID
        bb = BasicBlock(bbID)
        self.vertices[bbID] = bb
        
    def getVertex (self, bbID):
        return DirectedGraph.DirectedGraph.getVertex(self, bbID)
        
    def setEntryID (self, entryID=None):
        if entryID is None:
            for bb in self.vertices.values():
                if bb.numberOfPredecessors() == 0:
                    bbID = bb.getVertexID()
                    assert self.entryID == DirectedGraph.dummyVertexID, "The entry ID has already been set to %s. Found another entry candidate %s" % (self.entryID, bbID)
                    self.entryID = bbID
            assert self.entryID != DirectedGraph.dummyVertexID, "Unable to find a vertex without predecessors to set as the entry"
        else:
            assert entryID in self.vertices, "Cannot find vertex " + str(entryID) + " in vertices"
            assert entryID > DirectedGraph.dummyVertexID, "Entry ID " + str(entryID) + " is not positive"
            self.entryID = entryID
        
    def setExitID (self, exitID=None):
        if exitID is None:
            for bb in self.vertices.values():
                if bb.numberOfSuccessors() == 0:
                    bbID = bb.getVertexID()
                    assert self.exitID == DirectedGraph.dummyVertexID, "The exit ID has already been set to %s. Found another entry candidate %s" % (self.entryID, bbID)
                    self.exitID = bbID
            assert self.exitID != DirectedGraph.dummyVertexID, "Unable to find a vertex without successors to set as the entry"
        else:
            assert exitID in self.vertices, "Cannot find vertex " + str(exitID) + " in vertices"
            assert exitID > DirectedGraph.dummyVertexID, "Exit ID " + str(exitID) + " is not positive"
            self.exitID = exitID
            
    def addExitEntryEdge (self):
        assert self.entryID != DirectedGraph.dummyVertexID, "Entry ID not set"
        assert self.exitID != DirectedGraph.dummyVertexID, "Exit ID not set"
        entryv = self.getVertex(self.entryID)
        exitv = self.getVertex(self.exitID)
        entryv.addPredecessor(self.exitID)
        exitv.addSuccessor(self.entryID)
        
    def __str__ (self):
        string = "*" * 20 + " CFG Output " + "*" * 20 + "\n" + \
        "Entry ID = %s\n" % str(self.entryID) + \
        "Exit ID  = %s\n" % str(self.exitID) + "\n"
        for bb in self.vertices.values():
            string += bb.__str__()
        return string
    
dummyVertexID = -1

class DirectedGraph ():        
    def __init__ (self):
        self.vertices = {}
        self.__name = None
    
    def setName (self, name):
        self.__name = name
        
    def getName (self):
        return self.__name
    
    def getVertex (self, vertexID):
        assert vertexID in self.vertices, "Vertex " + str(vertexID) + " is not in the graph"
        return self.vertices[vertexID]
    
    def hasVertex (self, vertexID):
        return vertexID in self.vertices
    
    def addEdge (self, predID, succID):
        predv = self.getVertex(predID)
        succv = self.getVertex(succID)
        predv.addSuccessor(succID)
        succv.addPredecessor(predID)
    
    def getNextVertexID (self):
        nextID = 0
        while nextID in self.vertices.keys():
            nextID = nextID + 1 
        return nextID
    
    def numOfVertices (self):
        return len(self.vertices)
    
    def numOfEdges(self):
        total = 0
        for v in self.vertices.values():
            total += v.numberOfSuccessors()
        return total
    
    def __iter__ (self):
        return self.vertices.values().__iter__()
    
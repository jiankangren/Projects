#!/usr/bin/python2.6

from optparse import OptionParser
from sys import argv, maxint, path
from subprocess import Popen, PIPE
from os import environ, sep, rename
from re import split, match
from math import ceil
from matplotlib.font_manager import fontManager, FontProperties
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

# Add the 'src' directory to the module search and PYTHONPATH
path.append(path[0] + sep + "src")
from Debug import Debug
 
# The command-line parser and its options
parser = OptionParser(add_help_option=False)

parser.add_option("-d",
                  "--debug",
                  action="store_true",
                  dest="debug",
                  help="Debug mode.",
                  default=False)

parser.add_option("-h",
                  "--help",
                  action="help",
                  help="Display this help message.")

parser.add_option("-R",
                  "--number-of-runs",
                  action="store",
                  type="int",
                  dest="runs",
                  help="The number of times to re-run the calculation per generated CFG. [Default is %default].",
                  default=10,
                  metavar="<INT>")

parser.add_option("-C",
                  "--cfg-variations",
                  action="store",
                  type="int",
                  dest="variations",
                  help="The number of CFG variants to generate for a fixed size of vertices. [Default is %default].",
                  default=1,
                  metavar="<INT>")

parser.add_option("--max-vertices",
                  action="store",
                  type="int",
                  dest="maxVertices",
                  help="Maximum number of vertices in a CFG. [Default is %default].",
                  default=1000,
                  metavar="<INT>")

parser.add_option("--min-vertices",
                  action="store",
                  type="int",
                  dest="minVertices",
                  help="Minimum number of vertices in a CFG. [Default is %default].",
                  default=10,
                  metavar="<INT>")

parser.add_option("-l",
                  "--loops",
                  action="store_true",
                  dest="loops",
                  help="Inject loops into the generated CFGs.",
                  default=False)

parser.add_option("-v",
                 "--verbose",
                 action="store_true",
                 dest="verbose",
                 help="Be verbose.",
                 default=False)

(opts, args) = parser.parse_args(argv[1:])
debug = Debug(opts.verbose)

# Check that the user has passed the correct options
assert opts.minVertices >= 10, "CFGs with less than 10 vertices not supported"
assert opts.runs >= 1, "The number of runs per CFG must be a positive integer"

# Maps whose key is the num of vertices in the CFG and whose value is either:
# 1) WCET estimate
# 2) #constraints in ILP
# 3) #variables in ILP
# 4) ILP solving time.
# These maps are defined for the ILP generated for the CFG and from the Super-Block CFG
wcetData         = {}
constraintData   = {}
variablesData    = {}
solvingTimeData  = {}
wcetData2        = {}
constraintData2  = {}
variablesData2   = {}
solvingTimeData2 = {}

def initialise ():
	for numOfVertices in range(opts.minVertices, opts.maxVertices + 1):
		wcetData[numOfVertices]         = 0		
		constraintData[numOfVertices]   = 0
		variablesData[numOfVertices]    = 0
		solvingTimeData[numOfVertices]  = 0
		wcetData2[numOfVertices]        = 0
		constraintData2[numOfVertices]  = 0
		variablesData2[numOfVertices]   = 0
		solvingTimeData2[numOfVertices] = 0

def parseMeasurements (numOfVertices, line, firstLine):
	wcetCol        = 1
	constraintsCol = 2
	variablesCol   = 3
	solvingTimeCol = 4

	tokens = split("\s+", line)
	colNum = 1
	for lexeme in tokens[1:-1]:
		value = lexeme[1:].strip()
		if colNum == wcetCol:
			if firstLine:
				wcetData[numOfVertices] += int(value)
			else:
				wcetData2[numOfVertices] += int(value)
		if colNum == constraintsCol:
			if firstLine:
				constraintData[numOfVertices] += int(value)
			else:
				constraintData2[numOfVertices] += int(value)
		if colNum == variablesCol:
			if firstLine:
				variablesData[numOfVertices] += int(value)
			else:
				variablesData2[numOfVertices] += int(value)
		if colNum == solvingTimeCol:
			if firstLine:
				solvingTimeData[numOfVertices] += int(value)
			else:
				solvingTimeData2[numOfVertices] += int(value)
		colNum += 1
			
def run ():
	# These environment variables are needed to compile and disassemble the program under analysis 
	WCET_HOME = "WCET_HOME"
	for var in [WCET_HOME]:
    		try:
        		environ[var]
    		except KeyError:
       		 	debug.exitMessage ("Cannot find environment variable '" + var + "' which is needed to run the simulation.")

	javaPrefix = "java -ea -jar "
	for numOfVertices in range(opts.minVertices, opts.maxVertices + 1):
		for variations in range(1, opts.variations + 1):
			debug.verboseMessage("Now generating CFG of size " + str(numOfVertices))
			cmd1 = javaPrefix + environ[WCET_HOME] + sep + "bin" + sep + "program-generator.jar -s 1 -V " + str(numOfVertices)

			proc1 = Popen(cmd1, shell=True, executable="/bin/bash", stderr=PIPE, stdout=PIPE)
			stdoutdata, stderrdata = proc1.communicate()
			if proc1.returncode:
				debug.exitMessage("Problem running " + cmd1)

			oldProgramFileName = "program.xml"
			newProgramFileName = "program" + str(numOfVertices) + ".xml"
			rename(oldProgramFileName,newProgramFileName)

			for run in range(1, opts.runs + 1):
				debug.verboseMessage("Run #" + str(run))
				cmd2Options = " -p" + newProgramFileName + " -T"
			    	cmd2 = javaPrefix + environ[WCET_HOME] + sep + "bin" + sep + "program-analyser.jar" + cmd2Options
				proc2 = Popen(cmd2, shell=True, executable="/bin/bash", stderr=PIPE, stdout=PIPE)
				stdoutdata, stderrdata = proc2.communicate()
				if proc2.returncode != 0:
					debug.exitMessage("Problem running " + cmd2)

				firstLine = True
				for line in stdoutdata.splitlines():
					if line.startswith("|F"):
						parseMeasurements (numOfVertices, line, firstLine)
						if firstLine:
							firstLine = False

def generateGraph (fileName, yLabel, xAxis, curve1, curve2):
	figConstraints = plt.figure()
	ax = figConstraints.add_subplot(111)
	ax.grid(False)
	ax.plot(xAxis, curve1, markersize=11, marker='^', color='blue', label='CFG')
	ax.plot(xAxis, curve2, markersize=11, marker='+', color='red', label='SB-CFG')
	ax.set_xlim(10)
	ax.set_xticks(xAxis)
	ax.set_ylabel(yLabel, fontsize=12, fontweight='bold')
	ax.set_xlabel("#Vertices in CFG", fontsize=12, fontweight='bold')
	# Make the X-axis and Y-axis ticks thicker
	for tick in ax.xaxis.get_major_ticks():
    		tick.label1.set_fontsize(10)
  		tick.label1.set_fontweight('bold')
	for tick in ax.yaxis.get_major_ticks():
  	  	tick.label1.set_fontsize(10)
   	 	tick.label1.set_fontweight('bold')
	plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,ncol=2, mode="expand", borderaxespad=0.)
	plt.savefig(fileName)

def showResults ():
	xAxis                 = []
	cfgConstraintsCurve   = []
	sbcfgConstraintsCurve = []
	cfgVariablesCurve     = []
	sbcfgVariablesCurve   = []
	cfgTimeCurve          = []
	sbcfgTimeCurve        = []

	# Collate the data
	for numOfVertices in wcetData:
		xAxis.append(numOfVertices)
		print("#Vertices " + str(numOfVertices))
		print("WCET " + str(wcetData[numOfVertices]) + " " +  str(wcetData2[numOfVertices]))

		cfgConstraints   = ceil(constraintData[numOfVertices]/(opts.runs*opts.variations))
		sbcfgConstraints = ceil(constraintData2[numOfVertices]/(opts.runs*opts.variations))
		print("Constraints " + str(cfgConstraints) + " " + str(sbcfgConstraints))
		cfgConstraintsCurve.append(cfgConstraints)
		sbcfgConstraintsCurve.append(sbcfgConstraints)

		cfgVariables  = ceil(variablesData[numOfVertices]/(opts.runs*opts.variations))
		sbcfgVariables = ceil(variablesData2[numOfVertices]/(opts.runs*opts.variations))
		print("Variables " + str(cfgVariables) + " " + str(sbcfgVariables))
		cfgVariablesCurve.append(cfgVariables)
		sbcfgVariablesCurve.append(sbcfgVariables)

		cfgSolveTime   = ceil(solvingTimeData[numOfVertices]/(opts.runs*opts.variations))
		sbcfgSolveTime = ceil(solvingTimeData2[numOfVertices]/(opts.runs*opts.variations))
		print("Solving time " + str(cfgSolveTime) + " " + str(sbcfgSolveTime))
		cfgTimeCurve.append(cfgSolveTime)
		sbcfgTimeCurve.append(sbcfgSolveTime)

	# Generate the graphs
	generateGraph("constraints.png", "#Constraints", xAxis, cfgConstraintsCurve, sbcfgConstraintsCurve)
	generateGraph("variables.png", "#Variables", xAxis, cfgVariablesCurve, sbcfgVariablesCurve)
	generateGraph("solvingTime.png", "ILP Solving Time", xAxis, cfgTimeCurve, sbcfgTimeCurve)
		
if __name__ == "__main__":
	initialise ()
	run ()
	showResults ()

package adam.betts.simplescalar;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.util.HashMap;
import java.util.Stack;

import adam.betts.graphs.ControlFlowGraph;
import adam.betts.graphs.IpointGraph;
import adam.betts.programs.Program;
import adam.betts.programs.Subprogram;
import adam.betts.tools.MainSimpleScalarTraceParser;
import adam.betts.utilities.Debug;
import adam.betts.utilities.Globals;
import adam.betts.utilities.Enums.IProfile;

public class TraceParser
{
	protected Program program;

	/*
	 * Cycle time
	 */
	protected long time = 0;

	/*
	 * Stack and Hashmap needed to return to previous locations of CFGs between
	 * calls
	 */
	Stack<Integer> callStack = new Stack<Integer> ();
	HashMap<Integer, Integer> previousBB = new HashMap<Integer, Integer> ();

	/*
	 * The id given by SimpleScalar to an instruction as it enters the pipeline.
	 * The String records the address (in hex) of the instruction
	 */
	protected HashMap<Integer, String> idToString = new HashMap<Integer, String> ();

	public TraceParser (Program program)
	{
		this.program = program;

		String traceFileName = Globals.getTraceFileName ();
		try
		{
			RandomAccessFile raf = new RandomAccessFile (traceFileName, "r");
			String line = raf.readLine ();

			/*
			 * Make sure the trace file passes a sanity check before processing
			 */
			if (line.startsWith ("@"))
			{
				TraceOutput.openFileHandles ();
				parseRawTrace ();
				TraceOutput.closeFileHandles ();
			}
			else
			{
				throw new IOException (
						traceFileName
								+ " is not a valid SimpleScalar trace file (generated by pipeview)");
			}
		}
		catch (IOException e)
		{
			System.err.println (e.getMessage ());
			System.exit (1);
		}
	}

	private void parseRawTrace ()
	{
		/*
		 * New cycle indicator
		 */
		final char newCycle = '@';

		/*
		 * These symbols are used in the trace to indicate progress of an
		 * instruction through the pipeline
		 */
		final char added = '+';
		final char retire = '-';
		final char progress = '*';

		/*
		 * Positions of strings of interest in the tokenized string
		 */
		final int idIndex = 1;
		final int addressIndex = 2;
		final int stageIndex = 2;
		final int instrIndex = 4;

		try
		{
			BufferedReader in = new BufferedReader (new FileReader (Globals
					.getTraceFileName ()));
			String str;

			while ( (str = in.readLine ()) != null)
			{
				char c = str.charAt (0);

				if (c == newCycle)
				{
					if (str.charAt (1) == ' ')
					{
						time = Long.parseLong (str.substring (2));
					}
					else
					{
						time = Long.parseLong (str.substring (1));
					}
					Debug.debugMessage (getClass (), "Cycle " + time, 3);
				}
				else
				{
					String[] lexemes = str.split ("\\s+");

					if (c == added)
					{
						if (!lexemes[instrIndex].contains ("agen")
								&& !lexemes[instrIndex].contains ("ldp"))
						{
							int id = Integer.parseInt (lexemes[idIndex]);
							idToString.put (id, lexemes[addressIndex]);

							Debug.debugMessage (getClass (),
									"New instruction with id " + id
											+ " @ address "
											+ lexemes[addressIndex]
											+ " entering pipeline", 4);

							/*
							 * Only output to the trace file when a new
							 * instruction is fetched in the pipeline. This must
							 * be changed to handle speculative execution
							 */
							decideAction (id);
						}
					}
					else if (c == progress)
					{
						int id = Integer.parseInt (lexemes[idIndex]);
						String stage = lexemes[stageIndex];
						Debug.debugMessage (getClass (), id
								+ " entering stage " + stage, 4);
					}
					else if (c == retire)
					{
						int id = Integer.parseInt (lexemes[idIndex]);
						Debug.debugMessage (getClass (), id
								+ " is leaving the pipeline ", 4);
						idToString.remove (id);
					}
				}
			}
			in.close ();
		}
		catch (Exception e)
		{
			System.err.println ("Error: " + e.getMessage ());
			System.exit (1);
		}
	}

	private void decideAction (int id) throws IOException
	{
		String hexAddress = idToString.get (id);
		long address = Long.parseLong (hexAddress.substring (2), 16);

		Subprogram subprogram = program.getSubprogram (address);
		if (subprogram != null)
		{
			ControlFlowGraph cfg = subprogram.getCFG ();

			Debug.debugMessage (getClass (), "In subprogram "
					+ subprogram.getSubprogramName (), 3);

			/*
			 * The call stack maintains the exact sequence of subprograms
			 * called. Thus the last element on the stack is the current
			 * subprogram
			 */
			if (callStack.isEmpty ())
			{
				Debug.debugMessage (getClass (), "Entering "
						+ subprogram.getSubprogramName (), 1);
				callStack.push (subprogram.getSubprogramID ());
			}
			else if (callStack.peek () != subprogram.getSubprogramID ())
			{
				Debug.debugMessage (getClass (), "Calling "
						+ subprogram.getSubprogramName (), 1);
				callStack.push (subprogram.getSubprogramID ());
			}

			for (IProfile iprofile: Globals.getInstrumentationProfiles ())
			{
				Debug.debugMessage (getClass (), iprofile.toString (), 1);
				IpointGraph ipg = subprogram.getIPG (iprofile);

				if (ipg.hasIpointID (address))
				{
					Debug.debugMessage (getClass (), "Ipoint " + address
							+ " found", 4);
					if (MainSimpleScalarTraceParser.Globals
							.outputHexAddresses ())
					{
						TraceOutput.writeTuple (iprofile, hexAddress, time);
					}
					else
					{
						TraceOutput.writeTuple (iprofile, address, time);
					}
				}

			}

			if (cfg.getLastAddress () == address)
			{
				Debug.debugMessage (getClass (), "Returning from "
						+ subprogram.getSubprogramName (), 1);
				int subprogramID = callStack.pop ();
				previousBB.remove (subprogramID);
			}
		}
	}
}
package adam.betts.tools;

import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.CommandLineParser;
import org.apache.commons.cli.GnuParser;
import org.apache.commons.cli.HelpFormatter;
import org.apache.commons.cli.Options;
import org.apache.commons.cli.ParseException;

import adam.betts.programs.Program;
import adam.betts.programs.ProgramReader;
import adam.betts.utilities.DefaultOptions;

public class MainPathExpressionAnalyser
{

    private static Options options;

    private static String programFileName;

    private static void addOptions ()
    {
        options = new Options();
        DefaultOptions.addDefaultOptions(options);
        DefaultOptions.addProgramOption(options);
        DefaultOptions.addRootOption(options, false);
        DefaultOptions.addUDrawDirectoryOption(options);
        DefaultOptions.addInstrumentationProfileOption(options, true, 1);
    }

    private static void parseCommandLine (String[] args)
    {
        final String toolName = "path-expression.jar";
        CommandLineParser parser = new GnuParser();
        HelpFormatter formatter = new HelpFormatter();
        formatter.setWidth(128);
        CommandLine line = null;
        try
        {
            line = parser.parse(options, args);

            if (line.hasOption(DefaultOptions.helpOption.getOpt()))
            {
                formatter.printHelp(toolName, options);
                System.exit(1);
            }
            else
            {
                DefaultOptions.setDefaultOptions(line);
                DefaultOptions.setRootOption(line);
                DefaultOptions.setUDrawDirectoryOption(line);
                DefaultOptions.setInstrumentationProfileOption(line);

                programFileName = line
                        .getOptionValue(DefaultOptions.programFileOption
                                .getOpt());
            }
        }
        catch (ParseException e)
        {
            System.out.println(e.getMessage());
            formatter.printHelp(toolName, options);
            System.exit(1);
        }
    }

    private static void run ()
    {
        Program program = new Program();
        new ProgramReader(program, programFileName, true);
        program.insertVirtualIpoints();
        program.buildPathExpressions ();
    }

    public static void main (String[] args)
    {
        addOptions();
        parseCommandLine(args);
        run();
    }
}
#!/usr/bin/env groovy

@Grab(group = "com.google.guava", module = "guava", version ="13.0.1")

import com.google.common.base.Preconditions
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture
import com.google.common.util.concurrent.ListeningExecutorService
import com.google.common.util.concurrent.MoreExecutors
import com.sun.tools.javac.resources.version

import java.util.concurrent.Callable
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.Future

def cli = new CliBuilder(
    usage: "call another script with specified number of threads simultaneously. Ctrl + C will kill all threads.")

cli.h(longOpt: 'help', 'print help')
cli.n(longOpt: 'number', args: 1, required: true, 'number of threads')
cli.s(longOpt: 'script', args: 1, required: true, 'script to be executed plus all arguments')
cli.v(longOpt: 'verbose', 'whether to print script output to console')

def options = cli.parse(args)

if (!options) {
    cli.usage()
}
def n = options.n
int numOfThreads = Integer.parseInt(n)
Preconditions.checkArgument(numOfThreads > 0, "number of threads must be greater than 0")

String script = options.s
String[] scriptAndArgs = script.split(/\s/)
File scriptFile = new File(scriptAndArgs[0])
String[] scriptArgs = Arrays.copyOfRange(scriptAndArgs, 1, scriptAndArgs.size())

Preconditions.checkArgument(scriptFile.exists(), "script does not exist at %s", scriptFile.absolutePath)
Preconditions.checkArgument(scriptFile.canExecute(), "script %s is not executable", scriptFile.name)

def verbose = options.v

def printIfVerbose = {
    if (verbose) {
        println it;
    }
}

printIfVerbose("will execute $scriptFile with $numOfThreads threads simultaneously")

if (numOfThreads > 5) {
    println "WARNING: if you fire up this script and target your local machine, it may kill your machine!"
    def answer = System.console().
        readLine('Are you sure you want to fire up these many threads? (y/n)')
    if (answer && !answer =~ /(?i)y|yes/) {
        println "quit"
        System.exit(0)
    }
}

def callable = new Callable<Integer>() {

    @Override
    Integer call() throws Exception {
        run(scriptFile, scriptArgs)
        println "done"
        0
    }
}

List<Callable<Integer>> callables = Collections.nCopies(numOfThreads, callable)
ExecutorService service = Executors.newFixedThreadPool(numOfThreads)

service.invokeAll(callables)
System.exit(0)











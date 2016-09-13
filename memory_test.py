import os, sys, getopt

def main( argv ):
  interval = '600'
  process = ""
  debug = 0
  count = 5
  threshold_multiplier = "1.3"
  start_value = ""

  # Debug messages
  def debug_out( message ):
    if debug == 1:
      print(message)

  # Print help
  def help_me():
    print("\nmemory_test.py [-h -v -i <interval> -o <processid> -c <count> -t <threshold>]")
    print("Defaults are in brackets, eg [5]")
    print("All arguments are optional\n")
    print("-h                          Print this help")
    print("-v                          Verbose output")
    print("-i, --interval <interval>   Delay between samples (seconds) [600]")
    print("-p, --processid <id>        ID of Zanata server process, eg. 123456")
    print("-c, --count <num>           Number of samples to record [5]")
    print("-t, --threshold <float>     Max memory increase (multiplied) before failure [1.3]")
    sys.exit(2)

  # Parse arguments
  try:
    opts, args = getopt.getopt(argv,"hvi:p:c:t:s:",["interval=","processid=","count=","threshold_multiplier=","startmem="])
  except getopt.GetoptError as err:
    print ("\nError: "+str(err))
    help_me()

  for opt, arg in opts:
    if opt == "-h":
      help_me()
    elif opt == "-v":
      debug = 1
    elif opt in ("-i", "--interval"):
      interval = arg
    elif opt in ("-p", "--processid"):
      process = arg
    elif opt in ("-c","--count"):
      count = arg
    elif opt in ("-t","--threshold"):
      threshold_multiplier = float(arg)
    elif opt in ("-s", "--startmem"):
      start_value = arg      

  debug_out("Verbose mode enabled")
  debug_out("Interval is "+interval+" seconds")
  debug_out("Count is "+str(count)+" iterations")
  debug_out("Threshold Multiplier is "+str(threshold_multiplier))

  # Determine ProcessID
  if len(process) > 0:
    pass
  else:
    pids = []
    a = os.popen("pgrep -f \"org.jboss.as.standalone\"").read().splitlines()
    if len(a) == 0:
      print("Process not found, run Zanata server first!")
      exit(1)
    process = a[0]

  debug_out("Process ID is "+process)
  try:
    os.kill(int(process), 0)
  except:
    print("Error: Could not find running process with ID "+process)
    exit(1)

  # Get immediate initial sample
  commandhead = "pidstat -p "+process+" -r "
  commandtail = " 1 | grep java | grep -v Average | awk '{print $6}'"
  command = commandhead+"1"+commandtail

  if len(start_value) > 0:
    debug_out("Secret option startmem used")
  else:
    debug_out(("Executing "+command))
    start_value = os.popen(command).read().splitlines()[0]
  print("Starting memory usage is: "+start_value)
  old_value = start_value

  # Update to include interval
  command = commandhead+interval+commandtail

  # Set threshold
  threshold = int(float(start_value)*float(threshold_multiplier))
  debug_out("Threshold is "+str(threshold))
  exit_code = 0

  # Test sampling loop
  for iteration in range(1,int(count)+1):
    new_value = os.popen(command).read().splitlines()[0]
    print(str(iteration)+". Sample: "+new_value)

    if int(new_value) >= threshold:
      print("Error: Memory increased beyond acceptable threshold ("+str(threshold)+") to "+new_value)
      old_value = new_value
      debug_out("Updated stored latest to "+old_value)
      exit_code = 1
      debug_out("Set exit code to "+str(exit_code))
    elif int(new_value) > int(old_value):
      print("Warning: Memory usage increased ("+new_value+" greater than "+start_value+")")
      old_value = new_value
      debug_out("Updated stored latest to "+old_value)
    else:
      pass

  # And we're done.
  debug_out("Exiting with code "+str(exit_code))
  sys.exit(exit_code)

if __name__ == "__main__":
   main(sys.argv[1:])

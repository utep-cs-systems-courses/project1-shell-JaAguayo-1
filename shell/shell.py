#! /usr/bin/env python3

import os, sys, re

def run_process(args):
    try:
        if '>' in args:
            os.close(1) #close file descriptor 1 since it is the output
            os.open(args[-1], os.O_CREAT | os.O_WRONLY) #open a file to write to
            os.set_inheritable(1,True)
            args = args[0:args.index(">")] #get the command

        if '<' in args:
            os.close(0) #close file descriptor 0 since it is the input
            os.open(args[-1], os.O_RDONLY) #open read only file to get input
            os.set_inheritable(0,True)
            args = args[0:args.index("<")] #get the command

    except IndexError:
        os.write(2, "Invalid input for redirection\n".encode())
    try:
        if args[0][0] == '/': #handle path names to execute
            os.execve(args[0],args,os.environ)
    except FileNotFoundError: #in case the file path doesnt exit
        pass
    except IndexError:
        sys.exit(1)
    except Exception:
        sys.exit(1)

    for dir in re.split(":",os.environ['PATH']): #exec the command
        program = "%s/%s" % (dir, args[0])
        try:
            os.execve(program,args,os.environ)
        except FileNotFoundError:
            pass
        except Exception:
            pass
            sys.exit(1)
    os.write(2, ("%s: Command not found\n" % args[0]).encode)
    sys.exit(1)

def pipe(args):
    wrCommand = args[0:args.index("|")] #get the write command
    rdCommand = args[args.index("|")+1:] #get the read command
    pr,pw = os.pipe() #pipe returns a read and write file descriptor
    rc = os.fork()
    if rc < 0:
        os.write(2, ("Fork Failed").encode())
        sys.exit(1)
    elif rc == 0:
        os.close(1) #close file descriptor 1 to set it to the pipe
        os.dup2(pw,1) #dup2 to pick the file descriptor to use
        for fd in (pr,pw):
            os.close(fd) #close output/input fds
        run_process(wrCommand) #run the write command
        os.write(2, ("Could not exec %s\n" % wrCommand[0]).encode())
        sys.exit(1)
    else:
        os.close(0) #close file descriptor 0 to set it to the pipe
        os.dup2(pr,0) #dup2 to pick the file descriptor to use
        for fd in (pw,pr):
            os.close(fd) #close output/input fds
        if "|" in rdCommand: #if the second arg is a "|" then it is a double pipe
            pipe(rdCommand) #call it again to make another pipe
        run_process(rdCommand) #if not exec the read command
        os.write(2, ("Could not exec %s\n" % wrCommand[0]).encode())
        sys.exit(1)

def command_handler(args):
    if len(args) == 0:
        return

    if args[0].lower() == 'exit': #exit command
        os.write(2, ("Exiting shell...\n").encode())
        sys.exit(1)
        
    if args[0] == 'cd':
        try:
            os.chdir(args[1]) #change directory command with whatever is after cd
        except FileNotFoundError:
            os.write(2,("Directory %s not found\n" % args[1]).encode())
        except IndexError:
            os.write(2, ("Must write a directory to swap to\n").encode())
            
    elif "|" in args:
        rc = os.fork()

        if rc < 0:
            os.write(2,("Forked Failed").encode())
            sys.exit(1)
            
        if rc == 0:
            pipe(args)
            
        else:    
            if args[-1] != "&":
                val = os.wait() #os.wait returns childs PID and exit status
                if val[1] != 0: #if the exit code isnt returned correctly
                    os.write(2, ("Program terminated with exit code: %d\n" % val[1]).encode())
    else:
        rc = os.fork()

        prog_wait = True #set a flag for wait, default wait

        if '&' in args:
            prog_wait = False #if there is a "&" it will set the the flag to False
            args.remove("&")

        if rc < 0:
            os.write(2,("Forked Failed").encode())
            sys.exit(1)

        elif rc == 0:
            run_process(args) #exec command

        else:
            if prog_wait: #if wait flag is true run os.wait()
                val = os.wait() #os.wait returns childs PID and exit status
                if val[1] != 0: #if the exit code isnt returned correctly
                    os.write(2, ("Program terminated with exit code: %d\n" % val[1]).encode())

while True:
    prompt = "$ " #default prompt if PS1 isnt valid
    if 'PS1' in os.environ: #check if PS1 is set in the environment to use as prompt
        prompt = os.environ['PS1']

    try:
        os.write(1, prompt.encode()) #prints the prompt
        args = os.read(0,10000) #reads input from keyboard

        if len(args) == 0: 
            break
        
        args = args.decode().split("\n") #split the args by newlines 

        if not args: #if nothing is entered just redisplays the prompt
            continue

        for arg in args:
            command_handler(arg.split()) #send split args to commnd_handler
             
    except EOFError:
        sys.exit(1)

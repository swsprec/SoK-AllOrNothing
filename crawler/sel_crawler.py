#!/usr/bin/python3
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.remote.command import Command
from tranco import Tranco
import crawlerlib
import socket
import http.client as http_client
import argparse
import sys
import time
import random
import yaml
import string
import linecache
import os
import subprocess, signal
import json
from datetime import datetime
import math


def parse_cmd():
    desc = "Selenium based crawler, using custom FF build"
    epi = "created by swsprec"
    parser = argparse.ArgumentParser(description=desc, epilog=epi, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-o', '--output', required=True,
                        help="File for FF log", dest='logFile')

    parser.add_argument('-b', '--binpath', required=True, 
                        help="Absolute path to FOLDER with obj build",
                        dest="path")

    parser.add_argument('-g', '--globals', help=("yml file with globals, has "
                                            "defaults in file already, can be "
                                            "overwritten with yml file"), 
                        dest="globalYMLin", default="globals.yml")

    parser.add_argument('-x', '--blacklist', help=("blacklist file with domains"
                                                "to not crawl, comments are #"),
                        dest="blacklistFile")

    parser.add_argument('-n', '--number', type=int,
                        help="# random sites of Tranco to crawl", dest="num")
    
    parser.add_argument('-m', '--mode', type=str,choices=["TOP","STUDY","RAND"],
                        help=("supported modes: \n"
                        "TOP: top #NUM of tranco sites\n"
                        "STUDY: study breakdown with #NUM of tranco sites\n"
                        "RAND: random #NUM of tranco sites"), dest="mode")

    parser.add_argument('-p', '--profile', required=True,
                        help="Absolute path to profile folder", dest="profile")

    parser.add_argument('-t', '--test', 
                        help="test url or file with urls to run on", dest='testOpen')
    
    args = parser.parse_args()
    test = False 
    if args.testOpen is None:
        if not args.num or not args.mode:
            parser.error("if not a test run, you must supply number of tranco sites and run mode")
    else:
        test = True
    return test, args 


def print_exception(ID):
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    pstring = 'EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)
    crawlerlib.printDEBUG(ID, pstring, error=True)
    return pstring


'''
Getting globals from config file
'''
def get_globals(ID, ymlIn):
    try:
        with open(ymlIn, "r") as fin:
            globalsIn = yaml.load(fin, Loader=yaml.FullLoader)
            return globalsIn
    except Exception as err:
        crawlerlib.printDEBUG(ID, "Error reading in YML global file: %s" % err, level=0)
        sys.exit(1)

'''
Getting tranco list to use for crawl
'''
def logTranco(ID, tranco):
    x = ID.split("-")
    runSeed = x[0]
    with open("./%s/TrancoRanking.txt" % runSeed, "w") as fout:
        for site in tranco:
            print(site, file=fout)


def get_sites(ID, number):
    crawlerlib.printDEBUG(ID, "getting tranco list...", level=0)
    tranc = Tranco(cache=True, cache_dir='.tranco')
    latest_list = tranc.list()
    logTranco(ID, latest_list.top())
    return latest_list.top(number)

def get_random_sites(ID, number):
    crawlerlib.printDEBUG(ID, "getting random traco list sites...", level=0)
    tranc = Tranco(cache=True, cache_dir='.tranco')
    latest_list = tranc.list()
    sites = latest_list.top()
    logTranco(ID, sites)
    return random.choices(sites, k=number)


def get_study_sites(ID, number):
    # 30% is all top
    # 30% from end of ^ to 100K
    # 40% from 100K to 1M
    crawlerlib.printDEBUG(ID, "getting sites for study...", level=0)
    tranc = Tranco(cache=True, cache_dir='.tranco')
    latest_list = tranc.list()
    sites = latest_list.top()
    logTranco(ID, sites)
    num_top = round(number * .3)
    num_bottom = number - (2 * num_top)
    retList = []
    retList += sites[:num_top]
    retList += random.choices(sites[num_top:100000], k=num_top)
    retList += random.choices(sites[100000:len(sites)], k=num_bottom)
    #TODO: uncomment next code line to ret random scan ordering for ALL links 
    # Otherwise, the order for the top 30% will always be the same
    random.shuffle(retList)
    return retList

def get_driver(ID, logFile, path, profile):
    x = ID.split("-")
    runSeed = x[0]
    procID = x[1]
    real_pid = str(os.getpid())
    #logFileGecko = "./" + runSeed + "/" + ID + "-Gecko-" + logFile
    #logFile = "./" + runSeed + "/" + ID + "-" + logFile
    logFileGecko = "./" + runSeed + "/data/" + real_pid + "-Gecko-" + logFile
    logFile = "./" + runSeed + "/data/" + real_pid + "-Binary-" + logFile

    '''
    Creating FF options:
    headless: True
    '''
    #########################
    crawlerlib.printDEBUG(ID, "setting options...", level=0)
    options = Options()
    options.headless = True
    #########################
    
    '''
    Creating FF binary obj
    This is so we can use our custom FF patch with Selenium
    TODO: seems the logfile doesn't do anything when added here
    '''
    ##########################
    crawlerlib.printDEBUG(ID, "creating binary object...", level=0)
    #binary = FirefoxBinary(firefox_path="/home/seclab/Documents/research/DataEx/firefox/obj-x86_64-pc-linux-gnu/dist/bin/firefox", 
    binary = FirefoxBinary(firefox_path="%s/dist/bin/firefox" % path, 
                            log_file=logFile)
    ###########################
    
    '''
    TODO: figure out if this is necessary
    this was the profile when running ./mach run <url>
    '''
    ###########################
    crawlerlib.printDEBUG(ID, "creating firefox profile...", level=0)
    #fp = webdriver.FirefoxProfile("/home/seclab/Documents/research/DataEx/firefox/obj-x86_64-pc-linux-gnu/tmp/profile-default")
    fp = webdriver.FirefoxProfile(profile)
    ###########################
    
    
    '''
    Provisioning webdriver
    '''
    ##########################
    crawlerlib.printDEBUG(ID, "attempting to provision driver...", level=0)
    driver = webdriver.Firefox(firefox_binary=binary, 
                                firefox_profile=fp, options=options, 
                                service_log_path=logFileGecko)
    driver.set_page_load_timeout(_PAGE_LOAD_TIME)
    ##########################
    return driver


def get_run_seed():
    return ''.join(random.choices(string.ascii_uppercase + string.digits + string.ascii_lowercase, k=6)) 
    


from multiprocessing import Process, Queue, Lock, cpu_count, Event
import queue
#from pudb.remote import set_trace

def process_function(runID, procID, sites_to_crawl, blacklist, args,  ResetBool, PauseCV, checkinQueue, resetRequest):
    #set_trace(term_size=(200,200))
    try:
        ID = runID + "-" + procID

        # Wait in case was spawned during a pause
        PauseCV.wait()
        
        #TODO: has thrown a selenium.common.exceptions.TimeoutException ...
        try:
            driver = get_driver(ID, args.logFile, args.path, args.profile)
        except KeyboardInterrupt:
            return 1
        except:
            resetRequest.request()
            driver = get_driver(ID, args.logFile, args.path, args.profile)

        # TODO: this logic fails when multi-threaded (will only make sure each
        # process doesn't overlap sites it has already crawled but won't stop
        # multiple procs from scanning the same site [though that should be a very
        # small occurance])
        sites_crawled = set()
        counter = 1
        while True:
            try:
                if not PauseCV.is_set():
                    checkinQueue.put_nowait(int(procID))
                    crawlerlib.printDEBUG(ID, "Checked in and waiting...", level=0)
                    PauseCV.wait()
                    if ResetBool.is_set():
                        # get driver again
                        driver = get_driver(ID, args.logFile, args.path, args.profile)
                        crawlerlib.printDEBUG(ID, "SUCCESSFULLY RESTARTED DRIVER", level=0)

                site = sites_to_crawl.get(timeout=10)

                # Communication object for data output
                comms = Comms(site)

                try:
                    if counter % 50 == 0:
                        driver.quit()
                        driver = get_driver(ID, args.logFile, args.path, args.profile)
                        crawlerlib.printDEBUG(ID, "SUCCESSFULLY RESTARTED DRIVER", level=0)
                    crawlerlib.printDEBUG(ID, "PROCESSING SITE #%s" % counter , level=0)
                    # check if site already has protocol (this could happen with
                    # the test input, or test input file)
                    if site.startswith("http://"):
                        http_site = site
                        https_site = None
                    elif site.startswith("https://"):
                        https_site = site
                        http_site = None
                    else:
                        http_site = "http://%s" % site
                        https_site = "https://%s" % site

                    if http_site and crawlerlib.crawl_site(ID, http_site, driver, comms):
                        crawlerlib.find_and_fill(ID, driver, sites_crawled, blacklist, comms)
                    if https_site and https_site not in sites_crawled:
                        if crawlerlib.crawl_site(ID, https_site, driver, comms):
                            crawlerlib.find_and_fill(ID, driver, sites_crawled, blacklist, comms)
                    counter += 1
                    crawlerlib.printLOG(ID, comms)
                except KeyboardInterrupt:
                    driver.quit()
                    crawlerlib.printDEBUG(ID, "Quitting after KEYBOARDINTERRUPT", level=0)
                    comms.add_error("KeyboardInterrupt in proc_manager")
                    crawlerlib.printLOG(ID, comms)
                    return 1
                except:
                    error = print_exception(ID)
                    comms.add_error(error)
                    crawlerlib.printLOG(ID, comms)
                    driver.quit()
                    driver = get_driver(ID, args.logFile, args.path, args.profile)
                    crawlerlib.printDEBUG(ID, "SUCCESSFULLY RESTARTED DRIVER", level=0)

            except (KeyboardInterrupt, queue.Empty):
                break
        driver.close()
        crawlerlib.printDEBUG(ID, "Multiprocess #%s finished" % procID, level=0)
    except KeyboardInterrupt:
        if get_driver_status(driver):
            driver.close()
        crawlerlib.printDEBUG(ID, "Multiprocess #%s Keyboard Interruptted" % procID, level=0)
    except (http_client.BadStatusLine, socket.error):
        # firefox shutdown before response was read on the socket
        return 1
    except Exception as err:
        crawlerlib.printDEBUG(ID, "Process function had unexpected and uncaught error: %s" % (repr(err)), level=0)
        return 1


def get_driver_status(driver):
    try:
        driver.execute(Command.STATUS)
        return 1
    except (socket.error, http_client.CannotSendRequest):
        return 0



def make_list_queue(inList, mainID):
    x = mainID.split("-")
    runSeed = x[0]
    with open("./%s/inputList.txt" % runSeed, "w") as inputList:
        retQueue = Queue()
        for item in inList:
            retQueue.put(item)
            print(item, file=inputList)
        return retQueue

class Comms:
    def __init__(self, url):
        self.site = url
        self.errors = []
        self.form = False
        self.typed = []
        self.subpages = []
        self.submitted = False
        self.start = datetime.now().strftime("%m/%d/%Y-%H:%M:%S:%f")

    def __str__(self):
        return json.dumps(self._dictionary())
        

    def _dictionary(self):
        return {"site": self.site, "errors": self.errors,
                "form": self.form, "typed": self.typed,
                "subpages": self.subpages, "submitted": self.submitted, 
                "start": self.start, "end": datetime.now().strftime("%m/%d/%Y-%H:%M:%S:%f")}
    
    ##### Methods used by worker threads #####
    def add_error(self, error):
        self.errors.append(error)

    def found_form(self):
        self.form = True

    def add_typing(self, typed_string):
        self.typed.append(typed_string)

    def add_subpage(self, subpage):
        self.subpages.append(subpage)

    def submitted_form(self):
        self.submitted = True
    ##### End Methods used by worker threads #####

    ##### Methods used by MAIN / logging thread #####
    def jsonString(self):
        return self.__str__()
    
    def jsonObj(self):
        return self._dictionary()
    ##### End Methods used by MAIN / logging thread #####

class RequestReset:
    def __init__(self):
        self.reset = False
        self.waitingGroup = Event()
        self.waitingGroup.clear()
    
    def request(self):
        self.reset = True
        self.waitingGroup.clear()
        self.waitingGroup.wait()

    def clear(self):
        self.reset = False
        self.waitingGroup.set()

    def value(self):
        return self.reset


class ProcManager:
    def __init__(self, mainID, sites_to_crawl, runSeed, blacklist, args, test, num_proc=None):
        self.mainID = mainID
        self.sites_to_crawl = sites_to_crawl
        self.runSeed = runSeed
        self.blacklist = blacklist
        self.args = args
        self.test = test
        self.pauseEvent = Event()
        #self.pauseEvent.set()
        self.pauseEvent.clear()
        self.resetEvent = Event()
        self.resetEvent.clear()
        self.procList = []
        self.resetRequest = RequestReset()
        if not num_proc:
            cpus = cpu_count()
            self.num_proc = math.floor(cpus * .875)
        else:
            self.num_proc = num_proc
        #self.goodCheckins = Queue(self.num_proc)
        self.goodCheckins = Queue()

    def checkin(self, reset=False):
        ALLDONE = False
        # checkin with all procs
        crawlerlib.printDEBUG(self.mainID, "Check In proceedure started: RESET = %s" % reset, level=0)
        # 1. Issue pause
        self.pause()
        if reset:
            self.send_reset_signal()
        else:
            self.clear_reset_signal()
        
        # 2. Wait for timeout
        # TODO: fine tune this sleep timer here... 20 seconds seemed to not have
        # full coverage; 60 seconds also seemed to be too quick; I'm suspecting
        # threads are held up by the print statements
        time.sleep(90)
        num_sites_left_to_scan = self.sites_to_crawl.qsize()
        if num_sites_left_to_scan == 0:
            ALLDONE = True
        
        crawlerlib.printDEBUG(self.mainID, "Sites left to scan: %d" % num_sites_left_to_scan, level=0)
        
        # 3. Check on goodCheckins

        soft_reset = self.goodCheckins.empty()

        # 4. Kill what needs to die
        tmpList = [x for x in range(0,self.num_proc)]
        while not self.goodCheckins.empty():
            x = self.goodCheckins.get_nowait()
            try:
                tmpList.remove(x)
            except ValueError:
               crawlerlib.printDEBUG(self.mainID, "ValueError error when removing item from tmpList in checkin(), list is: {} and x is: {}".format(tmpList, x), level=0)
        tmpList.sort(reverse=True)
        for procNUM in tmpList:
            crawlerlib.printDEBUG(self.mainID, "Process %d failed to check in" % procNUM, level=1)
            # Kick off replacement procs for step 4
            self.kill_proc(procNUM)
            crawlerlib.printDEBUG(self.mainID, "Process %d KILLED" % procNUM, level=1)
            self.procList.pop(procNUM)
            self.start_proc(procNUM, printLevel=2)
            crawlerlib.printDEBUG(self.mainID, "Process %d RESTARTED" % procNUM, level=1)
            
       
        # If all procs are unresponsive, we have restarted them all. We do not
        # have to send the reset signal since all procs will be starting fresh
        # and waiting at the first pause condition, then they will proceed to
        # make a driver to work with
        if soft_reset and not reset:
           self.clean_all() 
        
        # 6. Resume
        if not reset:
            crawlerlib.printDEBUG(self.mainID, "Processes starting to resume...", level=1)
            self.resume()
            crawlerlib.printDEBUG(self.mainID, "Processes resumed", level=1)
        return ALLDONE

    def start_proc(self, procID, printLevel=0):
        p = Process(target=process_function, args=(self.runSeed, str(procID),
                                        self.sites_to_crawl, self.blacklist, self.args,
                                        self.resetEvent, self.pauseEvent,
                                        self.goodCheckins, self.resetRequest))
        self.procList.insert(int(procID), p)
        # setting as daemon so when main exits all children exit
        p.daemon = True
        p.start()
        crawlerlib.printDEBUG(self.mainID, "Starting process number: %d" % int(procID), level=printLevel)

    def pause(self):
        # pause all procs
        # set pauseEvent
        self.pauseEvent.clear()

    def send_reset_signal(self):
        self.resetEvent.set()

    def clear_reset_signal(self):
        self.resetEvent.clear()

    def resume(self):
        # resumes all procs
        # clears pauseEvent
        self.pauseEvent.set()

    def kill_proc(self, procID):
        # kills a process
        # picks out proc from procList and issues .kill()

        # TODO: need to test this function, I'm worried that if the process is
        # unresponsive that it will just hang forever on the close / kill... 
        # One thought could be to get the PID and just have the OS to ahead and
        # murder the process... we shall see I suppose
        # TODO: just found if a proc has finished and is trying to be killed bad
        # things obviously happen
        try:
            self.procList[procID].close()
        except ValueError:
            self.procList[procID].kill()
        except AttributeError:
            return

    def clean_all(self):
        # os kill all firefox and geckodriver
        # Time to murder firefox and geckodriver
        p = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE)
        out, err = p.communicate()
        counter = 0
        for line in out.splitlines():
            line = line.decode("utf-8")
            if 'firefox' in line or 'geckodriver' in line:
                pid = int(line.split(None, 1)[0])
                try:
                    os.kill(pid, signal.SIGKILL)
                    counter += 1
                except ProcessLookupError as err:
                    continue
        
        crawlerlib.printDEBUG(self.mainID, "Firefox & Geckodriver processes killed - number killed was %d" % counter, level=0)

    def run_scan(self):
        # GLOBALS for how often to check in on procs and how often to do a full
        # reset
        # TODO: fine tune these globals more
       
        # If check in time is too short, you get a system crash (happened w/ 2m)
        CHECK_IN_TIME = 60 * 90 # 90 mins I think
        RESET_NUM = 5000 # every 5000 sites scanned
        

        # TODO: I think that I could make the reset signal just a bool that is
        # passed around... hmmmm though it needs to be async... possibly a
        # Manager class would be useful here... could be interesting as well to
        # do a remote manager thing where we could just run workers on a cluster
        # etc etc... 

        # Processes start paused as _init_ clears the CV
        for proc in range(0, self.num_proc):
            self.start_proc(str(proc))

        # Since qsize isnt fully reliable in a multiprocessing scenario, we 
        #need to approximate, so holding
        # onto the old value and comparing to the approximate value taken at
        # another point in time to do the hard resets
        num_sites_left = self.sites_to_crawl.qsize()
        
        # Kick off all threads that are waiting to begin
        self.resume()

        while not self.sites_to_crawl.empty():
            
            # Hard reset calls
            if (num_sites_left - self.sites_to_crawl.qsize() >= RESET_NUM) or (self.resetRequest.value()):
                num_sites_left = self.sites_to_crawl.qsize()
                AllDone = self.checkin(reset=True)
                # Threads have been paused, checked on, and killed if necessary
                # with new procs spawned to take their place AND the reset
                # signal has been set, so procs will know upon resumption to
                # reset
                # PROCS are NOT resumed here, and will be waiting on the pause
                # cv
                self.clean_all()
                self.resume()
                self.resetRequest.clear()
                
                if AllDone:
                    return 0
            
            # Check in calls: sleep for specified time, then run the check in
            # proceedure 
            time.sleep(CHECK_IN_TIME / 3)
            
            if self.resetRequest.value():
                self.checkin(reset=True)
                self.clean_all()
                self.resume()
                self.resetRequest.clear()
            
            time.sleep(CHECK_IN_TIME / 3)
            
            AllDone = self.checkin()
            if AllDone:
                return 0
            
            time.sleep(CHECK_IN_TIME / 3)


def main():
    test, args = parse_cmd()
    runSeed = get_run_seed()
    mainID = runSeed + "-" + "MAIN"
    
    screenshot_path = "./" + runSeed + "/screenshots"
    data_path = "./" + runSeed + "/data"
    run_log_path = "./" + runSeed + "/runLogs"
    try: 
        os.makedirs(screenshot_path)
        os.makedirs(data_path)
        os.makedirs(run_log_path)
    except OSError:
        print("error creating directory structure: %s" % data_path)
        print("error creating directory structure: %s" % screenshot_path)
        print("error creating directory structure: %s" % run_log_path)
        print_exception(mainID)
        sys.exit(1)
    

    if args.globalYMLin:
        globalsIn = get_globals(mainID, args.globalYMLin)
        globals().update(globalsIn)
        crawlerlib.init_globals(globalsIn)

    blacklist = crawlerlib.get_blacklist(mainID, args.blacklistFile)

    # Try and open test url file, if fails, then assume a url was handed on the
    # cmd line
    sites_in = []
    if test:
        try:
            with open(args.testOpen, "r") as sites:
                for line in sites:
                    line = line.strip()
                    sites_in.append(line)
        except FileNotFoundError:
            # If test was a url and not a file handle
            sites_in = [args.testOpen]
    else:
        # args.mode: TOP, STUDY, RAND
        
        if args.mode == "TOP":
            # Gets args.num of the top sites in order
            sites_in = get_sites(mainID, args.num)
        
        if args.mode == "RAND":
            # Gets args.num random sites from the top 1M
            sites_in = get_random_sites(mainID, args.num)

        if args.mode == "STUDY":
            # Gets args.num sites in the study breakdown and randomly shuffles them
            # 30% of the top sites
            # 30% from end of ^ to 100K
            # 40% from 100K to 1M
            sites_in = get_study_sites(mainID, args.num)

    # Turning site list into multiprocessing Queue() 
    sites_to_crawl = make_list_queue(sites_in, mainID)

    # Initialize instance of ProcManager and invoke the run_scan method
    manager = ProcManager(mainID, sites_to_crawl, runSeed, blacklist, args, test)
    #manager = ProcManager(mainID, sites_to_crawl, runSeed, blacklist, args, test, num_proc=8)
    manager.run_scan()


    crawlerlib.printDEBUG(mainID, "All processes are completed!", level=0)
    # To let any procs that may be finishing (from checkin's all done signal)
    # finish before exiting. Because the procs are daemon's they will be killed
    # when this proc finishes
    time.sleep(20)
    
    return 0

if __name__ == "__main__":
    main()

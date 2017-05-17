"""
Frits Dannenberg, May 17th, 2017.
This module has two parts.
1) Given multistrand results, compute reaction rate constants. 
2) A module for running multistrand concurrently. Results are merged automatically
"""
import operator
import time, datetime, math

from multistrand.options import Options
import multiprocessing
import numpy as np

from multistrand.system import SimSystem 


MINIMUM_RATE = 1e-18;


## Rate-computation classes start here



# Shared class methods
class basicRate(object):
    
    def log10KEff(self):
        
        return np.log10(self.kEff())


## Migration rates for first step
class migrationRate(basicRate):
    
    
    def __init__(self, dataset=None, concentration=None):
        
        
        if not concentration == None:        
            # empty constructor for resampling code
            self.z = np.float(concentration)

        
        if dataset == None:
        
            
            self.collision_rates = []
            self.was_success = []
            self.was_failure = []
            self.time = []
            
            self.generateRates()

        else:
        
            # process the result on object creation
            self.process(dataset, concentration)
            self.generateRates()
      
    
    def terminate(self, dataset):
        
        newRates = migrationRate(dataset=dataset, concentration=1e-99)
        
        print(str(newRates))
        
        if(newRates.nForward <= 25):
            return False
        else: 
            return True
        
        
    
    def process(self, dataset, concentration):
        
        # concentration not actually used in generateRates
        self.z = concentration
        
        # Now determine the reaction model parameters from the simulation results.  (Simplified from hybridization_first_step_mode.py.)    
        
        # if there is no collision_rate set, then either something is wrong or we're not using first step mode. Default to 
        # a standard collisionrate so we can at least run the code TODO
         
        self.collision_rates = np.array([ i.collision_rate for i in dataset])
        
        self.was_success = np.array([1 if i.tag == Options.STR_SUCCESS else 0 for i in dataset])
        self.was_failure = np.array([1 if i.tag == Options.STR_FAILURE else 0 for i in dataset])
        
        # save unprocessed times for re-sample
        self.time = np.array([ i.time for i in dataset])
        

    def generateRates(self):
        
        
        self.forward_times = np.array([self.time[i] for i in range(len(self.was_success)) if self.was_success[i] == 1])
        self.reverse_times = np.array([self.time[i] for i in range(len(self.was_failure)) if self.was_failure[i] == 1])
       
        self.collision_forward = np.array([self.collision_rates[i] for i in range(len(self.was_success)) if self.was_success[i] == 1])
        self.collision_reverse = np.array([self.collision_rates[i] for i in range(len(self.was_failure)) if self.was_failure[i] == 1])
        
        self.nForward = sum(self.was_success)
        self.nReverse = sum(self.was_failure)
        self.nTotal = self.nForward + self.nReverse

    # FD: this is the concentration-independent rate
    def k1(self):

        # Erik's notes:   
        # Basic calculations from Joseph's PhD thesis.  (See also threewaybm_first_step_mode.py.)
        # The equations there were derived for runs stating with exact microstates.
        # Here, as we are using Boltzmann sampling, which requires that the mean collision rate 
        # be calculated separately for forward and reverse cases, since conditioning on success
        # might alter the distribution of secondary structures, and thus the collision rates.
     
        forward_kcoll = np.mean(self.collision_forward)
        
        if not self.nTotal==0:
            prob = np.float(self.nForward) / np.float(self.nTotal)
        else:
            return MINIMUM_RATE
#             raise Warning("Could not find the results, nTotal = 0")

        k1 = prob * forward_kcoll  
        
        return k1
    
    # FD: this is the concentration-dependent rate
    def kEff(self, concentration=None):
        
        if not concentration == None:
            z = np.float(concentration)
        else:
            z = self.z

        if(self.nForward == 0):
            return MINIMUM_RATE
    
        dTsuccess_uni = np.mean(self.forward_times)
        dTfail_uni = np.mean(self.reverse_times)
        
        kcollision = np.mean(self.collision_rates)
        
        kcollision_foward = np.mean(self.collision_forward)
        kcollision_reverse = np.mean(self.collision_reverse)        
        
        
        multiple = float(self.nReverse) / float(self.nForward)

        dTcoll = np.float(1.0) / ((kcollision) * z)

        if(True):  # toggle if use specific collision rates or not
            dTcoll_forward = np.float(1.0) / ((kcollision_foward) * z)
            dTcoll_reverse = np.float(1.0) / ((kcollision_reverse) * z)
        else:
            dTcoll_forward = dTcoll
            dTcoll_reverse = dTcoll
       
        
        dTfail = dTcoll_reverse + dTfail_uni
        dTforward = dTcoll_forward + dTsuccess_uni
        
        dTcorrect = dTfail * multiple + dTforward
        
        kEff = (1 / dTcorrect) * (1 / z)
        
        return kEff



    def resample(self):
        
        # returns a new rates object with resampled data
        
        newRates = migrationRate(concentration=self.z)
        
        N = len(self.collision_rates)
        
        # # generate random between 0 and N-1
        
        for i in range(N):
        
            index = int(np.floor(np.random.uniform(high=N)))
            
            newRates.collision_rates.append(self.collision_rates[index])
            newRates.was_success.append(self.was_success[index])
            newRates.was_failure.append(self.was_failure[index])
            newRates.time.append(self.time[index])

        
        newRates.castToNumpyArray()       
        newRates.generateRates()
        
        return newRates
    

    def castToNumpyArray(self):
        

        self.collision_rates = np.array(self.collision_rates)
        self.was_success = np.array(self.was_success)
        self.was_failure = np.array(self.was_failure)
        self.time = np.array(self.time)
        

    def merge(self, that):
        
        if not self.z == that.z:
            print("Error! Cannot combine results from different concentrations")
            
        # Now merge the existing datastructures with the ones from the new dataset
        self.collision_rates = np.concatenate([self.collision_rates, that.collision_rates])
        self.was_success = np.concatenate([self.was_success, that.was_success])
        self.was_failure = np.concatenate([self.was_failure, that.was_failure])
        self.time = np.concatenate([self.time, that.time])

        # re-generate the rates
        self.generateRates()


        
    # # override toString
    def __str__(self):
        
        output = "nForward = " + str(self.nForward) + " \n"
        output += "nReverse = " + str(self.nReverse) + " \n"
        output += "k1 = " + str(self.k1()) + " /M/s   \n"
        output += "k_eff = " + str(self.kEff()) + " /M/s   \n"
        output += ", concentration = " + str(self.z) + " M  \n "
        
        return output



# Like migrationrate, but uses data from first passage time rather than first step mode
class migrationRatePassage(basicRate):
    
    def __init__(self, dataset=None, concentration=None):
        
        if dataset == None:
            
            # set up for resampling 
            self.concentration = concentration
            self.times = []
            self.timeouts = []
            
        else:
            self.process(dataset, concentration)
            self.generateRates()
        
    def process(self, dataset, concentration):
               
        self.concentration = concentration
        self.times = np.array([i.time for i in dataset])
        self.timeouts = [i for i in dataset if not i.tag == Options.STR_SUCCESS]
        
    def castToNumpyArray(self):
        
        self.times = np.array(self.times)
    
    def resample(self):
        
        # avoid resampling time-outs.
        newRates = migrationRatePassage(concentration=self.concentration)
        
        N = len(self.times)
        
        # generate random between 0 and N-1        
        for i in range(N):
        
            index = int(np.floor(np.random.uniform(high=N)))
            
            newRates.times.append(self.times[index])
        
        newRates.castToNumpyArray()       
        newRates.generateRates()
        
        return newRates
                
    
    def generateRates(self):
        0


    def kEff(self):
        
        if len(self.timeouts) > 0 :
            
            print("# association trajectories did not finish =",  str(len(self.timeouts)))
            for i in self.timeouts :
                assert (i.type_name == 'Time')
                assert (i.tag == None)
                assert (i.time >= 10.0)
        
#         print "average completion time = %g seconds at %s" % (np.mean(self.times), concentration_string(self.concentration))
        
        
        mean = np.mean(self.times)
        kEff = np.float(1.0) / (mean * self.concentration)
        
        
        return kEff


class bootstrap():
    
    
    def __init__(self, myRates, concentration=None):
        
        self.myRates = myRates
        
        self.process(concentration)
        
    def process(self, concentration):
        
        # # Resample the dataset
        
        self.effectiveRates = list()
        self.logEffectiveRates = list()
        self.N = 1000
        
        if not concentration == None:
            self.myRates.z = concentration
        
        for i in range(self.N):
            
            sample = self.myRates.resample()
            rate = float(sample.kEff())
            self.effectiveRates.append(rate)
            
            del sample
                
        self.effectiveRates.sort(cmp=None, key=None, reverse=False)
        
        for rate in self.effectiveRates:
            self.logEffectiveRates.append(np.log10(rate))
        
        
    
    def ninetyFivePercentiles(self):
        
        low = self.effectiveRates[int(0.025 * self.N)]
        high = self.effectiveRates[int(0.975 * self.N)]
        
        return low, high
    
    def standardDev(self):
        
        return np.std(self.effectiveRates)
    
    def logStd(self):
        
        # Returns standard deviation from the mean of log10 of the original rates
        return np.std(self.logEffectiveRates)

        


## Concurrent classes start here



class optionsFactory(object):   
    
    def __init__(self, funct, put0, put1, put2, put3, put4, put5, put6):
        
        self.myFunction = funct
        self.input0 = put0
        self.input1 = put1
        self.input2 = put2
        self.input3 = put3
        self.input4 = put4
        self.input5 = put5 
        self.input6 = put6 
        
    
    def new(self, inputSeed):
        
        output = None
        
        if self.input1 == None:
            output = self.myFunction(self.input0)        
        elif self.input2 == None:
            output = self.myFunction(self.input0, self.input1)
        elif self.input3 == None:
            output = self.myFunction(self.input0, self.input1, self.input2)
        elif self.input4 == None:
            output = self.myFunction(self.input0, self.input1, self.input2, self.input3)
        elif self.input5 == None:
            output = self.myFunction(self.input0, self.input1, self.input2, self.input3, self.input4)
        elif self.input6 == None:
            output = self.myFunction(self.input0, self.input1, self.input2, self.input3, self.input4, self.input5)
        else: 
            output = self.myFunction(self.input0, self.input1, self.input2, self.input3, self.input4, self.input5, self.input6)
            
        output.initial_seed = inputSeed
            
        return output


# hard-coded locks
# # this is a manager.dict, that is dict, lock is multithreading.lock
def mergeDictAdd (this, that, lock):
    
    with lock:    
        for key, value in that.iteritems():
            
            if(this.has_key(key)):
                this[key] += value
            else:
                this[key] = value
            
def mergeDictBinary(this, that, lock):
    
    # # If an entry in that is non-zero, add +1 to this using the same key
    with lock:
        for key, value in that.iteritems():
            
            if(value > 0):
            
                if(this.has_key(key)):
                    this[key] += 1
                else:
                    this[key] = 1


def mergeDict (this, that, lock):
    
    with lock:    
        for key, value in that.iteritems():
            
            if not(key in this):
        
                this[key] = value

def mergeList (this, that, lock):
    
    with lock:    
        for entry in that:
            
            this.append(entry)
        

def mergeCount(mValue, counter, lock):
        
    with lock:
        mValue.value = mValue.value + counter
        



class msSettings(object):
    
    debug = False
    
def timeStamp(inTime=None):
    
    if inTime == None:
        inTime = time.time()
    
    return str(datetime.datetime.fromtimestamp(inTime).strftime('%Y-%m-%d %H:%M:%S'))

class msMulti(object):

    numOfThreads = 2
    seed = 7713147777;
    

    def __init__(self, settings=None):

        
        self.initializationTime = time.time()
        print(timeStamp(), "   Starting Multistrand 3.0    (c) 2008-2016 Caltech   ")
                

        self.factory = optionsFactory
        self.aFactory = None
        
        if(settings == None):
            self.settings = msSettings()
            
        # override to enable dynamic simulation length
        self.terminationCriteria = None


    def setTerminationCriteria(self, input):
        
        self.terminationCriteria = input
        
    def timeSinceStart(self):
        
        print("Time since creating object %.5f seconds" % (time.time() - self.initializationTime))
#                 print("Done.  %.5f seconds" % (time.time() - startTime))
        
    
    def setDebug(self, value):
        
        self.settings.debug = value
        
    
    def setNumOfThreads(self, numOfThreads):
        
        self.numOfThreads = numOfThreads

    def setOptionsFactory(self, optionsFactory):
        
        self.factory = optionsFactory

    def setOptionsFactory1(self, myFun, put0):
        
        self.factory = optionsFactory(myFun, put0, None, None, None, None, None, None) 
 
    def setOptionsFactory2(self, myFun, put0, put1):
        
        self.factory = optionsFactory(myFun, put0, put1, None, None, None, None, None) 

    def setOptionsFactory3(self, myFun, put0, put1, put2):
        
        self.factory = optionsFactory(myFun, put0, put1, put2, None, None, None, None) 

    def setOptionsFactory4(self, myFun, put0, put1, put2, put3):
        
        self.factory = optionsFactory(myFun, put0, put1, put2, put3, None, None, None)
    
    def setOptionsFactory5(self, myFun, put0, put1, put2, put3, put4):
        
        self.factory = optionsFactory(myFun, put0, put1, put2, put3, put4, None, None)  
    
    def setOptionsFactory6(self, myFun, put0, put1, put2, put3, put4, put5):
        
        self.factory = optionsFactory(myFun, put0, put1, put2, put3, put4, put5, None)

    def setOptionsFactory7(self, myFun, put0, put1, put2, put3, put4, put5, put6):
        
        self.factory = optionsFactory(myFun, put0, put1, put2, put3, put4, put5, put6)

    def setAnaylsisFactory(self, mySeq, cutOff):
        
        lockArray = list()
        for i in range(16):
            lockArray.append(multiprocessing.Lock())
         
        self.aFactory = analysisFactory(mySeq, cutOff)
        self.aFactory.lockArray = lockArray        
        

    def numOfSuccesTrials(self):
        
        count = 0
        
        for result in self.results:
            if result.tag == STR_SUCCESS:
                count += 1

        return count

    # reset the multithreading objects
    def clear(self):
        
        if not self.aFactory == None:
            self.aFactory.clear()
    
    def printTrajectories(self, myOptions):
        # # Print all the trajectories we can find. 
        # # Debug function primairly. 
        
        print("Printing trajectory and times: \n")
        
        
        trajs = myOptions.full_trajectory 
        times = myOptions.full_trajectory_times
        
        for t, time in zip (trajs, times):
            
            print (t, "  t=", time, "\n")
        
        0
    
    def initialInfo(self):
        
        myOptions = self.factory.new(777)
        simSys = SimSystem(myOptions)
        simSys.initialInfo()


    def startSimMessage(self):
        
        welcomeMessage = "Computing " + str(self.numOfThreads * self.trialsPerThread) 
        welcomeMessage += " trials,  using " + str(self.numOfThreads)  
        welcomeMessage += " threads  .. "
        return welcomeMessage
#         print(welcomeMessage, end="")


    def run(self):
        
        # The input0 is always trails.
        self.trialsPerThread = int(math.ceil(float(self.factory.input0) / float(self.numOfThreads)))
        
        startTime = time.time()
        
        
        #FD: Analysis factory is only used for the likelihood plots in the Multistrand 2.0 casestudy.
        def doAnalysis(aFactory, myOptions):
       
        
            myAnalysis = analysisFactory(aFactory.mySeq, aFactory.cutOff)
        
            def processAndMergeDicts(clause, myOptions, myAnalysis, analysisResult, lockArray):
            
                
                traj, times, pathCount = myAnalysis.selectTrajectories(clause, myOptions.interface.results, myOptions.full_trajectory, myOptions.full_trajectory_times)
            
                posDict, countDict, pathProps, structDict2 = myAnalysis.analyzeTrajectory(traj, times)   
                firstTraj = myAnalysis.parseFirstTrajectory(traj, times)
                analysisResult.setInitialTrajectory(firstTraj, lockArray[1])
                
                mergeDictAdd(analysisResult.posDict, posDict, lockArray[0])
                mergeDict(analysisResult.countDict, countDict, lockArray[2])
                mergeDictBinary(analysisResult.binaryDict, countDict, lockArray[3])
                
                
                mergeList(analysisResult.pathProps, pathProps, lockArray[4])
                mergeCount(analysisResult.pathCount, pathCount, lockArray[5])
                
                for i in range(len(structDict2)):
                    if not structDict2[i] == None:
                        mergeDictAdd(analysisResult.structDict2[i], structDict2[i], lockArray[6])
                    
                
                
        
            processAndMergeDicts(myAnalysis.selectors[0], myOptions, myAnalysis, aFactory.result0, aFactory.lockArray)
            processAndMergeDicts(myAnalysis.selectors[1], myOptions, myAnalysis, aFactory.result1, aFactory.lockArray)
            processAndMergeDicts(myAnalysis.selectors[2], myOptions, myAnalysis, aFactory.result2, aFactory.lockArray)
        
        
        

                        
        def doSim(myFactory, aFactory, list0, list1, seed):
                        
            
            myOptions = myFactory.new(seed)
            myOptions.num_simulations = self.trialsPerThread
        
            s = SimSystem(myOptions)
            s.start()
            
            for result in myOptions.interface.results:
                
                list0.append(result)   
                 
            for endState in myOptions.interface.end_states:
                
                list1.append(endState)
            
            if not(aFactory == None):
                
                doAnalysis(aFactory, myOptions)
            
            if self.settings.debug:
                
                self.printTrajectories(myOptions)
                
        
        assert(self.numOfThreads > 0)
        
        manager = multiprocessing.Manager()
        
        self.results = manager.list()
        self.endStates = manager.list()
        
        
    
        terminate = False

        while not terminate:

            print(self.startSimMessage(), "\n") 

            procs = []
            
            for i in range(self.numOfThreads):
                
                instanceSeed = self.seed + i * 3 * 5 * 19 + (time.time() * 10000000) % (math.pow(2, 16) - 1)
                
                          
                p = multiprocessing.Process(target=doSim, args=(self.factory, self.aFactory, self.results, self.endStates, instanceSeed))
                procs.append(p)
                p.start()
            
                
            for i in range(self.numOfThreads):
                procs[i].join()
             
            print("Done.  %.5f seconds" % (time.time() - startTime))
            
            
            if self.terminationCriteria == None:
                terminate = True
            else: 
                terminate = self.terminationCriteria.terminate(self.results)    
                self.trialsPerThread = self.trialsPerThread * 2
        
        
        
        self.runTime = (time.time() - startTime)
        
        return 0


# simply pipes the initial info command.
def initialInfo(self):
                          
    def initialInfo(myFactory):
                    
        
        myOptions = myFactory.new(777)
        myOptions.num_simulations = self.trialsPerThread
    
        s = SimSystem(myOptions)
        s.initialInfo() 
    
    
    multiprocessing.Process(target=initialInfo(), args=(self.factory))


# # The default multistrand object
myMultistrand = msMulti()
        
        
          
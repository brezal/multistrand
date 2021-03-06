
# Often recurring experimental setups
from multistrand.objects import Complex, Domain, Strand, StopCondition
from multistrand.options import Options


def setBoltzmann(complexIn, trials, supersample=1):
    complexIn.boltzmann_supersample = supersample
    complexIn.boltzmann_count = trials
    complexIn.boltzmann_sample = True


# easy handle for options creation
def standardOptions(simMode=Options.firstStep, tempIn=25.0, trials=10, timeOut=0.1):

    output = Options(simulation_mode=simMode,
                     rate_method=Options.metropolis,
                     num_simulations=trials,
                     simulation_time=timeOut,
                     temperature=tempIn
                     )

    output.DNA23Metropolis()

    return output


def makeComplex(seq, dotparen):

    strandList = []

    for seq in seq:

        onedomain = Domain(
            name="domain" + str(makeComplex.counter), sequence=seq)
        makeComplex.counter += 1

        onestrand = Strand(domains=[onedomain])
        strandList.append(onestrand)

    return Complex(strands=strandList, structure=dotparen)

makeComplex.counter = 0



def hybridization(options, mySeq, myTrials=0, doFirstPassage=False):

    # Using domain representation makes it easier to write secondary structures.
    onedomain = Domain(name="itall", sequence=mySeq)
    top = Strand(name="top", domains=[onedomain])
    bot = top.C

    # Note that the structure is specified to be single stranded, but this will be over-ridden when Boltzmann sampling is turned on.
    startTop = Complex(strands=[top], structure=".")
    startBot = Complex(strands=[bot], structure=".")

    # Turns Boltzmann sampling on for this complex and also does sampling more efficiently by sampling 'trials' states.
    if(myTrials > 0):
        setBoltzmann(startTop, myTrials)
        setBoltzmann(startBot, myTrials)

    # Stop when the exact full duplex is achieved.
    success_complex = Complex(strands=[top, bot], structure="(+)")
    stopSuccess = StopCondition(Options.STR_SUCCESS, [(
        success_complex, Options.exactMacrostate, 0)])

    # Declare the simulation unproductive if the strands become single-stranded again.
    failed_complex = Complex(strands=[top], structure=".")
    stopFailed = StopCondition(Options.STR_FAILURE, [(
        failed_complex, Options.dissocMacrostate, 0)])

    options.start_state = [startTop, startBot]

    # Point the options to the right objects
    if not doFirstPassage:

        options.stop_conditions = [stopSuccess, stopFailed]

    else:

        options.stop_conditions = [stopSuccess]

 # Does not inherit NormalSeesawGate - basically have to rewrite everything

# simulates until a dissociation event occurs. 
# Note: for long sequences, this could result in a timeout.
def dissociation(options, mySeq, myTrials=0):
                
    # Using domain representation makes it easier to write secondary structures.
    onedomain = Domain(name="itall", sequence=mySeq)
    top = Strand(name="top", domains=[onedomain])
    bot = top.C
    
    # Note that the structure is specified to be single stranded, but this will be over-ridden when Boltzmann sampling is turned on.
    duplex = Complex(strands=[top, bot], structure="(+)")
    
    # Turns Boltzmann sampling on for this complex and also does sampling more efficiently by sampling 'trials' states.
    if(myTrials > 0):
        setBoltzmann(duplex, myTrials)
    
    # Stop when the strands fall apart.
    successComplex = Complex(strands=[top], structure=".")
    stopSuccess = StopCondition(Options.STR_SUCCESS, [(successComplex, Options.dissocMacrostate, 0)])
    
    options.start_state = [duplex]
    options.stop_conditions = [stopSuccess]         
        







# Aug 2017: this is Mrinanks' implementation of the clamped seesaw gate.



# this is how much the domain overlaps
# see Figure 1, Winfree Qian 2010 -- A simple DNA gate motif for synthesizing large-scale circuits 
SEESAW_DELTA = 5


# Domain list as a list of strings, defined as follows input_sequence, base_sequence, output_sequence, fuel_sequence,
# toehold_sequence, clamp_sequence which defaults to clamp_sequence 
# This method takes a gate output complex and its input and then calculate the rate of output production
def clamped_gate_output_production(options, domain_list, trials, supersample=25, doFirstPassage=False):
    gate = ClampedSeesawGate(*domain_list)
    two_input(options, gate.gate_output_complex, gate.input_complex,
              gate.output_complex, trials, supersample, doFirstPassage=False)

# Domain list as a list of strings, defined as follows input_sequence, base_sequence, output_sequence, fuel_sequence,
# toehold_sequence, clamp_sequence which defaults to clamp_sequence
# This method takes a gate input complex and its fuels and then calculates the rate of input regeneration
def clamped_gate_fuel_catalysis(options, domain_list, trials, supersample=25, doFirstPassage=False):
    gate = ClampedSeesawGate(*domain_list)
    two_input(options, gate.gate_input_complex, gate.fuel_complex,
              gate.input_complex, trials, supersample, doFirstPassage=False)


# Domain list as a list of strings, defined as follows input_sequence, base_sequence, output_sequence, fuel_sequence,
# toehold_sequence, clamp_sequence which defaults to clamp_sequence
# This method takes a gate output complex with its fuel complex and calculates the ***leak*** rate at which
# the fuel displaces the output i.e. the rate of leak output production.
def clamped_gate_output_leak(options, domain_list, trials, supersample=25, doFirstPassage=False):
    gate = ClampedSeesawGate(*domain_list)
    two_input(options, gate.gate_output_complex, gate.fuel_complex,
              gate.output_complex, trials, supersample, doFirstPassage=False)



def two_input(options, input_complex_A, input_complex_B, output_complex, trials=0, supersample=25, doFirstPassage=False):

    if(trials > 0):
        for x in [input_complex_A, input_complex_B]:
            setBoltzmann(x, trials, supersample)

    successful_stop_condition = StopCondition(
        Options.STR_SUCCESS, [(output_complex, Options.dissocMacrostate, 0)])
    failure_stop_condition = StopCondition(
        Options.STR_SUCCESS, [(input_complex_B, Options.dissocMacrostate, 0)])

    options.start_state = [input_complex_A, input_complex_B]

    # Point the options to the right objects
    if not doFirstPassage:
        options.stop_conditions = [successful_stop_condition, failure_stop_condition]
    else:
        options.stop_conditions = [successful_stop_condition]


class ClampedSeesawGate(object):

    Gate_Count = 1

    def __init__(self, input_sequence, base_sequence, output_sequence, fuel_sequence,
                 toehold_sequence, clamp_sequence="CG"):

        count_str = str(ClampedSeesawGate.Gate_Count) + '_Cl '
        self.input_domain = Domain(
            name="input_domain_" + count_str, sequence=input_sequence)
        self.base_domain = Domain(
            name="base_domain_" + count_str, sequence=base_sequence)
        self.output_domain = Domain(
            name="output_domain_" + count_str, sequence=output_sequence)
        self.fuel_domain = Domain(
            name="fuel_domain_" + count_str, sequence=fuel_sequence)
        self.toehold_domain = Domain(
            name="toehold_domain_" + count_str, sequence=toehold_sequence)
        self.clamp_domain = Domain(
            name="clamp_domain_" + count_str, sequence=clamp_sequence)

        # Use the convention of always adding 5' to 3'
        # Setup stuff for this type of gate

        # Clamp domain setup - add clamp domains either side of each recognition domain
        self.input_strand = self.clamp_domain + self.base_domain + self.clamp_domain + \
            self.toehold_domain + self.clamp_domain + self.input_domain + self.clamp_domain

        self.fuel_strand = self.clamp_domain + self.fuel_domain + self.clamp_domain + \
            self.toehold_domain + self.clamp_domain + self.base_domain + self.clamp_domain

        self.base_strand = self.clamp_domain.C + self.toehold_domain.C + self.clamp_domain.C + \
            self.base_domain.C + self.clamp_domain.C + \
            self.toehold_domain.C + self.clamp_domain.C

        self.output_strand = self.clamp_domain + self.output_domain + self.clamp_domain + \
            self.toehold_domain + self.clamp_domain + self.base_domain + self.clamp_domain

        self.input_partial = Domain(name="partial",
                                    sequence=self.input_domain.sequence[:SEESAW_DELTA])

        self.threshold_base = self.input_partial.C + self.clamp_domain.C + \
            self.toehold_domain.C + self.clamp_domain + \
            self.base_domain.C + self.clamp_domain
        self.base_dom_strand = self.clamp_domain + self.base_domain + self.clamp_domain

        self.gate_output_complex = Complex(strands=[self.base_strand,
                                                    self.output_strand],
                                           structure="..(((((+..)))))")
        self.gate_fuel_complex = Complex(strands=[self.base_strand,
                                                  self.fuel_strand],
                                         structure="..(((((+..)))))")
        self.gate_input_complex = Complex(strands=[self.base_strand,
                                                   self.input_strand],
                                          structure="(((((..+)))))..")
        self.threshold_complex = Complex(strands=[self.threshold_base,
                                                  self.base_dom_strand],
                                         structure="...(((+)))")
        self.input_complex = Complex(strands=[self.input_strand],
                                     structure='.' *
                                     len(self.input_strand.sequence))
        self.fuel_complex = Complex(strands=[self.fuel_strand],
                                    structure='.' *
                                    len(self.fuel_strand.sequence))
        self.output_complex = Complex(strands=[self.output_strand],
                                      structure='.' *
                                      len(self.output_strand.sequence))
        
        ClampedSeesawGate.Gate_Count += 1 
    
   
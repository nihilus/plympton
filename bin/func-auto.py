import yaml
import idascript
import idc

class Object(yaml.YAMLObject):
    yaml_tag = u'!fuzz.io,2011/Object'
    def __init__(self, textSegmentStart, textSegmentEnd):
        self.name = GetInputFilePath() 
        self.functionList = []
        self.importList = []
        self.textSegmentStart = textSegmentStart
        self.textSegmentEnd = textSegmentEnd

        #
        # Pull out all information about functions
        #
        self.initialize_functions()

        self.numFunctions = len(self.functionList)
        self.numImports = len(self.importList)
        self.numBlocks = self.iter_functions()
        self.textSegmentStart = hex(textSegmentStart)
        self.textSegmentEnd = hex(textSegmentEnd)

    def initialize_functions(self): 
        #
        # Iterate through all of the functions
        #
        for fn in Functions(self.textSegmentStart, self.textSegmentEnd):
            tmp = Function(fn)
            if not tmp.isImport:
        	    self.functionList.append(tmp)
            else:
                self.importList.append(tmp)

    def iter_functions(self):
        blockCount = 0
        for fn in self.functionList:
            blockCount = blockCount + fn.iter_chunks()

        return(blockCount)

#
# Create a class for a function
#
class Function(yaml.YAMLObject):
    yaml_tag = u'!fuzz.io,2011/Function'
    def __init__(self, effectiveAddress):
        self.name = Name(effectiveAddress) 
        self.argSize = 0
        self.numArgs = 0
        self.numLocalVars = 0
        self.isImport = False
        self.chunkList = [] 
        self.numChunks = 0
        self.cyclomaticComplexity = 0
        
        #
        # Get the function flags, structure, and frame info
        #
        flags = GetFunctionFlags(effectiveAddress)
        funcStruct = idaapi.get_func(effectiveAddress) 
        frameStruct  = idaapi.get_frame(funcStruct)

        # if we're not in a "real" function. set the id and ea_start manually and stop analyzing.
        if not funcStruct or flags & FUNC_LIB or flags & FUNC_STATIC:
            self.startAddress   = hex(effectiveAddress) 
            self.endAddress     = hex(effectiveAddress) 
            self.name = idaapi.get_name(effectiveAddress, effectiveAddress) 
            self.savedRegSize       = 0
            self.localVarSize       = 0  
            self.frameSize          = 0 
            self.retSize            = 0
            self.isImport  = True
            
            #
            # Need to fix these if possible
            #
            self.argSize            = 0 
            self.numArgs            = 0
            self.numLocalVars       = 0
            return 

		#
		# So we know we're in a real function
		#
        self.startAddress       = funcStruct.startEA
        self.endAddress         = hex(PrevAddr(funcStruct.endEA))
        self.savedRegSize       = funcStruct.frregs
        self.localVarSize       = funcStruct.frsize 
        self.frameSize          = idaapi.get_frame_size(funcStruct)
        self.retSize            = idaapi.get_frame_retsize(funcStruct)

        print("=========================================")
        print("Frame Size %d" % self.frameSize)
        print("EIP Return Size %d" % self.retSize)
        print("Saved Registers Size %d" % self.savedRegSize)
        print("Locals Size %d" % self.localVarSize)
        print("=========================================")
        print("Function name: %s" % self.name)

        #
        # Fixup numbers for arguments and local variables
        #
        self.__init_args_and_local_vars__(funcStruct, frameStruct)

        #
        # Initialize chunks
        #
        self.collect_function_chunks()
        self.cyclomaticComplexity = self.calculate_cyclomatic_complexity(self.startAddress)
        self.startAddress       = hex(self.startAddress)

    def calculate_cyclomatic_complexity (self, function_ea):
        '''Calculate the cyclomatic complexity measure for a function.
		    
	       Given the starting address of a function, it will find all
           the basic block's boundaries and edges between them and will
           return the cyclomatic complexity, defined as:

           CC = Edges - Nodes + 2
		   http://www.openrce.org/articles/full_view/11
        '''

        f_start = function_ea
        f_end = FindFuncEnd(function_ea)

        edges = set([])
        boundaries = set((f_start,))
    
        # For each defined element in the function.
        for head in Heads(f_start, f_end):

            # If the element is an instruction
            if isCode(GetFlags(head)):
        
				# Get the references made from the current instruction
				# and keep only the ones local to the function.
				refs = CodeRefsFrom(head, 0)
				refs = set(filter(lambda x: x>=f_start and x<=f_end, refs))

				if refs:
					# If the flow continues also to the next (address-wise)
					# instruction, we add a reference to it.
					# For instance, a conditional jump will not branch
					# if the condition is not met, so we save that
					# reference as well.
					next_head = NextHead(head, f_end)
					if isFlow(GetFlags(next_head)):
						refs.add(next_head)
                
					# Update the boundaries found so far.
					boundaries.update(refs)
                            
					# For each of the references found, and edge is
					# created.
					for r in refs:
						# If the flow could also come from the address
						# previous to the destination of the branching
						# an edge is created.
						if isFlow(GetFlags(r)):
							edges.add((PrevHead(r, f_start), r))
						edges.add((head, r))

	return len(edges) - len(boundaries) + 2

    def __init_args_and_local_vars__ (self, funcStruct, frameStruct):
        '''
        Calculate the total size of arguments, # of arguments and # of local variables. Update the internal class member
        variables appropriately. Taken directly from paimei
        '''
        # Initialize some local variables
        args = {}
        local_vars = {} 

        if not frameStruct:
            return

        argument_boundary = self.frameSize 
        frame_offset      = frameStruct.get_member(0).soff


        for i in xrange(0, frameStruct.memqty):
            end_offset = frameStruct.get_member(i).soff

            if i == frameStruct.memqty - 1:
                begin_offset = frameStruct.get_member(i).eoff
            else:
                begin_offset = frameStruct.get_member(i+1).soff

            frame_offset += (begin_offset - end_offset)

            # grab the name of the current local variable or argument.
            name = idaapi.get_member_name(frameStruct.get_member(i).id)
            print("=============================")
            print("Name: %s" % name)
#            print "Agument Boundary: %d" % argument_boundary
#            print "Frame offset: %d" % frame_offset
            print("End offset: %d" % end_offset)
            print("Begin Offset: %d" % begin_offset)
#            print("Frame offset: %d\n" % frame_offset)
            print("=============================")

            if name == None:
                continue

            if frame_offset > argument_boundary:
                args[end_offset] = name
#            if name.startswith("arg_"):
#                args[end_offset] = name
#                self.argSize = self.argSize + (begin_offset - end_offset) 
            else:
                # if the name starts with a space, then ignore it as it is either the stack saved ebp or eip.
                # XXX - this is a pretty ghetto check.
                if not name.startswith(" "):
                    local_vars[end_offset] = name
        self.argSize       = frame_offset - argument_boundary
        self.numArgs       = len(args)
        self.numLocalVars  = len(local_vars)

    def iter_chunks(self):
        chunkBlockCount = 0
        for ch in self.chunkList:
            chunkBlockCount = chunkBlockCount + len(ch.blockList)

        return(chunkBlockCount)

    def collect_function_chunks(self):
        '''
        Generate and return the list of function chunks (including the main one) for the current function. Ripped from idb2reml (Ero Carerra). Modified slightly by Roger Seagle.

        @rtype:  None 
        @return: None 
        '''

        #
        # Loop through all chunks for a function
        #
        iterator = idaapi.func_tail_iterator_t(idaapi.get_func(self.startAddress))
        status   = iterator.main()

        while status:
            chunk = iterator.chunk()
            tmp = Chunk(chunk)
            self.chunkList.append(tmp)
            status = iterator.next()

#
# Create a class for a basic block
#
class Chunk(yaml.YAMLObject):
    yaml_tag = u'!fuzz.io,2011/Chunk'
    def __init__(self, chunk):
        self.startEA = chunk.startEA 
        self.endEA  = chunk.endEA 
        self.blockList = []
        self.numBlocks = 0

        #
        # Just to get it started
        #
        block_start = self.startEA

    #
    # Might be a bug? (effective address that has code mixed in and no ret instruction
    # Or effective address just calls exit (there is no return instruction!!!!)
    #

        #
        # Break down the chunk into blocks
        #
        for effectiveAddress in Heads(self.startEA, self.endEA):

            #
            # Ignore Head if data
            #
            if not isCode(GetFlags(effectiveAddress)):
                continue

            prev_ea = PrevNotTail(effectiveAddress)
            next_ea = NextNotTail(effectiveAddress)

            #
            # Get the list of places branched to and from
            #
            branchesTo   = self._branches_to(effectiveAddress)
            branchesFrom = self._branches_from(effectiveAddress)


            # ensure that both prev_ea and next_ea reference code and not data.
            while not isCode(GetFlags(prev_ea)):
                prev_ea = PrevNotTail(prev_ea)

            while not isCode(GetFlags(next_ea)):
                next_ea = PrevNotTail(next_ea)

            # if the current instruction is a ret instruction, end the current node at ea.
            if idaapi.is_ret_insn(effectiveAddress):
                tmp = Block(block_start, effectiveAddress, branchesTo, branchesFrom)
                self.blockList.append(tmp)
                block_start = next_ea

            elif branchesTo and block_start != effectiveAddress:
                tmp = Block(block_start, effectiveAddress, branchesTo, branchesFrom)
                self.blockList.append(tmp)

                # start a new block at ea.
                block_start = effectiveAddress

            # if there is a branch from the current instruction, end the current node at ea.
            elif branchesFrom:
                tmp = Block(block_start, effectiveAddress, branchesTo, branchesFrom)
                self.blockList.append(tmp)

                # start a new block at the next ea
                block_start = next_ea

        #
        # Calculate the number of blocks
        #
        self.numBlocks = len(self.blockList)

        #
        # Covert addresses to hex
        #
        self.startEA = hex(self.startEA) 
        self.endEA  = hex(self.endEA) 

####################################################################################################################
    def _branches_from (self, ea):
        '''
        Enumerate and return the list of branches from the supplied address, *including* the next logical instruction.
        Part of the reason why we even need this function is that the "flow" argument to CodeRefsFrom does not appear
        to be functional.

        @type  ea: DWORD
        @param ea: Effective address of instruction to enumerate jumps from.

        @rtype:  List
        @return: List of branches from the specified address.
        '''

        if idaapi.is_call_insn(ea):
            return []

        xrefs = list(CodeRefsFrom(ea, 1))

        # if the only xref from ea is next ea, then return nothing.
        if len(xrefs) == 1 and xrefs[0] == NextNotTail(ea):
            xrefs = []

        return xrefs


    ####################################################################################################################
    def _branches_to (self, ea):
        '''
        Enumerate and return the list of branches to the supplied address, *excluding* the previous logical instruction.
        Part of the reason why we even need this function is that the "flow" argument to CodeRefsTo does not appear to
        be functional.

        @type  ea: DWORD
        @param ea: Effective address of instruction to enumerate jumps to.

        @rtype:  List
        @return: List of branches to the specified address.
        '''

        xrefs        = []
        prev_ea      = PrevNotTail(ea)
        prev_code_ea = prev_ea

        while not isCode(GetFlags(prev_code_ea)):
            prev_code_ea = PrevNotTail(prev_code_ea)

        for xref in list(CodeRefsTo(ea, 1)):
            if not idaapi.is_call_insn(xref) and xref not in [prev_ea, prev_code_ea]:
                xrefs.append(hex(xref))

        return xrefs

#
# Create a class for a basic block
#
class Block(yaml.YAMLObject):
    yaml_tag = u'!fuzz.io,2011/Block'
    def __init__(self, effectiveAddressStart, effectiveAddressEnd, branchesTo, branchesFrom): 
        self.startEA = hex(effectiveAddressStart)
        self.endEA = hex(effectiveAddressEnd)
        self.branchTo = branchesTo
        branchFr = []
        		
        #
        # Covert branches to hex addresses
        #
        for i in range(len(branchesFrom)):
            branchFr.append(hex(branchesFrom[i]))

        self.branchFrom = branchFr

        #
        # Get the number of instructions in the block
        #
        heads = [head for head in Heads(effectiveAddressStart, effectiveAddressEnd + 1) if isCode(GetFlags(head))]
        self.numInstructions = len(heads)

# Wait for the analysis to stop
idaapi.autoWait()

# Create the filenames to dump and log
yamlFilename  = os.environ['PWD'] + "/" + GetInputFile() + ".fz" 

# Open the file
yamlFile = open(yamlFilename, 'w')

# Get the start and end of the text section
textSegmentSelector = SegByName("__text")
textSegmentStart = SegByBase(textSegmentSelector)
textSegmentEnd = SegEnd(textSegmentStart)

# Pull out all the information
disassembledObject = Object(textSegmentStart, textSegmentEnd)

# Dump the disassembled Object info in a portable format
yaml.dump(disassembledObject, yamlFile, default_flow_style=False)

# Be nice close the file
yamlFile.close()

# Exit IDA Pro
Exit(0)

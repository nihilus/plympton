module Plympton
	# Class responsible for working with a disassembly
	class Disassembly
		attr_accessor	:attributes
		attr_accessor	:expression

		# Create an instance of the disassembly class
		# Reads in a YAML serialized disassembly
		# @param [String] Path to the YAML serialized disassembly
		# @param [String] A mathematical expression for object evaluation
		def initialize(yamlDisassembly, literalExpression="")

			# Check for existence of the file
			if(!File.exists?(yamlDisassembly)) then
				return(nil)
			end

			# Unserialize the YAML disassembly
			@attributes = YAML.load(File.open(yamlDisassembly))	
			@attributes.setup()

			# Create an instance of the expression
			initialize_solver(literalExpression)
		end

		# Wrapper function for the solver's evaluate function 
		# After expression evaluation it resets for another turn
		# @param [BigDecimal] Test case runtime, defaults to zero
		# @return [BigDecimal] The results of the evaluated expression
		def evaluate(runtime="0")
			@attributes.runtime = BigDecimal(runtime)
			result = @expression.evaluate()
			initialize_solver(@expression.expressionCache)

			# Catch Not A Number or Infinite cases
			if(result.nan?() or result.infinite?()) then
				result = BigDecimal("0")
			end

			return(result)
		end

                # Function to process hit tracing recorded by lldb 
                # @param [String] Path to a lldb trace file
                def lldb_coverage(lldbTrace)
                  # Open the valgrind xml trace file
                  xmlFile = File.open(valgrindTrace, "r")
                  xmlDoc = Nokogiri::XML(xmlFile)

                  # Delete any previous hit traces
                  @attributes.functionHitTrace.clear()

                  # Parse all the function hits 
                  xmlDoc.xpath("//hit").each do |hit|
                    functionOffset = hit.search("offset").first().inner_text()
                    functionOffset = hit.search("count").first().inner_text()

                    if(!@attributes.functionHitTrace.has_key?(functionOffset)) then
                      a = 1
#                      @attributes.functionHitTrace[functionOffset] = [1] 
                    else
                      a = 1
 #                     @attributes.functionHitTrace[functionOffset][0] = @attributes.functionHitTrace[functionOffset][0] + 1 
                    end
                  end

                  # FIXME: Add code to handle the markov matrix

                  # Cleanup open file
                  xmlFile.close()
                end

		# Function to process hit tracing recorded by Valgrind tools (rufus and callgrind)
		# @param [String] Path to a valgrind trace file
		def valgrind_coverage(valgrindTrace)

			# Open the valgrind xml trace file
			xmlFile = File.open(valgrindTrace, "r")
			xmlDoc = Nokogiri::XML(xmlFile)

			# Delete any previous hit traces
			@attributes.functionHitTrace.clear()

			# Parse all the function hits 
			xmlDoc.xpath("//hit").each do |hit|
				functionOffset = hit.search("offset").first().inner_text()
				#puts "Function offset hit: #{functionOffset}"
				if(@attributes.functionHash.has_key?(functionOffset)) then
				#puts "Function offset found: #{functionOffset}"
					if(!@attributes.functionHitTrace.has_key?(functionOffset)) then
						@attributes.functionHitTrace[functionOffset] = [1] 
					else
						@attributes.functionHitTrace[functionOffset][0] = @attributes.functionHitTrace[functionOffset][0] + 1 
					end

					# Parse all the functions this function called
					hit.xpath("callee").each do |callee|
						calleeOffset = callee.search("offset").first().inner_text()
						numberOfCalls = callee.search("numberOfCalls").first().inner_text().to_i()
						if(@attributes.functionHash.has_key?(calleeOffset)) then
							if(!@attributes.functionHitTrace.has_key?(functionOffset)) then
								@attributes.functionHitTrace[functionOffset] = [numberOfCalls] 
							else
								@attributes.functionHitTrace[functionOffset][0] = @attributes.functionHitTrace[functionOffset][0] + numberOfCalls 
							end

							#puts "Function offset: #{functionOffset} -> #{calleeOffset}"
							# Increment the number of transitions for a state
							@attributes.functionHash[functionOffset].numTransitions += BigDecimal("#{numberOfCalls}")

							# Update the transition matrix
							@attributes.transitionMatrix[@attributes.functionHash[functionOffset].markovIdx, @attributes.functionHash[calleeOffset].markovIdx] = @attributes.transitionMatrix[@attributes.functionHash[functionOffset].markovIdx, @attributes.functionHash[calleeOffset].markovIdx] + BigDecimal("#{numberOfCalls}") 

							# Keep track of call trace and number of times called
							@attributes.trace << "#{@attributes.functionHash[functionOffset].markovIdx}:#{@attributes.functionHash[calleeOffset].markovIdx}:#{numberOfCalls}"
						end
					end # end callee xpath
				end # end function hash check for hit function
			end # end hit xpath

			# Cleanup open file
			xmlFile.close()
		end

		# Parses a mathematical expression and setups for function evaluation
		# @param [String] A mathematical expression for object evaluation
		def initialize_solver(literalExpression)
			# Allocate an expression to solve
			@expression = Solver::Parser.new(Solver::Lexer.new(literalExpression))
			@expression.expressionCache = literalExpression
			@expression.objectCache = @attributes
		end
	
	end
end

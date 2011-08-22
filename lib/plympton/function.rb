module Plympton
	# Class responsible for parsing a YAML serialized function object
    class Function
		# YAML Entries
        attr_accessor   :name, :startAddress, :endAddress, :savedRegSize, :localVarSize, :argSize, :numArgs, :numLocalVars, :isImport, :numChunks, :chunkList, :cyclomaticComplexity
		
        attr_accessor   :idx

        # Defines the objects YAML tag
		def to_yaml_type
			"!fuzz.io,2011/Function"
		end
		
        # Convenience method for printing a function 
        # @return [String] A string representation of a function object
		def to_s()
			"#{self.class} (#{self.__id__}):#{name}"
		end
    end
end

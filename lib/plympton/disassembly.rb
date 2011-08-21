module Plympton
	# Class responsible for working with a disassembly
	class Disassembly
		attr_accessor	:attributes

		# @param [String] Path to the YAML serialized disassembly
		def initialize(yamlDisassembly)
			# Check for existence of the file
			if(!File.exists?(yamlDisassembly)) then
				return(nil)
			end

			# Unserialize the YAML disassembly
			@attributes = YAML::load(File.open(yamlDisassembly))	
			#puts @attributes.keys()
			@attributes["name"].chomp!()
		end
	end
end

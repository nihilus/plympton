grammar Solver;

options { 
		language = Ruby;
}

tokens {
	PLUS		= '+';
	MINUS		= '-';
	MULT		= '*';
	DIV			= '/';
	MOD			= '%';
	EXP			= '^';
	LPAREN		= '(';
	RPAREN		= ')';
}

@header {
	require 'bigdecimal/math'
}

@members {
	attr_accessor :expressionCache
	attr_accessor :objectCache

	# Recovery function handling errors 
	def recover( error = $! )
		puts "Parser Recovering: #{error}"
		exit(1)
	end

	# Reporting function handling errors 
	def report_error( error = $! )
		puts "Parser Reporting: #{error}"
		exit(1)
	end
}


@lexer::members {
	# Recovery function handling errors 
	def recover( error = $! )
		puts "Lexer Recovering: #{error}"
		exit(1)
	end

	# Reporting function handling errors 
	def report_error( error = $! )
		puts "Lexer Reporting: #{error}"
		exit(1)
	end
}

/*------------------------------------------------------------------
 * PARSER RULES
 *------------------------------------------------------------------*/
evaluate returns [result] 
			: r=expression {$result = $r.result }
			;
expression returns [result]
  : r=mult
    ( '+' r2=mult { $r.result += $r2.result }
    | '-' r2=mult { $r.result -= $r2.result }
    )* { $result = $r.result }
  ;

mult returns [result]
  : r=log
    ( '*' r2=log { $r.result *= $r2.result }
    | '/' r2=log { $r.result /= $r2.result } 
    )* { $result = $r.result };

log returns [result]
  : 'ln' r=exp { $result = BigMath.log(r, 2)}
  | r=exp { $result = $r.result }
  ;

exp returns [result]
  : r=atom ( '^' r2=atom { $r.result **= $r2.result.to_i() } )? { $result = $r.result }
  ;

atom returns [result] 
			:		(a=INT   {$result = BigDecimal($a.text)}
			|		 a=FLOAT {$result = BigDecimal($a.text)}
			|		 LPAREN r=expression { $result = $r.result } RPAREN
			|		 a=MODVAR	 {
						$result = @objectCache.send($a.text)
			}
			|		 a=UNMODVAR { 
						case $a.text 
							when 'R'
								$result = @objectCache.runtime 
							when 'U'
								$result = @objectCache.send($a.text)
							when 'V'
								$result = @objectCache.send($a.text)
							else
								$result = BigDecimal("0")
							end
					 }
			)
 ;

/*------------------------------------------------------------------
 * LEXER RULES
 *------------------------------------------------------------------*/
INT		   : (DIGIT)+ ;
FLOAT	   : INT '.' INT;
MODVAR	   : 'A'..'G'(MODIFIER); 
UNMODVAR   : ( 'R' | 'U' | 'V' );
WHITESPACE : ( '\t' | ' ' | '\r' | '\n'| '\u000C' )+ { $channel = HIDDEN; };

/*------------------------------------------------------------------
 * Fragment RULES (Only used as part of another Lexer Rule)
 *------------------------------------------------------------------*/

fragment DIGIT : '0'..'9';
fragment MODIFIER: 'a'|'s';

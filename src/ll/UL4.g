grammar UL4;

options
{
	language=Python;
	backtrack=true;
}

@lexer::header
{
	from ll import ul4c
}

@header
{
	import datetime, ast
	from ll import ul4c, color
}

@lexer::members {
def reportError(self, e):
	raise e
}

@members {
def reportError(self, e):
	raise e

def mismatch(self, input, ttype, follow):
	raise MismatchedTokenException(ttype, input)

def recoverFromMismatchedSet(self, input, e, follow):
	raise e

def start(self, token):
	return self.location.startcode + token.start

def end(self, token):
	return self.location.startcode + token.stop + 1
}

@rulecatch {
except RecognitionException as e:
    raise
}

NONE
	: 'None'
	;

TRUE
	: 'True'
	;

FALSE
	: 'False'
	;

NAME
	: ('a'..'z'|'A'..'Z'|'_') ('a'..'z'|'A'..'Z'|'0'..'9'|'_')*
	;

fragment
DIGIT
	: '0'..'9'
	;

fragment
BIN_DIGIT
	: ('0'|'1')
	;

fragment
OCT_DIGIT
	: '0'..'7'
	;

fragment
HEX_DIGIT
	: ('0'..'9'|'a'..'f'|'A'..'F')
	;

/* We don't have negative ints (as this would lex "1-2" wrong) */
INT
	: DIGIT+
	| '0' ('b'|'B') BIN_DIGIT+
	| '0' ('o'|'O') OCT_DIGIT+
	| '0' ('x'|'X') HEX_DIGIT+
	;

fragment
EXPONENT
	: ('e'|'E') ('+'|'-')? DIGIT+
	;

FLOAT
	: DIGIT+ '.' DIGIT* EXPONENT?
	| '.' DIGIT+ EXPONENT?
	| DIGIT+ EXPONENT
	;

fragment
TIME
	: DIGIT DIGIT ':' DIGIT DIGIT ( ':' DIGIT DIGIT ( '.' DIGIT DIGIT DIGIT DIGIT DIGIT DIGIT)?)?;

DATE
	: '@' '(' DIGIT DIGIT DIGIT DIGIT '-' DIGIT DIGIT '-' DIGIT DIGIT ('T' TIME?)? ')';

COLOR
	: '#' HEX_DIGIT HEX_DIGIT HEX_DIGIT
	| '#' HEX_DIGIT HEX_DIGIT HEX_DIGIT HEX_DIGIT
	| '#' HEX_DIGIT HEX_DIGIT HEX_DIGIT HEX_DIGIT HEX_DIGIT HEX_DIGIT
	| '#' HEX_DIGIT HEX_DIGIT HEX_DIGIT HEX_DIGIT HEX_DIGIT HEX_DIGIT HEX_DIGIT HEX_DIGIT
	;

WS
	: (' '|'\t'|'\r'|'\n') { $channel=HIDDEN; }
	;

STRING
	: '"' ( ESC_SEQ | ~('\\'|'"'|'\r'|'\n') )* '"'
	| '\'' ( ESC_SEQ | ~('\\'|'\''|'\r'|'\n') )* '\''
	;

STRING3
	: '"""' (options {greedy=false;}:TRIQUOTE)* '"""'
	|  '\'\'\'' (options {greedy=false;}:TRIAPOS)* '\'\'\''
	;

fragment
TRIQUOTE
	: ('"'|'""')? (ESC_SEQ|~('\\'|'"'))+
	;

fragment
TRIAPOS
	: ('\''|'\'\'')? (ESC_SEQ|~('\\'|'\''))+
	;

fragment
ESC_SEQ
	: '\\' ('a'|'b'|'t'|'n'|'f'|'r'|'\"'|'\''|'\\')
	| UNICODE1_ESC
	| UNICODE2_ESC
	| UNICODE4_ESC
	;

fragment
UNICODE1_ESC
	: '\\' 'x' HEX_DIGIT HEX_DIGIT
	;

fragment
UNICODE2_ESC
	: '\\' 'u' HEX_DIGIT HEX_DIGIT HEX_DIGIT HEX_DIGIT
	;

fragment
UNICODE4_ESC
	: '\\' 'U' HEX_DIGIT HEX_DIGIT HEX_DIGIT HEX_DIGIT HEX_DIGIT HEX_DIGIT HEX_DIGIT HEX_DIGIT
	;

/* Rules common to all tags */

none returns [node]
	: NONE { $node = ul4c.Const(self.location, self.start($NONE), self.end($NONE), None) }
	;

true_ returns [node]
	: TRUE { $node = ul4c.Const(self.location, self.start($TRUE), self.end($TRUE), True) }
	;

false_ returns [node]
	: FALSE { $node = ul4c.Const(self.location, self.start($FALSE), self.end($FALSE), False) }
	;

int_ returns [node]
	: INT { $node = ul4c.Const(self.location, self.start($INT), self.end($INT), int($INT.text, 0)) }
	;

float_ returns [node]
	: FLOAT { $node = ul4c.Const(self.location, self.start($FLOAT), self.end($FLOAT), float($FLOAT.text)) }
	;

string returns [node]
	: STRING { $node = ul4c.Const(self.location, self.start($STRING), self.end($STRING), ast.literal_eval($STRING.text)) }
	| STRING3 { $node = ul4c.Const(self.location, self.start($STRING3), self.end($STRING3), ast.literal_eval($STRING3.text.replace("\r", "\\r"))) }
	;

date returns [node]
	: DATE { $node = ul4c.Const(self.location, self.start($DATE), self.end($DATE), datetime.datetime(*map(int, [f for f in ul4c._datesplitter.split($DATE.text[2:-1]) if f]))) }
	;

color returns [node]
	: COLOR { $node = ul4c.Const(self.location, self.start($COLOR), self.end($COLOR), color.Color.fromrepr($COLOR.text)) }
	;

name returns [node]
	: NAME { $node = ul4c.Var(self.location, self.start($NAME), self.end($NAME), $NAME.text) }
	;

literal returns [node]
	: e_none=none { $node = $e_none.node; }
	| e_false=false_ { $node = $e_false.node; }
	| e_true=true_ { $node = $e_true.node; }
	| e_int=int_ { $node = $e_int.node; }
	| e_float=float_ { $node = $e_float.node; }
	| e_string=string { $node = $e_string.node; }
	| e_date=date { $node = $e_date.node; }
	| e_color=color { $node = $e_color.node; }
	| e_name=name { $node = $e_name.node; }
	;

/* List literals */
list returns [node]
	:
		open='['
		close=']' { $node = ul4c.List(self.location, self.start($open), self.end($close)) }
	|
		open='[' {$node = ul4c.List(self.location, self.start($open), None) }
		e1=expr_or { $node.items.append($e1.node) }
		(
			','
			e2=expr_or { $node.items.append($e2.node) }
		)*
		','?
		close=']' { $node.end = self.end($close) }
	;

listcomprehension returns [node]
	@init
	{
		_condition = None;
	}
	:
		open='['
		item=expr_or
		'for'
		n=nestedlvalue
		'in'
		container=expr_or
		(
			'if'
			condition=expr_or { _condition = $condition.node; }
		)?
		close=']' { $node = ul4c.ListComp(self.location, self.start($open), self.end($close), $item.node, $n.lvalue, $container.node, _condition) }
	;

/* Dict literal */
fragment
dictitem returns [node]
	:
		k=expr_or
		':'
		v=expr_or { $node = ($k.node, $v.node) }
	;

dict returns [node]
	:
		open='{'
		close='}' { $node = ul4c.Dict(self.location, self.start($open), self.end($close)) }
	|
		open='{' { $node = ul4c.Dict(self.location, self.start($open), None) }
		i1=dictitem { $node.items.append($i1.node) }
		(
			','
			i2=dictitem { $node.items.append($i2.node) }
		)*
		','?
		close='}' { $node.end = self.end($close) }
	;

dictcomprehension returns [node]
	@init
	{
		_condition = None;
	}
	:
		open='{'
		key=expr_or
		':'
		value=expr_or
		'for'
		n=nestedlvalue
		'in'
		container=expr_or
		(
			'if'
			condition=expr_or { _condition = $condition.node; }
		)?
		close='}' { $node = ul4c.DictComp(self.location, self.start($open), self.end($close), $key.node, $value.node, $n.lvalue, $container.node, _condition) }
	;

generatorexpression returns [node]
	@init
	{
		_condition = None
		_end = None
	}
	:
		item=expr_or { _start = $item.node.start }
		'for'
		n=nestedlvalue
		'in'
		container=expr_or { _end = $container.node.end }
		(
			'if'
			condition=expr_or { _condition = $condition.node; _end = $condition.node.end }
		)? { $node = ul4c.GenExpr(self.location, $item.node.start, _end, $item.node, $n.lvalue, $container.node, _condition) }
	;

atom returns [node]
	: e_literal=literal { $node = $e_literal.node; }
	| e_list=list { $node = $e_list.node; }
	| e_listcomp=listcomprehension { $node = $e_listcomp.node; }
	| e_dict=dict { $node = $e_dict.node; }
	| e_dictcomp=dictcomprehension { $node = $e_dictcomp.node; }
	| open='(' e_genexpr=generatorexpression close=')' {
		$node = $e_genexpr.node
		$node.start = self.start($open)
		$node.end = self.end($close)
	}
	| open='(' e_bracket=expr_or close=')' {
		$node = $e_bracket.node
		$node.start = self.start($open)
		$node.end = self.end($close)
	}
	;

/* For variable unpacking in assignments and for loops */
nestedlvalue returns [lvalue]
	:
		n=expr_subscript { $lvalue = $n.node; }
	|
		'(' n0=nestedlvalue ',' ')' { $lvalue = ($n0.lvalue,) }
	|
		'('
		n1=nestedlvalue
		','
		n2=nestedlvalue { $lvalue = ($n1.lvalue, $n2.lvalue) }
		(
			','
			n3=nestedlvalue { $lvalue += ($n3.lvalue,) }
		)*
		','?
		')'
	;

/* Function/method call, attribute access, item access, slice access */
expr_subscript returns [node]
	@init
	{
		index1 = None
		index2 = None
		slice = False
	}
	:
		e1=atom { $node = $e1.node; }
		(
			/* Attribute access */
			'.'
			n=name { $node = ul4c.Attr(self.location, $node.start, self.end($n.stop), $node, $n.text) }
		|
			/* Function/method call */
			'(' { $node = ul4c.Call(self.location, $node.start, None, $node) }
			(
				/* No arguments */
			|
				/* "**" argument only */
				'**' rkwargs=exprarg { $node.remkwargs = $rkwargs.node; }
				','?
			|
				/* "*" argument only (and maybe **) */
				'*' rargs=exprarg { $node.remargs = $rargs.node; }
				(
					','
					'**' rkwargs=exprarg { $node.remkwargs = $rkwargs.node; }
				)?
				','?
			|
				/* At least one positional argument */
				a1=exprarg { $node.args.append($a1.node) }
				(
					','
					a2=exprarg { $node.args.append($a2.node) }
				)*
				(
					','
					an3=name '=' av3=exprarg { $node.kwargs.append(($an3.text, $av3.node)) }
				)*
				(
					','
					'*' rargs=exprarg { $node.remargs = $rargs.node; }
				)?
				(
					','
					'**' rkwargs=exprarg { $node.remkwargs = $rkwargs.node; }
				)?
				','?
			|
				/* Keyword arguments only */
				an1=name '=' av1=exprarg { $node.kwargs.append(($an1.text, $av1.node)) }
				(
					','
					an2=name '=' av2=exprarg { $node.kwargs.append(($an2.text, $av2.node)) }
				)*
				(
					','
					'*' rargs=exprarg { $node.remargs = $rargs.node; }
				)?
				(
					','
					'**' rkwargs=exprarg { $node.remkwargs = $rkwargs.node; }
				)?
				','?
			)
			close=')' { $node.end = self.end($close) }
		|
			/* Item/slice access */
			'['
			(
				':'
				(
					e2=expr_or { index2 = $e2.node; }
				)? { $node = ul4c.Slice(self.location, $node.start, None, $node, None, index2) }
			|
				e2=expr_or { index1 = $e2.node; }
				(
					':' { slice = True; }
					(
						e3=expr_or { index2 = $e3.node; }
					)?
				)? { $node = ul4c.Slice(self.location, $node.start, None, $node, index1, index2) if slice else ul4c.Item(self.location, $e1.node.start, None, $node, index1) }
			)
			close=']' { $node.end = self.end($close) }
		)*
	;

/* Negation */
expr_neg returns [node]
	:
		e1=expr_subscript { $node = $e1.node; }
	|
		minus='-' e2=expr_neg { $node = ul4c.Neg.make(self.location, self.start($minus), $e2.node.end, $e2.node) }
	;

/* Multiplication, division, modulo */
expr_mul returns [node]
	:
		e1=expr_neg { $node = $e1.node; }
		(
			(
				'*' { cls = ul4c.Mul; }
			|
				'/' { cls = ul4c.TrueDiv; }
			|
				'//' { cls = ul4c.FloorDiv; }
			|
				'%' { cls = ul4c.Mod; }
			)
			e2=expr_neg { $node = cls.make(self.location, $node.start, $e2.node.end, $node, $e2.node) }
		)*
	;

/* Addition, substraction */
expr_add returns [node]
	:
		e1=expr_mul { $node = $e1.node; }
		(
			(
				'+' { cls = ul4c.Add; }
			|
				'-' { cls = ul4c.Sub; }
			)
			e2=expr_mul { $node = cls.make(self.location, $node.start, $e2.node.end, $node, $e2.node) }
		)*
	;

/* Comparisons */
expr_cmp returns [node]
	:
		e1=expr_add { $node = $e1.node; }
		(
			(
				'==' { cls = ul4c.EQ; }
			|
				'!=' { cls = ul4c.NE; }
			|
				'<' { cls = ul4c.LT; }
			|
				'<=' { cls = ul4c.LE; }
			|
				'>' { cls = ul4c.GT; }
			|
				'>=' { cls = ul4c.GE; }
			)
			e2=expr_add { $node = cls.make(self.location, $node.start, $e2.node.end, $node, $e2.node) }
		)*
	;

/* "in"/"not in" operator */
expr_contain returns [node]
	:
		e1=expr_cmp { $node = $e1.node }
		(
			{ cls = ul4c.Contains }
			(
				'not' { cls = ul4c.NotContains }
			)?
			'in'
			e2=expr_cmp { $node = cls.make(self.location, $node.start, $e2.node.end, $node, $e2.node) }
		)?
	;

/* Not operator */
expr_not returns [node]
	:
		e1=expr_contain { $node = $e1.node; }
	|
		n='not' e2=expr_not { $node = ul4c.Not.make(self.location, self.start($n), $e2.node.end, $e2.node) }
	;


/* And operator */
expr_and returns [node]
	:
		e1=expr_not { $node = $e1.node; }
		(
			'and'
			e2=expr_not { $node = ul4c.And(self.location, $node.start, $e2.node.end, $node, $e2.node) }
		)*
	;

/* Or operator */
expr_or returns [node]
	:
		e1=expr_and { $node = $e1.node; }
		(
			'or'
			e2=expr_and { $node = ul4c.Or(self.location, $node.start, $e2.node.end, $node, $e2.node) }
		)*
	;

exprarg returns [node]
	: ege=generatorexpression { $node = $ege.node; }
	| e1=expr_or { $node = $e1.node; }
	;

expression returns [node]
	: ege=generatorexpression EOF { $node = $ege.node; }
	| e=expr_or EOF { $node = $e.node; }
	;


/* Additional rules for "for" tag */

for_ returns [node]
	:
		n=nestedlvalue
		'in'
		e=expr_or { $node = ul4c.For(self.location, self.start($n.start), $e.node.end, $n.lvalue, $e.node) }
		EOF
	;


/* Additional rules for "code" tag */

statement returns [node]
	: nn=nestedlvalue '=' e=expr_or EOF { $node = ul4c.SetVar(self.location, self.start($nn.start), $e.node.end, $nn.lvalue, $e.node) }
	| n=expr_subscript '+=' e=expr_or EOF { $node = ul4c.AddVar(self.location, self.start($n.start), $e.node.end, $n.node, $e.node) }
	| n=expr_subscript '-=' e=expr_or EOF { $node = ul4c.SubVar(self.location, self.start($n.start), $e.node.end, $n.node, $e.node) }
	| n=expr_subscript '*=' e=expr_or EOF { $node = ul4c.MulVar(self.location, self.start($n.start), $e.node.end, $n.node, $e.node) }
	| n=expr_subscript '/=' e=expr_or EOF { $node = ul4c.TrueDivVar(self.location, self.start($n.start), $e.node.end, $n.node, $e.node) }
	| n=expr_subscript '//=' e=expr_or EOF { $node = ul4c.FloorDivVar(self.location, self.start($n.start), $e.node.end, $n.node, $e.node) }
	| n=expr_subscript '%=' e=expr_or EOF { $node = ul4c.ModVar(self.location, self.start($n.start), $e.node.end, $n.node, $e.node) }
	| e=expression EOF { $node = $e.node }
	;

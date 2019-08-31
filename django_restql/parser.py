import re
from pypeg2 import name, csl, List, parse, word, optional


class Field():
    grammar = name()


class Argument(List):
    grammar = name(), ":", word
    
    @property
    def value(self):
        return self.pop()


class Arguments(List):
    grammar = optional('(', csl(Argument, separator=','),  ')')


class FirstArgs(Arguments):
    pass


class CallList(List):
    grammar = csl(Field, separator='.')


class Call(List):
    def names(self):
        return self[0]

    def arguments(self):
        return self[1]

    def body(self):
        return self[2]


class Block(List):
    grammar = '{', csl([Call, Field], separator=','), '}'


Call.grammar = CallList, Arguments, Block


class Parser(object):
    def __init__(self, query):
        self._query = query
        self._arguments = {}

    def get_parsed(self):
        parsed = parse(self._query, (FirstArgs, Block))
        self._arguments = {}  # Reset arguments
        return self._transform(parsed)

    def _transform(self, parsed):
        for element in parsed:
            if isinstance(element, Block):
                fields = self._transform_block(element)
            elif isinstance(element, FirstArgs):
                for arg in element:
                    self._arguments.update({str(arg.name) : arg.value})
            else:
                pass

        return {
            "fields": fields,
            "arguments": {**self._arguments}
        }
    
    def _transform_block(self, block):
        return [self._transform_child(child) for child in block]
    
    def _transform_child(self, child):
        # Is it a field name or a call?
        if isinstance(child, Call):
            return self._transform_call(child)
        else:
            return str(child.name)
    
    def _transform_call(self, call, prefix=[]):
        field_name = str(call.names()[0].name)
        prefix.append(field_name)
        prefix_str = "__".join(prefix)
        arguments = call.arguments()
        
        for arg in arguments:
            arg_name = prefix_str + "__" + arg.name
            self._arguments.update({arg_name: arg.value})
            
        return {
            field_name: self._transform_block(call.body())
        }

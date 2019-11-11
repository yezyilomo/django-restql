from pypeg2 import name, csl, List, parse, optional


class Field():
    grammar = name()


class CallList(List):
    grammar = csl(Field, separator='.')


class Call(List):
    def names(self):
        return self[0]

    def body(self):
        return self[1]
        

class Block(List):
    grammar = '{', optional(csl([Call, Field], separator=',')), '}'


Call.grammar = CallList, Block


class Parser(object):
    def __init__(self, query):
        self._query = query

    def get_parsed(self):
        parsed = parse(self._query, Block)
        return self._transform_block(parsed)

    def get_dict(self, data=None):
        """
        Returns the RestQL query as a dict.
        """
        keys = {}
        if not data:
            data = self.get_parsed()

        for item in data:
            if isinstance(item, str):
                keys[item] = None
            elif isinstance(item, dict):
                for key, nested_items in item.items():
                    key_base = key
                    nested_keys = self.get_dict(nested_items)
                    keys[key_base] = nested_keys

        return keys

    def _transform_block(self, block):
        return [self._transform_child(child) for child in block]
    
    def _transform_child(self, child):
        # Is it a field name or a call?
        if isinstance(child, Call):
            return self._transform_call(child)
        else:
            return str(child.name)
    
    def _transform_call(self, call):
        field_name = str(call.names()[0].name)

        return {
            field_name: self._transform_block(call.body())
        }

from pypeg2 import name, csl, List, parse, optional, contiguous

from .exceptions import QueryFormatError


class IncludedField(List):
    grammar = name()


class ExcludedField(List):
    grammar = contiguous('-', name())


class AllFields(str):
    grammar = '*'


class ParentField(List):
    """
    According to ParentField grammar:
    self[0]  returns IncludedField instance,
    self[1]  returns Block instance
    """
    @property
    def name(self):
        return self[0].name

    @property
    def block(self):
        return self[1]


class BlockBody(List):
    grammar = optional(csl(
        [ParentField, IncludedField, ExcludedField, AllFields], 
        separator=','
    ))


class Block(List):
    grammar = '{', BlockBody, '}'

    @property
    def body(self):
        return self[0]


# ParentField grammar,
# We don't include `ExcludedField` here because
# exclude operator(-) on a parent field should 
# raise syntax error, e.g {name, -location{city}}
# IncludeField is a parent field and Block contains sub children
ParentField.grammar = IncludedField, Block


class Parser(object):
    def __init__(self, query):
        self._query = query

    def get_parsed(self):
        parse_tree = parse(self._query, Block)
        return self._transform_block(parse_tree)
    
    def _transform_block(self, block):
        fields = {
            "include": [],
            "exclude": []
        }

        for item in block.body:
            # A child may be a parent or included field or excluded field
            child = self._transform_child(item)
            if isinstance(child, dict):
                # A child is a parent
                fields["include"].append(child)
            elif isinstance(child, IncludedField):
                fields["include"].append(str(child.name))
            elif isinstance(child, ExcludedField):
                fields["exclude"].append(str(child.name))
            elif isinstance(child, AllFields):
                # include all fields
                fields["include"].append("*")

        if fields["exclude"]:
            # fields['include'] should contain only nested fields

            # We should add `*`` operator in fields['include']
            add_include_all_operator = True
            for field in fields["include"]:
                if field == "*":
                    # `*`` operator is alredy in fields['include']
                    add_include_all_operator = False
                    continue

                if isinstance(field, str):
                    # Including and excluding fields on the same field level
                    msg = (
                        "Can not include and exclude fields on the same "
                        "field level"
                    )
                    raise QueryFormatError(msg)
                    
            if add_include_all_operator:
                # Make sure we include * operator
                fields["include"].append("*")
        return fields
    
    def _transform_child(self, child):
        # A child may be a parent or included field or excluded field
        if isinstance(child, ParentField):
            # A child is a parent
            return self._transform_parent(child)
        elif isinstance(child, (IncludedField, ExcludedField, AllFields)):
            return child
    
    def _transform_parent(self, parent):
        parent_name = str(parent.name)

        return {
            parent_name: self._transform_block(parent.block)
        }

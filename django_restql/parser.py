from pypeg2 import name, csl, List, parse, optional, contiguous


class IncludedField(List):
    grammar = name()


class ExcludedField(List):
    grammar = contiguous('-', name())


class ParentField(List):
    """
    According to ParentField grammar:
    self[0]  returns IncludedField,
    self[1]  returns Block
    """
    @property
    def name(self):
        return self[0].name

    @property
    def block(self):
        return self[1]


# A block which contains IncludedField and ParentField only
include_block = optional(csl([ParentField, IncludedField], separator=','))

# A block which contains ExcludedField and ParentField only
exclude_block = optional(csl([ParentField, ExcludedField], separator=','))


class Block(List):
    # A block with either `include_block` or `exclude_block` 
    # features but not both
    grammar = '{', include_block, exclude_block, '}'


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
    
    def _transform_block(self, blocks):
        fields = {
            "include": [],
            "exclude": []
        }
        for block in blocks:
            # A child may be a parent or included field or excluded field
            child = self._transform_child(block)
            if isinstance(child, dict):
                # A child is a parent
                fields["include"].append(child)
            elif isinstance(child, IncludedField):
                # A child is an instance of `IncludedField`
                fields["include"].append(str(child.name))
            elif isinstance(child, ExcludedField):
                # A child is an instance of `ExcludedField`
                fields["exclude"].append(str(child.name))
        return fields
    
    def _transform_child(self, child):
        # A child may be a parent or included field or excluded field
        if isinstance(child, ParentField):
            # A child is a parent
            return self._transform_parent(child)
        elif isinstance(child, (IncludedField, ExcludedField)):
            # A child is an instance of `IncludedField` or `ExcludedField`
            return child
    
    def _transform_parent(self, parent):
        parent_name = str(parent.name)

        return {
            parent_name: self._transform_block(parent.block)
        }

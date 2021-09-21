import re
from collections import namedtuple

from pypeg2 import List, contiguous, csl, name, optional, parse

from .exceptions import QueryFormatError


class Alias(List):
    grammar = name(), ':'


class IncludedField(List):
    grammar = optional(Alias), name()

    @property
    def alias(self):
        if len(self) > 0:
            return self[0].name
        return None


class ExcludedField(List):
    grammar = contiguous('-', name())


class AllFields(str):
    grammar = '*'


class ArgumentWithoutQuotes(List):
    grammar = name(), ':', re.compile(r'true|false|null|[-+]?[0-9]*\.?[0-9]+')

    def number(self, val):
        try:
            return int(val)
        except ValueError:
            return float(val)

    @property
    def value(self):
        raw_val = self[0]
        FIXED_DATA_TYPES = {
            'true': True,
            'false': False,
            'null': None
        }
        if raw_val in FIXED_DATA_TYPES:
            return FIXED_DATA_TYPES[raw_val]
        return self.number(raw_val)


class ArgumentWithQuotes(List):
    grammar = name(), ':', re.compile(r'"([^"\\]|\\.|\\\n)*"|\'([^\'\\]|\\.|\\\n)*\'')

    @property
    def value(self):
        # Slicing is for removing quotes
        # at the begining and end of a string
        return self[0][1:-1]


class Arguments(List):
    grammar = optional(csl(
        [
            ArgumentWithoutQuotes,
            ArgumentWithQuotes,
        ],
        separator=[',', '']
    ))


class ArgumentsBlock(List):
    grammar = optional('(', Arguments, optional(','), ')')

    @property
    def arguments(self):
        if self[0] is None:
            return []  # No arguments
        return self[0]


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
    def alias(self):
        return self[0].alias

    @property
    def block(self):
        return self[1]


class BlockBody(List):
    grammar = optional(csl(
        [ParentField, IncludedField, ExcludedField, AllFields],
        separator=[',', '']
    ))


class Block(List):
    grammar = ArgumentsBlock, '{', BlockBody, optional(','), '}'

    @property
    def arguments(self):
        return self[0].arguments

    @property
    def body(self):
        return self[1]


# ParentField grammar,
# We don't include `ExcludedField` here because
# exclude operator(-) on a parent field should
# raise syntax error, e.g {name, -location{city}}
# `IncludedField` is a parent field and `Block`
# contains its sub fields
ParentField.grammar = IncludedField, Block


Query = namedtuple(
    "Query",
    ("field_name", "included_fields", "excluded_fields", "aliases", "arguments")
)


class QueryParser(object):
    def parse(self, query):
        parse_tree = parse(query, Block)
        return self._transform_block(parse_tree, parent_field=None)

    def _transform_block(self, block, parent_field=None):
        query = Query(
            field_name=parent_field,
            included_fields=[],
            excluded_fields=[],
            aliases={},
            arguments={}
        )

        for argument in block.arguments:
            argument = {str(argument.name): argument.value}
            query.arguments.update(argument)

        for field in block.body:
            # A field may be a parent or included field or excluded field
            if isinstance(field, (ParentField, IncludedField)):
                # Find all aliases
                if field.alias:
                    query.aliases.update({str(field.name): str(field.alias)})

            field = self._transform_field(field)

            if isinstance(field, Query):
                # A field is a parent
                query.included_fields.append(field)
            elif isinstance(field, IncludedField):
                query.included_fields.append(str(field.name))
            elif isinstance(field, ExcludedField):
                query.excluded_fields.append(str(field.name))
            elif isinstance(field, AllFields):
                # include all fields
                query.included_fields.append("*")

        if query.excluded_fields and "*" not in query.included_fields:
            query.included_fields.append("*")

        field_names = set(query.aliases.values())
        field_aliases = set(query.aliases.keys())
        faulty_fields = field_names.intersection(field_aliases)
        if faulty_fields:
            # We check this here because if we let it pass during
            # parsing it's going to raise inappropriate error message
            # when checking fields availability(for the case of renamed parents)
            msg = (
                "You have either "
                "used an existing field name as an alias to another field or "  # e.g {id, id: course{}}
                "you have defined an alias with the same name as a field name."  # e.g {id: id}
                "The list of fields which led to this error is %s."
            ) % str(list(faulty_fields))
            raise QueryFormatError(msg)
        return query

    def _transform_field(self, field):
        # A field may be a parent or included field or excluded field
        if isinstance(field, ParentField):
            return self._transform_parent_field(field)
        return field

    def _transform_parent_field(self, parent_field):
        return self._transform_block(
            parent_field.block,
            parent_field=str(parent_field.name)
        )

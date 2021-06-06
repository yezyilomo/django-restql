import re

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


class BaseArgument(List):
    @property
    def value(self):
        try:
            return self[0]
        except IndexError:
            return ""


class ArgumentWithoutQuotes(BaseArgument):
    grammar = name(), ':', re.compile(r'[^,:"\'\)]+')


class ArgumentWithSingleQuotes(BaseArgument):
    grammar = name(), ':', "'", optional(re.compile(r'[^\']+')), "'"


class ArgumentWithDoubleQuotes(BaseArgument):
    grammar = name(), ':', '"', optional(re.compile(r'[^"]+')), '"'


class Arguments(List):
    grammar = optional(csl(
        [
            ArgumentWithoutQuotes,
            ArgumentWithSingleQuotes,
            ArgumentWithDoubleQuotes
        ],
        separator=','
    ))


class ArgumentsBlock(List):
    grammar = optional('(', Arguments, ')')

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
        separator=','
    ))


class Block(List):
    grammar = ArgumentsBlock, '{', BlockBody, '}'

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


class QueryParser(object):
    def parse(self, query):
        parse_tree = parse(query, Block)
        return self._transform_block(parse_tree)

    def _transform_block(self, block):
        fields = {
            "include": [],
            "exclude": [],
            "arguments": {},
            "aliases": {},
        }

        for argument in block.arguments:
            argument = {str(argument.name): argument.value}
            fields['arguments'].update(argument)

        for field in block.body:
            # A field may be a parent or included field or excluded field
            if isinstance(field, (ParentField, IncludedField)):
                # Find all aliases
                if field.alias:
                    fields["aliases"].update({str(field.name): str(field.alias)})

            field = self._transform_field(field)

            if isinstance(field, dict):
                # A field is a parent
                fields["include"].append(field)
            elif isinstance(field, IncludedField):
                fields["include"].append(str(field.name))
            elif isinstance(field, ExcludedField):
                fields["exclude"].append(str(field.name))
            elif isinstance(field, AllFields):
                # include all fields
                fields["include"].append("*")

        if fields["exclude"] and "*" not in fields["include"]:
            fields["include"].append("*")

        field_names = set(fields["aliases"].values())
        field_aliases = set(fields["aliases"].keys())
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
        return fields

    def _transform_field(self, field):
        # A field may be a parent or included field or excluded field
        if isinstance(field, ParentField):
            return self._transform_parent_field(field)
        return field

    def _transform_parent_field(self, parent_field):
        parent_field_name = str(parent_field.name)
        parent_field_value = self._transform_block(parent_field.block)
        return {parent_field_name: parent_field_value}

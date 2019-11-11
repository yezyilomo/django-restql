from django.db.models import Prefetch


def get_all_dict_values(dict_to_parse):
    """
    Helper function to get *all* values from a dict and it's nested dicts.
    """
    values = []

    for value in dict_to_parse.values():
        if isinstance(value, dict):
            values.extend(get_all_dict_values(value))
        else:
            values.append(value)

    return values


def get_mapping_values(parsed, mapping):
    """
    Returns the mapping value (or nested mapping values as needed) of a particular parsed dict
    against the mapping provided. Parsed input expected to come from get_dict from the parser.
    """
    values = []

    for parsed_key, parsed_value in parsed.items():
        if parsed_key in mapping.keys():
            mapping_value = mapping[parsed_key]

            if isinstance(mapping_value, dict):
                base = mapping_value.get("base")
                nested = mapping_value.get("nested")
            else:
                base = mapping_value
                nested = None

            # This should never be a falsy value, but we're being safe here.
            if base:
                values.append(base)

            if nested:
                # If we're given a dict, we only want keys that were mapped as needed, so
                # recursively call with the smaller map.
                if isinstance(parsed_value, dict):
                    nested_values = get_mapping_values(parsed_value, nested)
                    values.extend(nested_values)
                else:
                    # If we don't have a dict, we want every nested value, since it's assumed
                    # all of them will be present. We recursively get all values from here.
                    nested_values = get_all_dict_values(nested)
                    values.extend(nested_values)
    return values


def apply_restql_orm_mapping(queryset, parsed_keys, mapping):
    """
    Applies appropriate select_related and prefetch_related calls on a
    queryset based on the passed on dictionaries provided.
    """
    if mapping:
        select = mapping.get("select", {})
        prefetch = mapping.get("prefetch", {})

        select_mapped = get_mapping_values(parsed_keys, select)
        prefetch_mapped = get_mapping_values(parsed_keys, prefetch)

        for value in select_mapped:
            if isinstance(value, str):
                queryset = queryset.select_related(value)
            elif isinstance(value, list):
                for select_value in value:
                    queryset = queryset.select_related(select_value)

        for value in prefetch_mapped:
            if isinstance(value, str) or isinstance(value, Prefetch):
                queryset = queryset.prefetch_related(value)
            elif isinstance(value, list):
                for prefetch_value in value:
                    queryset = queryset.prefetch_related(prefetch_value)

    return queryset

import unittest
import pyparsing as pp
from fnmatch import fnmatch
ppc = pp.pyparsing_common


# LDAP style filter (RFC4515)
BOOLEAN = pp.oneOf('true True yes false False no').setParseAction(
    pp.tokenMap(lambda token: token in ('true', 'True', 'yes')))

EQ, ASTERISK = map(pp.Literal, "=*")
LPAREN, RPAREN, COLON = map(pp.Suppress, "():")

ASSERTION_VALUE = pp.quotedString | ppc.number | BOOLEAN
ATTR = ppc.identifier | ASTERISK
MATCHING_RULE = COLON + ppc.identifier
FILTER_TYPE = pp.MatchFirst(map(pp.Literal, ('>', '>=', '<', '<=', '!=', '=', '~=')))

SIMPLE = (ATTR + FILTER_TYPE + ASSERTION_VALUE)('simple')
# PRESENT = ATTR + EQ + ASTERISK
# ABSENT = ATTR + EQ + pp.Empty()
# EXTENSIBLE = ATTR + MATCHING_RULE + COLON + EQ + ASSERTION_VALUE

ITEM = SIMPLE
# TODO: backlog
# ITEM = SIMPLE | EXTENSIBLE | PRESENT | ABSENT

FILTER = pp.Forward()
FILTER_LIST = FILTER[1, ...]
FILTER_COMP = pp.Group(((pp.oneOf('& |') + FILTER_LIST) | (pp.Literal('!') + FILTER))('comp') | ITEM)
FILTER <<= (LPAREN + FILTER_COMP + RPAREN)('filter')


def parse_ldap_filter(expr) -> pp.ParseResults:
    return FILTER.parseString(expr)


def default_object_get_value(obj, attr=None):
    if attr is None:
        return []
    getattr(obj, attr)


def default_dict_get_value(d: dict, key=None):
    if key is None:
        return []
    return d.get(key)


def eval_ldap_filter(ast: pp.ParseResults, obj, get_value=default_object_get_value):
    def partial_eval_filter(_ast):
        return eval_ldap_filter(_ast, obj, get_value)

    name = ast.getName()
    if 'filter' == name:
        return partial_eval_filter(ast[0])
    if 'comp' == name:
        if '&' == ast[0]:
            return all(map(partial_eval_filter, ast[1:]))
        if '|' == ast[0]:
            return any(map(partial_eval_filter, ast[1:]))
        if '!' == ast[0]:
            return not partial_eval_filter(ast[1])
    if 'simple' == name:
        return _eval_simple(ast, obj, get_value)
    raise ValueError('Invalid Syntax!')


def create_ldap_filter_fn(expr, get_value=default_object_get_value):
    parsed_filter = parse_ldap_filter(expr)
    return lambda obj: eval_ldap_filter(parsed_filter, obj, get_value)


def _eval_simple(ast, obj, get_value):
    attr, op, assertion_value = ast
    value = get_value(obj, attr)
    if value is None:
        return False
    assertion_value = _unescape_assertion_value(assertion_value)
    return {
        '>': lambda a, b: a > b,
        '>=': lambda a, b: a >= b,
        '<': lambda a, b: a < b,
        '<=': lambda a, b: a <= b,
        '!=': lambda a, b: a != b,
        '=': lambda a, b: a == b,
        '~=': fnmatch,
    }[op](value, assertion_value)


def _unescape_assertion_value(value):
    if isinstance(value, str):
        return value.strip(value[0]).replace('\\', '')
    return value


class TestFilter(unittest.TestCase):

    def test_ldap_filter(self):
        obj = {
            'title': 'Chrome Browser',
            'role': 'window',
            'hidden': True,
        }
        exprs = [
            '(title="Chrome Browser")',
            '(hidden=true)',
            '(hidden=yes)',
            '(title~="Chrome*")',
            '(&(title~="Chrome*")(role="window"))',
            '(&(title~="Chrome*")(role!="menu"))',
        ]
        for expr in exprs:
            filter_fn = create_ldap_filter_fn(expr, default_dict_get_value)
            self.assertTrue(filter_fn(obj))

        exprs = [
            '(title="Chrome")',
            '(hidden=false)',
            '(hidden=false)',
            '(hidden=no)',
            '(!(title~="Chrome*"))',
        ]
        for expr in exprs:
            filter_fn = create_ldap_filter_fn(expr, default_dict_get_value)
            self.assertFalse(filter_fn(obj))


if __name__ == '__main__':
    unittest.main()

""" bacula_parse
Parse the output of `bareos-dir -xc`, `bareos-sd -xc` or `bareos-fd -xc` and transform the data,
using lark-parser, into python's dictionary format.
"""
import pprint
import re
from lark import Lark
from lark import Transformer
from collections import defaultdict
from subprocess import Popen, PIPE

from helputils.core import format_exception


def preprocess_config(daemon, hn=False):
    """Parse bareos-dir, bareos-sd or bareos-fd config and return as dictionary"""
    cmd = ("%s -xc" % daemon).split()
    if hn:
        cmd = ["ssh", "-tt", hn] + cmd
    p1 = Popen(cmd, stdout=PIPE)
    try:
        text2 = p1.communicate()[0].decode("UTF-8")
    except Exception as e:
        print(format_exception(e))
        print("""\n---------\n
Failed to decode config. Try `bareos-dir -xc`, `bareos-fd -xc`, `bareos-sd -xc`
manually. There could be an error in your bareos config.
---------\n
""")
        return None
    # Remove spaces
    text2 = "{".join(list(filter(None, [x.strip(" ") for x in text2.split("{")])))
    text2 = "}".join(list(filter(None, [x.strip(" ") for x in text2.split("}")])))
    text2 = "\n".join(list(filter(None, [x.strip() for x in text2.split("\n")])))
    # Add quotes and remove lines containing commas or multiple equal signs
    quote_open = False
    text3 = list()
    unescaped_quotes = r'(?<!\\)(?:\\\\)*"'
    has_comma = r'(,)(?=(?:[^"]|"[^"]*")*$)'
    for line in text2.split("\n"):
        if "=" in line or quote_open:
            if not quote_open:
                # Split only on first equal sign occurence
                directive = line.split("=", 1)
                directive_name = directive[0]
                directive_value = directive[1]
            else:
                directive_value += " %s" % line
            # Omit Lines with Comma
            comma_count = len(re.findall(has_comma, line))
            if not quote_open and comma_count != 0:
                continue
            # Omit Lines with multiple equal signs
            equal_count = line.count("=")
            if equal_count >= 2 and not quote_open:
                continue
            else:
                quote_count = len(re.findall(unescaped_quotes, line))
                directive_name = directive_name.strip()
                directive_value = directive_value.strip()
                if quote_count == 2:
                    # quote_count implies that directive_name has no quotes
                    line = "\"%s\" = %s" % (directive_name, directive_value)
                elif quote_count == 0 and not quote_open:
                    directive_value = directive_value.strip()
                    line = "\"%s\" = \"%s\"" % (directive_name, directive_value)
                elif quote_count == 0 and quote_open:
                    continue
                elif quote_count == 1 and quote_open:
                    quote_open = False
                    directive_value = directive_value.strip()
                    line = "\"%s\" = %s" % (directive_name, directive_value)
                elif quote_count == 1 and not quote_open:
                    quote_open = True
                    continue
        text3.append(line)

    # Add Quotes to Resource type
    text4 = list()
    for line in text3:
        if "{" in line:
            left, right = line.split("{")
            left = "\"%s\"" % left
            line = left + "{"
        text4.append(line)

    # Put it back into a string and standardize last character by adding a newline in the end
    text4 = "\n".join(text4)
    if text4[-1] != "\n":
        text4 += "\n"
    return text4

class MyTransformer(Transformer):

    def string(self, items):
        return "".join(items)

    def resource(self, items):
        resource_type = items[0].strip('"')
        directives = items[1:]
        for directive in directives:
            if not directive:
                continue            
            for name, value in directive.items():
                if name.lower() == "name":
                    resource_name = value
        try:
            resource_name
        except:
            return None
        resource_dict = defaultdict(lambda: defaultdict(defaultdict))
        for directive in directives:
            if not directive:
                continue
            for directive, value in directive.items():
                resource_dict[resource_name][directive] = value
        return {resource_type: resource_dict}

    def resources(self, items):
        _dict = defaultdict(list)
        _dict = defaultdict(lambda: defaultdict(defaultdict))
        for d in items:
            for k1, v1 in d.items():
                # k1 resource_type e.g. Clients
                for k2, v2 in v1.items():
                    name = d[k1][k2]["Name"]
                    _dict[k1][k2] = v2
        return _dict
 
    def directive(self, items):
        items2 = list()
        for x in items:
            items2.append(x.strip('"'))
        return {items2[0]: items2[1]}


def bacula_parse(daemon="bareos-dir", hn=False):
    # Parse the preprocessed config with lark-parser
    parser = Lark(r"""
        ?value: resources
              | resource
              | directive
              | string
        string    : ESCAPED_STRING
        resource  : (string "{" "\n" (directive|resource)* "}" "\n")
        resources : resource*
        directive : string " " "=" " " string "\n"

        %import common.ESCAPED_STRING
        %import common.WORD
        %import common.WS
    """, start='value')
    config = preprocess_config(daemon, hn)
    if not config:
        return None
    tree = parser.parse(config)
    trans = MyTransformer().transform(tree)
    # pp = pprint.PrettyPrinter(indent=4)
    # pp.pprint(trans)
    return trans
    # print(trans["Client"]["phpc01lin-fd"])

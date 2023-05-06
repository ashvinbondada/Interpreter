from bparser import BParser
from intbase import InterpreterBase as IB
import operator


class Interpreter(IB):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   

    
    def run(self, program):
        # parse the program into a more easily processed form
        result, self.parsed_program = BParser.parse(program)
        if result == False:
            return # error
        self.__discover_all_classes_and_track_them(self.parsed_program)
        class_def = self.__find_definition_for_class(IB.MAIN_CLASS_DEF)
        obj = class_def.instantiate_object()
        res = obj.call_method(IB.MAIN_FUNC_DEF, [])

    def __discover_all_classes_and_track_them(self, parsed_program):
        self.classes = {parsed_program[i][1]:parsed_program[i][2:] for i in range(len(parsed_program))}
        # map of class name to entire definition in list form
        # can refer to this if a class does exist or not.
        return

    def __find_definition_for_class(self,class_name):
        def_list = self.classes[class_name]

        fields = []
        methods = []
        for field_or_method in def_list:
            # if field or name == IB.MAIN_CLASS_DEF -> undefined 
            if field_or_method[0] == IB.FIELD_DEF: fields.append(field_or_method)
            else: methods.append(field_or_method)
        if not methods: raise Exception # Each class must have one method
        return ClassDefinition(fields=fields, methods=methods, interpreter = self)

    # def print_line_nums(self, parsed_program):
    #     for item in parsed_program:
    #         if type(item) is not list:
    #             print(f'{item} was found on line {item.line_num}')
    #         else:
    #             self.print_line_nums(item)



#

class ClassDefinition:
# constructor for a ClassDefinition 
    def __init__(self, fields, methods, interpreter):
       self.my_methods = methods 
       self.my_fields = fields
       self.interpreter = interpreter

    # uses the definition of a class to create and return an instance of it
    def instantiate_object(self):
        obj = ObjectDefinition(self.interpreter)
        for method in self.my_methods:
            obj.add_method(method)
        for field in self.my_fields:
            obj.add_field(field[1], field[2])
        return obj
#
class ObjectDefinition: 
    def __init__(self, interpreter):
        self.interpreter = interpreter
        self.method_defs = {}
        self.field_defs = {}
        self.method_params = {}
        self.what_method = ""
        self.end = False
        self.operators = {'+' : (operator.add, False), '-' : (operator.sub, False),'*' : (operator.mul, False), 
                            '/' : (operator.truediv, False),'%' : (operator.mod, False), '>' : (operator.gt, True),
                            '<' : (operator.lt, True),'>=' : (operator.ge, True), '<=' : (operator.le, True),
                            '==' :(operator.eq, True), '!' : (operator.not_, True), '!=' : (operator.ne, True),
                            '&' : (operator.and_, True) ,'|' : (operator.or_, True), 'true' : (True, True), 'false' : (False, True),
                            'null' : (None, type(None))}

    # Interpret the specified method using the provided parameters
    def call_method(self, method_name, parameters):
        method_params, statement = self.__find_method(method_name)
        self.what_method = method_name
        if self.what_method not in list(self.method_params.keys()):
            self.method_params[self.what_method] = {}
        #converting statement list of lists in to just a list.
        if len(method_params) != len(parameters):
            IB.error(self.interpreter,'ErrorType.TYPE_ERROR')
        else:
            for i in range(len(parameters)):
                self.method_params[self.what_method][method_params[i]] = (parameters[i], type(parameters[i]))  
        result = self.__run_statement(statement[0])
        return result
    
    def __find_method(self,method_name):
        if method_name in list(self.method_defs.keys()):
            return self.method_defs[method_name] #1 represents the method itself
        else:
            IB.error(self.interpreter, 'ErrorType.NAME_ERROR')

    def add_method(self, method):
        #name -> params, statement
        if method[1] in list(self.method_defs.keys()):
            IB.error(self.interpreter, 'ErrorType.NAME_ERROR') 
        self.method_defs[method[1]] = (method[2], method[3:]) 
        return
    
    def add_field(self, name, initial_value):
        res = self.__format_values(initial_value)
        if name in list(self.field_defs.keys()):
            IB.error(self.interpreter, 'ErrorType.NAME_ERROR')
        self.field_defs[name] = (res, type(res))
        return
    
    def __execute_print_statement(self, statement):
        res = ""
        for word in statement:
            if type(word) is not list:
                if word in list(self.method_params[self.what_method].keys()):
                    word = str(self.method_params[self.what_method][word][0])
                elif word in list(self.field_defs.keys()):
                    word = str(self.field_defs[word][0]) 
                res += word.replace('"', "")
            if type(word) is list:
                if word[0] == 'call':
                    res += str(self.__execute_call_statement(word[1:]))
                if word[0] in list(self.operators.keys()):
                    res += str(self.__eval_exp(word)).lower()


        IB.output(self=self.interpreter, val=res)
        return
    
    def __execute_input_statement(self, statement):
        res = IB.get_input(self.interpreter) 
        res = self.__format_values(res)    
        #self.method_params[self.what_method] = {statement[0] : (res, type(res))}
        if statement[0] in list(self.method_params[self.what_method].keys()):
            self.method_params[self.what_method][statement[0]] = (res, type(res))
        elif statement[0] in list(self.field_defs.keys()): 
            self.field_defs[statement[0]] = (res, type(res)) 
        else:
            IB.error(self.interpreter, 'ErrorType.NAME_ERROR')
    
    def __execute_call_statement(self,statement):
        object_reference, method_name, *args = statement
        # if this is not me, u need a global class tracker and then refer to that objects run method
        if object_reference != 'me':
            raise Exception
        else:
            params = []
            for arg in list(args):
                if type(arg) is list:
                    if arg[0] in list(self.operators.keys()):
                        params.append(self.__eval_exp(arg))
                elif arg in list(self.method_params[self.what_method].keys()):
                    params.append(self.method_params[self.what_method][arg][0])
                elif arg in list(self.field_defs.keys()):
                    params.append(self.field_defs[arg][0])
                elif arg.replace("-","").isnumeric():
                    params.append(int(arg))
        return self.call_method(method_name, params)
    
    def __execute_while_statement(self,statement):
        self.cond = True
        while self.cond:
            res = self.__execute_if_statement(statement)
            if self.end: return
        return res
    
    def __execute_if_statement(self,statement):
        try:
            condition, if_clause, else_clause = statement
        except:
            condition, if_clause = statement
            else_clause = None
        condition = self.__eval_exp(condition)
        if type(condition) is not bool: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')
        save_method_control_flo = self.what_method
        if condition: body = if_clause
        elif not else_clause: 
            self.cond = False
            return
        else: body = else_clause
        
        res = None
        self.method_defs[IB.IF_DEF] = ([], [body])
        if IB.IF_DEF not in list(self.method_params.keys()):
            self.method_params[IB.IF_DEF] = self.method_params[self.what_method] 
        res = self.call_method( IB.IF_DEF, [])
        if self.end: return
        self.method_params[self.what_method] = self.method_params[IB.IF_DEF]
        #del self.method_defs[IB.IF_DEF]
        #del self.method_params[IB.IF_DEF]
        self.what_method = save_method_control_flo
        return res
    
    def __execute_return_statement(self,statement):
        if not statement: 
            self.end = True
            return
        if type(statement[0]) is list:
            if statement[0][0] in list(self.operators.keys()):
                return self.__eval_exp(statement[0])
            if statement[0][0] == IB.CALL_DEF:
                return self.__execute_call_statement(statement[0])
        if statement[0] in list(self.method_params[self.what_method].keys()):
            return self.method_params[self.what_method][statement[0]][0]
        if statement[0] in list(self.field_defs.keys()): 
            return self.field_defs[statement[0]][0]
        return self.__format_values(statement[0])
    
    def __execute_all_sub_statements_of_begin_statement(self,statement):
        res = None
        for line in statement:
            res = self.__run_statement(line)
            if self.end:
                return
        return res
    
    def __execute_set_statement(self, statement):
        name,value = statement
        if type(value) is list:
            if value[0] in list(self.operators.keys()):
                res = self.__eval_exp(value)
                self.method_params[self.what_method][name] = (res, type(res)) 
            elif value[0] == IB.CALL_DEF:
                self.__execute_call_statement(value) 
        else:
            value = self.__format_values(value)
            self.method_params[self.what_method][name] = (value, type(value))
        return
        
#   # runs/interprets the passed-in statement until completion and
#   # gets the result, if any
    def __run_statement(self, statement):
        keyword = statement[0]
        statement = statement[1:]
        if keyword == IB.PRINT_DEF:
            result = self.__execute_print_statement(statement)
        elif keyword == IB.INPUT_INT_DEF or keyword == IB.INPUT_STRING_DEF:
            result = self.__execute_input_statement(statement)
        elif keyword == IB.CALL_DEF:
            result = self.__execute_call_statement(statement)
        elif keyword == IB.WHILE_DEF:
            result = self.__execute_while_statement(statement)
        elif keyword == IB.IF_DEF:
            result = self.__execute_if_statement(statement)
        elif keyword == IB.RETURN_DEF:
            result = self.__execute_return_statement(statement)
        elif keyword == IB.BEGIN_DEF:
            result = self.__execute_all_sub_statements_of_begin_statement(statement)
        elif keyword == IB.SET_DEF:
            result = self.__execute_set_statement(statement)
        return result

    def __format_values(self,string):
        res = ""
        if string.replace(".", "").replace("-","").isnumeric(): 
            res = int(string)
        elif string == IB.TRUE_DEF or string == IB.FALSE_DEF:
            return string
        elif string in list(self.operators.keys()):
            res = self.operators[string][0]
        else:
            res = str(string)
        return res
    
    def __eval_exp(self,expression):
        if expression[0] not in list(self.operators.keys()): IB.error(self.interpreter, 'ErrorType.TYPE_ERROR') 
        op, is_boolean_operator = self.operators[expression[0]]
        filled_in_exp = []
        for i,term in enumerate(expression):
            expr_val = term
            if type(term) is list:  
                if term[0] in list(self.operators.keys()):                                  # expression
                    expr_val = self.__eval_exp(term)
                if term[0] == IB.CALL_DEF:                                                  # method call
                    expr_val = self.__execute_call_statement(term[1:])                                    
            elif term in list(self.method_params[self.what_method].keys()):                 # method parameter
                expr_val = self.method_params[self.what_method][term]
            elif term in list(self.field_defs.keys()):                                      # field variable
                expr_val = self.field_defs[term]
            elif term.replace('.',"").replace("-","").isnumeric():                          # number
                expr_val = (int(term), type(int(term)))
            elif '"' in term:                                                               # string
                expr_val = (str(term), type(str(term))) 
            elif term in list(self.operators.keys()):                                       # operator                 
                expr_val = self.operators[term]
            elif expr_val == term:                                                          # out of scope
                raise Exception
            filled_in_exp.append(expr_val)
        
        if op is operator.not_:
            if len(filled_in_exp[1:]) != 1: raise Exception
            if type(filled_in_exp[1]) is not tuple: 
                filled_in_exp[1] = (filled_in_exp[1], type(filled_in_exp[1]))
            if type(filled_in_exp[1][0]) is not bool: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')
            res = op(filled_in_exp[1][0])
        elif is_boolean_operator:
            if (len(filled_in_exp)) == 1:
                if type(filled_in_exp[0][0]) is not bool: IB.error(self.interpreter, 'TypeError.TYPE_ERROR')
                return filled_in_exp[0][0]
            if len(filled_in_exp[1:]) != 2: raise Exception
            if type(filled_in_exp[1][0]) != type(filled_in_exp[2][0]):
                IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')
            if op not in {operator.ne, operator.eq, operator.and_, operator.or_} and type(filled_in_exp[1][0]) is bool:
                IB.error(self.interpreter, 'ErrorType.TYPE_ERROR') 
            res = op(filled_in_exp[1][0], filled_in_exp[2][0])
        else:
            stack = []
            for c in filled_in_exp[::-1]:
                if type(c) is int:
                    stack.append(c)
                elif not callable(c[0]):
                    stack.append(c[0])
                else:
                    o1 = stack.pop()
                    o2 = stack.pop()
                    if type(o1) != type(o2): IB.error(self.interpreter, 'ErrorType.TYPE_ERROR') 
                    stack.append(c[0](o1,o2))
            res = int(stack.pop())
        return res
    

# def main():


#     program_ex = ['(class main',
#                     '(field num 0)',
#                     '(field result 1)',
#                     '(method main ()',
#                         '(begin',
#                             '(print "Enter a number: ")',
#                             '(inputs num)',
#                             '(print num " factorial is " (call me factorial num))))',
#                             '',
#                     '(method factorial (n)',
#                         '(return num)))']
#     program_ex2 = ['(class main',
#                     '(field num "ash")',
#                     '(field result 1)',
#                     '(method main ()',
#                         '(begin',
#                             '(print "Enter a number: ")',
#                             '(inputi num)',
#                             '(print num " factorial is " (call me factorial num))))',
#                             '',
#                     '(method factorial (n)',
#                     '(begin'
#                         '(set result 1)',
#                         '(print num)',
#                         '(if (!= "ash" num)',
#                             '(return result)))))']

#     program = Interpreter()
#     program.run(program_ex2)

# main()
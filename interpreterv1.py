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
            if field_or_method[0] == IB.FIELD_DEF:
                fields.append(field_or_method)
            else:
                if field_or_method in methods: raise Exception
                methods.append(field_or_method)
        # fields = [field for field in def_list if field[0] == 'field']
        # methods = [method for method in def_list if method[0] == 'method']
        return ClassDefinition(fields, methods)

    def print_line_nums(self, parsed_program):
        for item in parsed_program:
            if type(item) is not list:
                print(f'{item} was found on line {item.line_num}')
            else:
                self.print_line_nums(item)




#

class ClassDefinition:
# constructor for a ClassDefinition 
    def __init__(self, fields, methods):
       self.my_methods = methods 
       self.my_fields = fields
       # ... 

    # uses the definition of a class to create and return an instance of it
    def instantiate_object(self):
        obj = ObjectDefinition()
        for method in self.my_methods:
            obj.add_method(method)
        for field in self.my_fields:
            obj.add_field(field[1], field[2])
        return obj
#
class ObjectDefinition: 
    def __init__(self):
        self.method_defs = {}
        self.field_defs = {}
        self.method_params = {}
        self.what_method = ""
        self.operators = {'+' : (operator.add, False), '-' : (operator.sub, False),'*' : (operator.mul, False), 
                            '/' : (operator.truediv, False),'%' : (operator.mod, False), '>' : (operator.gt, True),
                            '<' : (operator.lt, True),'>=' : (operator.ge, True), '<=' : (operator.le, True),
                            '==' :(operator.eq, True), '!' : (operator.truth, True), '!=' : (operator.ne, True),
                            '&' : (operator.and_, True) ,'|' : (operator.or_, True)}

    # Interpret the specified method using the provided parameters
    def call_method(self, method_name, parameters):
        self.what_method = method_name
        if self.what_method not in list(self.method_params.keys()):
            self.method_params[self.what_method] = {}
        method_params, statement = self.__find_method(method_name)
        #converting statement list of lists in to just a list.
        if len(method_params) != len(parameters):
            IB.error('ErrorType.TYPE_ERROR')
        else:
            for i in range(len(parameters)):
                self.method_params[self.what_method][method_params[i]] = (parameters[i], type(parameters[i]))  
        result = self.__run_statement(statement[0])
        return result
    
    def __find_method(self,method_name):
        if method_name in self.method_defs:
            return self.method_defs[method_name] #1 represents the method itself
        else:
            IB.error('ErrorType.NAME_ERROR')

    def add_method(self, method):
        #name -> params, statement
        self.method_defs[method[1]] = (method[2], method[3:]) 
        return
    
    def add_field(self, name, initial_value):
        res = self.__format_values(initial_value)
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
            if type(word) is list and word[0] == 'call':
                
                res += str(self.__execute_call_statement(word[1:]))
        
        print(res)
        return True
    
    def __execute_input_statement(self, statement):
        res = input() 
        res = self.__format_values(res)    
        #self.method_params[self.what_method] = {statement[0] : (res, type(res))}
        self.method_params[self.what_method][statement[0]] = (res, type(res)) 
        return True
    
    def __execute_call_statement(self,statement):
        object_reference, method_name, *args = statement
        # if this is not me, u need a global class tracker and then refer to that objects run method
        if object_reference != 'me':
            raise Exception
        else:
            params = []
            for arg in list(args):
                if arg in list(self.method_params[self.what_method].keys()):
                    params.append(self.method_params[self.what_method][arg][0])
                elif arg in list(self.field_defs.keys()):
                    params.append(self.field_defs[arg][0]) 
        return self.call_method(method_name, params)
    
    def __execute_while_statement(self,statement):
        condition = statement[0]
        cond = self.__eval_exp(condition)
        while cond:
            res = self.__execute_if_statement(statement)
            cond = self.__eval_exp(condition)
        return res
    
    def __execute_if_statement(self,statement):
        condition, body = statement
        save_method_control_flo = self.what_method
        cond = self.__eval_exp(condition)
        if type(cond) is not bool:
            raise Exception

        if cond:
            self.method_defs[IB.IF_DEF] = ([], [body])
            self.method_params[IB.IF_DEF] = self.method_params[self.what_method] 
            res = self.call_method( IB.IF_DEF, [])
            self.method_params[self.what_method] = self.method_params[IB.IF_DEF]
            self.what_method = save_method_control_flo
            return res
        return None
    
    def __execute_return_statement(self,statement):
        if type(statement[0]) is list:
            pass    # this is likely a call function
        if IB.IF_DEF in list(self.method_defs.keys()):
            self.method_params[self.what_method] = self.method_params[IB.IF_DEF]
        if statement[0] in list(self.method_params[self.what_method].keys()):
            return self.method_params[self.what_method][statement[0]][0]

        return self.__format_values(statement[0])
    
    def __execute_all_sub_statements_of_begin_statement(self,statement):
        res = None
        for line in statement:
            res = self.__run_statement(line)
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
        return True
        
#   # runs/interprets the passed-in statement until completion and
#   # gets the result, if any
    def __run_statement(self, statement):
        keyword = statement[0]
        statement = statement[1:]
        if keyword == IB.PRINT_DEF:
            result = self.__execute_print_statement(statement)
        elif keyword == IB.INPUT_INT_DEF:
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
        if string.replace(".", "").isnumeric(): 
            res = int(string)
        elif string == 'false' or string == 'true':
            res = eval(string.capitalize())
        else:
            res = str(string)
        return res
    
    def __eval_exp(self,expression):
        op, is_boolean_operator = self.operators[expression[0]]
        filled_in_exp = []
        for i,term in enumerate(expression):
            expr_val = term
            if term.replace('.',"").isnumeric():
                expr_val = int(term)
            elif '"' in term:
                expr_val = term   # string
            elif term in list(self.method_params[self.what_method].keys()):
                expr_val = self.method_params[self.what_method][term][0]
            elif term in list(self.field_defs.keys()):
                expr_val = self.field_defs[term][0]
            elif term in list(self.operators.keys()):
                expr_val = self.operators[term][0]
            elif expr_val == term:
                raise Exception # term is not constant, var in scope, or term is not operator
            filled_in_exp.append(expr_val)
        
        if op == operator.neg:
            if len(filled_in_exp[1:]) != 1: raise Exception
            elif type(filled_in_exp[1]) is list: filled_in_exp[1] = self.__eval_exp(expression[1])
            return op(filled_in_exp[1])

        if is_boolean_operator:
            if len(filled_in_exp[1:]) != 2: raise Exception
            res = op(filled_in_exp[1], filled_in_exp[2])
        else:
            stack = []
            for c in filled_in_exp[::-1]:
                if type(c) is int:
                    stack.append(c)
                else:
                    o1 = stack.pop()
                    o2 = stack.pop()
                    stack.append(c(o1,o2))
            res = stack.pop() 
        return res

def main():
    # all programs will be provided to your interpreter as a list of
    # python strings, just as shown here.
    program_source = ['(class main',
                        ' (method main ()',
                        '   (print "hello world!")',
                        ' ) # end of method',
                        ') # end of class']
    

    # Field Syntax
    field_syn = ['(field field_name initial_value)']
    field_ex = ['(field foo_123 10)']
    # this is how you use our BParser class to parse a valid
    # Brewin program into python list format.

    # Method Syntax
    method_syn = ['(method method_name (param_name1 param_name2 ... param_namen)', 
                    ' (statement_to_execute)',
                    ')'] # end of method
    method_ex_oline = ['(method square (val) (return (* val val)))']
    method_ex_begin = ['(method do_several_things ()',
                        '(begin',
                        '(print "hi")',
                        '(print "bye")',
                        ')', ')']
    # Methods are always public, refer to param name if equal to a field, functions dont
    # have specific types (pass anything return anything including nothing), functions
    # must have begin statement if multiple statements
    # can pass expresssions so check if can evaluate it first

    program_ex = ['(class main',
                    '(field num 0)',
                    '(field result 1)',
                    '(method main ()',
                        '(begin',
                            '(print "Enter a number: ")',
                            '(inputi num)',
                            '(print num " factorial is " (call me factorial num))))',
                            '',
                    '(method factorial (n)',
                    '(begin'
                        '(set result 1)',
                        '(while (> n 0)',
                            '(begin',
                                '(set result (* n result))',
                                '(set n (- n 1))))',
                        '(return result))))']
    
    class_ex =['(class person',
         '(field name "")',
         '(field age 0)',
         '(method init (n a) (begin (set name n) (set age a)))',
         '(method talk (to_whom) (print name " says hello to " to_whom))',
         '(method get_age () (return age))',
        ')',
      '(class main',
       '(field p null)',
       '(method tell_joke (to_whom) (print "Hey " to_whom ", knock knock!"))',
       '(method main ()',
'(begin',
            '(call me tell_joke "Leia")',
            '(set p (new person))',
            '(call p init "Siddarth" 25)',  
'(call p talk "Boyan")',       
'(print \"Siddarth\'s age is \" (call p get_age))',
')', ')',
')']


    test_if_set_ex = ['(class main',
                    '(field num 0)',
                    '(field result 3)',
                    '(method main ()',
                        '(begin',
                            '(print "Enter a number: ")',
                            '(inputi num)',
                            '(print num " factorial is " (call me factorial num))))',
                            '',
                    '(method factorial (n)',
                    '(begin'
                        '(set result 1)',
                        '(if (> n 0)',
                            '(begin',
                                '(set result (* n result))',
                                '(return result))))',
                            '))']
    
    nested_flow_ex = ['(class main',
                    '(field num 0)',
                    '(field result 1)',
                    '(method main ()',
                        '(begin',
                            '(print "Enter a number: ")',
                            '(inputi num)',
                            '(print num " factorial is " (call me factorial num))))',
                            '',
                    '(method factorial (n)',
                    '(begin'
                        '(set result 1)',
                        '(while (> n 0)',
                            '(begin',
                                '(set result (* n result))',
                                '(print result)',
                                '(set n (- n 1))))',
                        '(return result))))']
    
    # Class referencing next

    input = nested_flow_ex
    example = Interpreter()
    example.run(input)
    #example.print_line_nums(example.parsed_program)
    #print(example.parsed_program)
    #print(example.classes)
    # for i,program in enumerate(example.parsed_program[0]):
    #     print(example.parsed_program[0][i])
    #     print()
main()

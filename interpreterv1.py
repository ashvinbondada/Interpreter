from bparser import BParser
from intbase import InterpreterBase as IB
import operator


class Interpreter(IB):
    lazy_loaded = {}

    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)  
        
    def run(self, program):
        # parse the program into a more easily processed form
        result, self.parsed_program = BParser.parse(program)
        if result == False: return # error
        self.classes = {}
        self.__discover_all_classes_and_track_them(self.parsed_program)
        self.find_definition_for_class(IB.MAIN_CLASS_DEF)        
        self.lazy_loaded[IB.MAIN_CLASS_DEF].call_method(IB.MAIN_FUNC_DEF, [])

    def __discover_all_classes_and_track_them(self, parsed_program):
        for i in range(len(parsed_program)):
            if parsed_program[i][1] in list(self.classes.keys()):
                IB.error(self, "ErrorType.TYPE_ERROR")
            self.classes[parsed_program[i][1]] = parsed_program[i][2:]
        # map of class name to entire definition in list form
        # can refer to this if a class does exist or not.
        return

    def find_definition_for_class(self,class_name):
        def_list = self.classes[class_name]
        fields = []
        methods = []
        for field_or_method in def_list:
            # if field or name == IB.MAIN_CLASS_DEF -> undefined 
            if field_or_method[0] == IB.FIELD_DEF: fields.append(field_or_method)
            else: methods.append(field_or_method)
        if not methods: raise Exception # Each class must have one method
        class_def = ClassDefinition(fields=fields, methods=methods, interpreter = self)
        obj = class_def.instantiate_object() 
        Interpreter.lazy_loaded[class_name] = obj
        return

    obj = None
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
        res = self.__eval_exp([initial_value])
        if name in list(self.field_defs.keys()):
            IB.error(self.interpreter, 'ErrorType.NAME_ERROR')
        self.field_defs[name] = (res , type(res))
        return
    
    def __execute_print_statement(self, statement):
        res = ""
        for word in statement:
            if type(word) is not list:
                word = self.__eval_exp([word])
            else:
                word = self.__eval_exp(word)
            if type(word) is bool: word = str(word).lower()
            res += str(word)
            # if type(word) is not list:
            #     if word in list(self.method_params[self.what_method].keys()):
            #         word = str(self.method_params[self.what_method][word][0])
            #     elif word in list(self.field_defs.keys()):
            #         word = str(self.field_defs[word][0]) 
            #     res += word.replace('"', "")
            # if type(word) is list:
            #     if word[0] == 'call':
            #         res += str(self.execute_call_statement(word[1:]))
            #     if word[0] in list(self.operators.keys()):
            #         res += str(self.__eval_exp(word)).lower()
        IB.output(self=self.interpreter, val=res)
        return
    
    def __execute_input_statement(self, statement):
        res = '"'+IB.get_input(self.interpreter)+'"'
        res = self.__eval_exp([res])        
        #self.method_params[self.what_method] = {statement[0] : (res, type(res))}
        if statement[0] in list(self.method_params[self.what_method].keys()):
            self.method_params[self.what_method][statement[0]] = (res, type(res))
        elif statement[0] in list(self.field_defs.keys()): 
            self.field_defs[statement[0]] = (res, type(res)) 
        else:
            IB.error(self.interpreter, 'ErrorType.NAME_ERROR')
    
    def execute_call_statement(self,statement):
        try: object_reference, method_name, *args = statement
        except: 
            object_reference, *args = statement
            method_name = None
        # if this is not me, u need a global class tracker and then refer to that objects run method
        if object_reference != 'me':
            if object_reference in list(self.method_params[self.what_method].keys()):
                obj = self.method_params[self.what_method][object_reference][0]
            elif object_reference in list(self.field_defs.keys()):
                obj = self.field_defs[object_reference][0]
            else: IB.error(self.interpreter, 'ErrorType.FAULT_ERROR')
            if not obj: IB.error(self.interpreter, 'ErrorType.FAULT_ERROR')
            if method_name not in list(obj.method_defs.keys()): IB.error(self.interpreter, 'ErrorType.NAME_ERROR')
            # bound the variables to their values now
            if len(args) != len(obj.method_defs[method_name][0]):
                IB.error(self.interpreter,'ErrorType.TYPE_ERROR')
            else:
                for i in range(2, len(statement[2:])):
                    term = statement[i]
                    if term in list(self.method_params[self.what_method].keys()):
                        statement[i] = self.method_params[self.what_method][term][0]
                    elif term in list(self.field_defs.keys()):
                        statement[i] = self.field_defs[term][0] 
            statement[0] = IB.ME_DEF
            obj.what_method = method_name
            return obj.execute_call_statement(statement)
        
        params = []
        for arg in list(args):
            if type(arg) is list:
                if arg[0] in list(self.operators.keys()):
                    params.append(self.__eval_exp(arg))
                # handle call method
            elif arg.replace("-","").isnumeric():
                params.append(int(arg))
            elif '"' in str(arg): 
                params.append(str(arg).replace('"',""))
            elif arg in list(self.method_params[self.what_method].keys()):
                params.append(self.method_params[self.what_method][arg][0])
            elif arg in list(self.field_defs.keys()):
                params.append(self.field_defs[arg][0])
        res = self.call_method(method_name, params)
        self.end = False 
        return res
    
    def __execute_while_statement(self,statement):
        condition, body =  statement
        if type(self.__eval_exp(condition)) is not bool: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')
        while self.__eval_exp(condition):
            res = self.__run_statement(body)
            if self.end: break
        return res
    
    def __execute_if_statement(self,statement):
        try: condition, if_clause, else_clause = statement
        except: 
            condition, if_clause = statement
            else_clause = None
        cond = self.__eval_exp(condition)
        if type(cond) is not bool: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')
        
        if cond: body = if_clause
        elif not else_clause: return
        else: body = else_clause
        res = self.__run_statement(body)
        return res 
    
    def __execute_return_statement(self,statement):
        self.end = True
        if not statement: 
            return
        if type(statement[0]) is list:
            if statement[0][0] in list(self.operators.keys()):
                return self.__eval_exp(statement[0])
            if statement[0][0] == IB.CALL_DEF:
                return self.execute_call_statement(statement[0][1:])
        if statement[0] in list(self.method_params[self.what_method].keys()):
            return self.method_params[self.what_method][statement[0]][0]
        if statement[0] in list(self.field_defs.keys()): 
            return self.field_defs[statement[0]][0]
        return self.__eval_exp([statement[0]])
    
    def __execute_all_sub_statements_of_begin_statement(self,statement):
        res = None
        for line in statement:
            res = self.__run_statement(line)
            if self.end: break
        return res
    
    def __execute_new_statement(self,expression):
        if expression[0] not in list(self.interpreter.lazy_loaded.keys()):
            if expression[0] in list(self.interpreter.classes.keys()):
                self.interpreter.find_definition_for_class(expression[0])
            else:
                raise Exception # wrong class name
        return self.interpreter.lazy_loaded[expression[0]]
            
        # if exoression

    def __execute_set_statement(self, statement):
        name,value = statement
        if type(value) is list:
            if value[0] in list(self.operators.keys()):
                res = self.__eval_exp(value)
            elif value[0] == IB.CALL_DEF:
                res = self.execute_call_statement(value[1:]) 
            elif value[0] == IB.NEW_DEF:
                res = self.__execute_new_statement(value[1:])
        else:
            res = self.__eval_exp([value])
            if type(res) is bool: res = str(res).lower()
        if name in list(self.method_params[self.what_method].keys()):
            self.method_params[self.what_method][name] = (res, type(res))
        elif name in list(self.field_defs.keys()):
            self.field_defs[name] = (res, type(res)) 
        else: IB.error(self.interpreter, 'ErrorType.NAME_ERROR')
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
            result = self.execute_call_statement(statement)
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

    # def __format_values(self,string):
    #     res = ""
    #     if string.replace(".", "").replace("-","").isnumeric(): 
    #         res = int(string)
    #     elif string == IB.TRUE_DEF or string == IB.FALSE_DEF:
    #         return string
    #     elif string in list(self.operators.keys()):
    #         res = self.operators[string][0]
    #     else:
    #         res = str(string)
    #     return res
    
    def __eval_exp(self,expression):
        if type(expression[0]) is int: return expression[0]
        # if len(expression) > 1:
        #     if expression[0] not in list(self.operators.keys()): 
        #         IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')
        filled_in_exp = []
        for i,term in enumerate(expression):
            expr_val = term
            if type(term) is list:  
                if term[0] in list(self.operators.keys()):
                    res = self.__eval_exp(term)                                  # expression
                    expr_val = (res, type(res))
                if term[0] == IB.CALL_DEF:    
                    res = self.__eval_exp(term)                           # method call
                    expr_val = (res, type(res))
            elif term == IB.CALL_DEF:
                return self.execute_call_statement(expression[1:])
            elif term.replace('"',"").replace("-","").isnumeric():                          # number
                expr_val = (int(term.replace('"',"")), type(int(term.replace('"',""))))
            elif '"' in term:                                                               # string
                expr_val = (str(term).replace('"',""), type(str(term)))                                  
            elif self.what_method != '' and term in list(self.method_params[self.what_method].keys()):                 # method parameter
                expr_val = self.method_params[self.what_method][term]
            elif term in list(self.field_defs.keys()):                                   # field variable
                expr_val = self.field_defs[term]
            elif term in list(self.operators.keys()):                                       # operator                 
                expr_val = self.operators[term]
            elif expr_val is term:                                                          # out of scope
                IB.error(self.interpreter, 'ErrorType.NAME_ERROR')
            filled_in_exp.append(expr_val)
        # print('my',filled_in_exp[0][0], len(filled_in_exp))
        res = filled_in_exp[0][0]
        if len(filled_in_exp) == 1: 
            return res
        if expression[0] not in list(self.operators.keys()): IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')
        op, is_boolean_operator = self.operators[expression[0]]
        if op is operator.not_:
            if len(filled_in_exp[1:]) != 1: raise Exception
            if type(filled_in_exp[1][0]) is not bool: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')
            res = op(filled_in_exp[1][0])
        elif is_boolean_operator:
            if (len(filled_in_exp)) == 1:
                if type(filled_in_exp[0][0]) is not bool: IB.error(self.interpreter, 'TypeError.TYPE_ERROR')
                return filled_in_exp[0][0]
            if len(filled_in_exp[1:]) != 2: raise Exception
            #print(filled_in_exp)
            try: res = op(filled_in_exp[1][0], filled_in_exp[2][0])
            except: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR') 
            # if type(filled_in_exp[1][0]) != type(filled_in_exp[2][0]):
            #     IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')
            # if op not in {operator.ne, operator.eq, operator.and_, operator.or_} and type(filled_in_exp[1][0]) is bool:
            #     IB.error(self.interpreter, 'ErrorType.TYPE_ERROR') 
            # res = op(filled_in_exp[1][0], filled_in_exp[2][0])
        else:
            stack = []
            for c in filled_in_exp[::-1]:
                if c[1] in [int, str]:
                    stack.append(c[0])
                elif c[1]: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')
                else:
                    o1 = stack.pop()
                    o2 = stack.pop()
                    if type(o1) != type(o2): IB.error(self.interpreter, 'ErrorType.TYPE_ERROR') 
                    stack.append(c[0](o1,o2))
            res = stack.pop()
            
        return res
    

def main():


    program_ex = ['(class main',
                    '(field num 0)',
                    '(field result 1)',
                    '(method main ()',
                        '(begin',
                            '(print "Enter a number: ")',
                            '(inputs num)',
                            '(print num " factorial is " (call me factorial num))))',
                            '',
                    '(method factorial (n)',
                        '(return num)))']
    program_ex2 = ['(class main',
                    '(field other null)',
                    '(method main ()',
                    '(begin'
                     '(print other)'
                    '(call other))',
                    ')',
                    ')']

    program = Interpreter()
    program.run(program_ex2)

if __name__ == '__main__':
    main()
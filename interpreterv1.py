from bparser import BParser
from intbase import InterpreterBase as IB
import operator

class Interpreter(IB):
    
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        
    def run(self, program):
        # parse the program into a more easily processed form
        result, self.parsed_program = BParser.parse(program)
        if result == False: return # error
        self.classes = {}
        self.__discover_all_classes_and_track_them(self.parsed_program)
        obj = self.find_definition_for_class(IB.MAIN_CLASS_DEF)        
        obj.call_method(IB.MAIN_FUNC_DEF, [])

    def __discover_all_classes_and_track_them(self, parsed_program):
        for i in range(len(parsed_program)):
            if parsed_program[i][1] in list(self.classes.keys()):
                IB.error(self, "ErrorType.TYPE_ERROR")
            self.classes[parsed_program[i][1]] = parsed_program[i][2:]
        return

    def find_definition_for_class(self,class_name):
        try: def_list = self.classes[class_name]
        except: IB.error(self, 'ErrorType.TYPE_ERROR')
        fields = []
        methods = []
        for field_or_method in def_list:
            # if field or name == IB.MAIN_CLASS_DEF -> undefined 
            if field_or_method[0] == IB.FIELD_DEF: fields.append(field_or_method)
            else: methods.append(field_or_method)
        if not methods: raise Exception # Each class must have one method

        class_def = ClassDefinition(fields=fields, methods=methods, interpreter = self)
        obj = class_def.instantiate_object() 
        return obj

    def print_statements(self, val):
        IB.output(self,val)
    obj = None
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
                            '==' :(operator.eq, True), '!' : (operator.not_, int), '!=' : (operator.ne, True),
                            '&' : (operator.and_, True) ,'|' : (operator.or_, True), 'true' : (True, bool), 'false' : (False, bool),
                            'null' : (None, type(None))}

    # Interpret the specified method using the provided parameters
    def call_method(self, method_name, parameters):
        method_params, statement = self.__find_method(method_name)
        self.what_method = method_name
        if self.what_method not in list(self.method_params.keys()):
            self.method_params[self.what_method] = {}
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
            word = self.__eval_exp([word])
            if type(word) is bool: word = str(word).lower()
            res += str(word)
        IB.output(self.interpreter, val=res)
        return
    
    def __execute_input_statement(self, statement):
        res = '"'+IB.get_input(self.interpreter)+'"'
        res = self.__eval_exp([res])        
        try: self.method_params[self.what_method][statement[0]] = (res, type(res))
        except: pass
        try: self.field_defs[statement[0]] = (res, type(res))
        except: IB.error(self.interpreter, 'ErrorType.NAME_ERROR') 
    
    def execute_call_statement(self,statement):
        try: object_reference, method_name, *args = statement
        except: 
            object_reference, *args = statement
            method_name = None
        # if this is not me, u need a global class tracker and then refer to that objects run method
        params = []
        for arg in list(args):
            try: params.append(self.method_params[self.what_method][arg][0])
            except:
                try: params.append(self.field_defs[arg][0]) 
                except: params.append(self.__eval_exp([arg]))
        if object_reference != 'me':
            try: obj = self.method_params[self.what_method][object_reference][0]
            except:
                try: obj = self.field_defs[object_reference][0]
                except: obj = self.__eval_exp([object_reference]) 
            if not obj or type(obj) is not ObjectDefinition: IB.error(self.interpreter, 'ErrorType.FAULT_ERROR')
            if method_name not in list(obj.method_defs.keys()): IB.error(self.interpreter, 'ErrorType.NAME_ERROR')
            return obj.call_method(method_name, params)
        
        temp = self.method_params[self.what_method].copy() 
        res = self.call_method(method_name, params)
        self.method_params[self.what_method] = temp
        self.end = False 
        return res
    
    def __execute_while_statement(self,statement):
        condition, body =  statement
        while True:
            if type(self.__eval_exp([condition])) is not bool: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')
            if not self.__eval_exp([condition]): break
            res = self.__run_statement(body)
            if self.end: return res
        return
    
    def __execute_if_statement(self,statement):
        try: condition, if_clause, else_clause = statement
        except: 
            condition, if_clause = statement
            else_clause = None
        cond = self.__eval_exp([condition])
        if type(cond) is not bool: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')

        if cond: body = if_clause
        elif not else_clause: return
        else: body = else_clause

        res = self.__run_statement(body)
        return res 
    
    def __execute_return_statement(self,statement):
        self.end = True
        if not statement: return
        try: return self.method_params[self.what_method][statement[0]][0]
        except:
            try: return self.field_defs[statement[0]][0]
            except: return self.__eval_exp([statement[0]])
    
    def __execute_all_sub_statements_of_begin_statement(self,statement):
        for line in statement:
            res = self.__run_statement(line)
            if self.end: return res
        return
    
    def __execute_new_statement(self,expression):
        if expression[0] in list(self.interpreter.classes.keys()):
            obj = self.interpreter.find_definition_for_class(expression[0])
        else: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')
        return obj
            
    def __execute_set_statement(self, statement):
        name,value = statement
        res = self.__eval_exp([value])
        if type(res) is bool: res = str(res).lower()    # True/False -> true/false
        if name in list(self.method_params[self.what_method].keys()):
            self.method_params[self.what_method][name] = (res, type(res))
        elif name in list(self.field_defs.keys()):
            self.field_defs[name] = (res, type(res))
        else: IB.error(self.interpreter, 'ErrorType.NAME_ERROR')
        return
        
#   # runs/interprets the passed-in statement until completion and
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

    def __eval_exp(self,expression):
        if type(expression[0]) is list: expression = expression[0]
        if type(expression[0]) in [int, bool]: return expression[0]
        filled_in_exp = []
        for term in expression:
            expr_val = term
            if type(term) is list:     
                res = self.__eval_exp(term)                           # method call
                expr_val = (res, type(res))
            elif term == IB.NEW_DEF:
                return self.__execute_new_statement(expression[1:])
            elif term == IB.CALL_DEF:
                return self.execute_call_statement(expression[1:])
            elif term.replace('"',"").replace("-","").isnumeric():                          # number
                expr_val = (int(term.replace('"',"")), int)
            elif '"' in term:                                                               # string
                expr_val = (str(term).replace('"',""), str)                                  
            elif self.what_method != '' and term in list(self.method_params[self.what_method].keys()):                 # method parameter
                expr_val = self.method_params[self.what_method][term]
            elif term in list(self.field_defs.keys()):                                   # field variable
                expr_val = self.field_defs[term]
            elif term in list(self.operators.keys()):                                       # operator                 
                expr_val = self.operators[term]
            elif expr_val is term: IB.error(self.interpreter, 'ErrorType.NAME_ERROR')   # out of scope
            filled_in_exp.append(expr_val)
        
        res = filled_in_exp[0][0]
        if len(filled_in_exp) == 1: return res
        if expression[0] not in list(self.operators.keys()): IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')
        op, is_boolean_operator = self.operators[expression[0]]
        if is_boolean_operator is int:
            if len(filled_in_exp[1:]) != 1: raise Exception
            if filled_in_exp[1][1] is not bool: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')
            res = op(filled_in_exp[1][0])
        elif is_boolean_operator:
            if (len(filled_in_exp)) == 1:
                if filled_in_exp[0][1] is not bool: IB.error(self.interpreter, 'TypeError.TYPE_ERROR')
                return filled_in_exp[0][0]
            if len(filled_in_exp[1:]) != 2: raise Exception
            if filled_in_exp[1][1] != filled_in_exp[2][1] and filled_in_exp[1][1] is not type(None) and filled_in_exp[2][1] is not type(None): 
                IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')  
            try: res = op(filled_in_exp[1][0], filled_in_exp[2][0])
            except: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR') 
        else:
            stack = []
            for c in filled_in_exp[::-1]:
                if c[1] is bool: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')
                if c[1] in [int, str]: stack.append(c)
                else: 
                    o1 = stack.pop()
                    o2 = stack.pop()
                    if o1[1] != o2[1]: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR') 
                    if c[0] is not operator.add and type(o1) is str: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR') 
                    res = c[0](o1[0],o2[0])
                    if o1[1] is int: res = int(res)
                    stack.append(res)
            res = stack.pop()
        return res
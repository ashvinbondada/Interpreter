
from bparser import BParser, StringWithLineNumber
from intbase import InterpreterBase as IB
import operator, inspect

class Interpreter(IB):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        
    def run(self, program):
        # parse the program into a more easily processed form
        result, self.parsed_program = BParser.parse(program)
        if result == False: 
            return # error
        self.classes = {}
        self.__discover_all_classes_and_track_them(self.parsed_program)
        obj = self.find_definition_for_class(IB.MAIN_CLASS_DEF)      
        obj.call_method(IB.MAIN_FUNC_DEF, [])

    def __discover_all_classes_and_track_them(self, parsed_program):
        for c_def in parsed_program:
            if c_def[1] in list(self.classes.keys()):
                IB.error(self, "ErrorType.TYPE_ERROR")
            if c_def[2] == IB.INHERITS_DEF:
                self.classes[c_def[1]] = (c_def[3], c_def[4:])
            else: self.classes[c_def[1]] = (None, c_def[2:])
        
        self.class_dictionary = {k: v[0] for k, v in self.classes.items() if v[0] is not None}
        self.class_dictionary.update({k: k for k in self.classes.keys() if k not in self.class_dictionary})
        return

    def find_definition_for_class(self,class_name):
        try: def_list = self.classes[class_name][1]
        except: IB.error(self, 'ErrorType.TYPE_ERROR')
        fields = []
        methods = []
        for field_or_method in def_list:
            # if field or name == IB.MAIN_CLASS_DEF -> undefined 
            if field_or_method[0] == IB.FIELD_DEF: fields.append(field_or_method)
            else: methods.append(field_or_method)

        class_def = ClassDefinition(fields=fields, methods=methods, interpreter = self)
        obj = class_def.instantiate_object(self.class_dictionary, class_name) 
        return obj
#

class ClassDefinition:
# constructor for a ClassDefinition 
    def __init__(self, fields, methods, interpreter):
       self.my_methods = methods 
       self.my_fields = fields
       self.interpreter = interpreter

    # uses the definition of a class to create and return an instance of it
    def instantiate_object(self, class_dict, class_name):
        obj = ObjectDefinition(self.interpreter, class_dict, class_name)
        for method in self.my_methods:
            obj.add_method(method)
        for field in self.my_fields:
            obj.add_field(field[1], field[2], field[3], "field_defs")
        return obj

#
class ObjectDefinition: 

    def __init__(self, interpreter, class_dict, instance_of_what_class):
        self.interpreter = interpreter
        self.class_dict = class_dict
        self.method_defs = {}
        self.field_defs = {}
        self.method_params = {}
        self.what_class = instance_of_what_class
        self.base = None
        self.derived = self
        self.what_method = ""
        self.end = False
        self.null = False
        self.temp_obj = None
        self.operators = {'+' : (operator.add, False), '-' : (operator.sub, False),'*' : (operator.mul, False), 
                            '/' : (operator.truediv, False),'%' : (operator.mod, False), '>' : (operator.gt, True),
                            '<' : (operator.lt, True),'>=' : (operator.ge, True), '<=' : (operator.le, True),
                            '==' :(operator.eq, True), '!' : (operator.not_, 'unary'), '!=' : (operator.ne, True),
                            '&' : (operator.and_, True) ,'|' : (operator.or_, True), IB.TRUE_DEF : (True, bool), 
                            IB.FALSE_DEF : (False, bool), IB.NULL_DEF : [None, type(None), 'main']}        # True/False - boolean operator, int - unary operator, bool - True/False
        self.default_returns = {IB.INT_DEF : 0, IB.BOOL_DEF : 'false', IB.STRING_DEF: "", IB.VOID_DEF: None}
        if self.class_dict[self.what_class] != self.what_class:
            res = self.__execute_new_statement([self.class_dict[self.what_class]])
            self.base = res
            res.derived = self
    def call_method(self, method_name, parameters):
        return_type, method_params, statement = self.__find_method(method_name)
        self.what_method = method_name
        if self.what_method not in list(self.method_params.keys()):
            self.method_params[self.what_method] = {}
        if len(method_params) != len(parameters): IB.error(self.interpreter,'ErrorType.NAME_ERROR')
        else:
            for i in range(len(parameters)):
                required_type = method_params[i][0]
                if required_type == IB.STRING_DEF: required_type = 'str'
                if required_type not in ['str', IB.INT_DEF, IB.BOOL_DEF]:
                    if required_type not in list(self.class_dict.keys()): IB.error(self.interpreter,'ErrorType.TYPE_ERROR')  # type DNE
                    if parameters[i] != None: #self.method_params[self.what_method][method_params[i][1]] = [parameters[i], type(parameters[i]), required_type]  # pass in None 
                        if type(parameters[i]) is ObjectDefinition:
                            while required_type != parameters[i].what_class:
                                if self.class_dict[parameters[i].what_class] == parameters[i].what_class: IB.error(self.interpreter, 'ErrorType.NAME_ERROR') 
                                else: parameters[i].what_class = self.class_dict[parameters[i].what_class]
                        else:  IB.error(self.interpreter,'ErrorType.NAME_ERROR')       # passed in NOT an obj.
                elif eval(required_type) != type(parameters[i]): IB.error(self.interpreter,'ErrorType.NAME_ERROR') # wrong primitive type passed.
                elif method_params[i][1] in list(self.method_params[self.what_method].keys()): IB.error(self.interpreter,'ErrorType.NAME_ERROR') # duplicate params 
                self.method_params[self.what_method][method_params[i][1]] = [parameters[i], type(parameters[i]), required_type]  # add it 
        # print('parameters', parameters, self.method_params, statement[0])
        res = self.__run_statement(statement[0])
        if return_type == 'void':
            if self.what_method == IB.MAIN_FUNC_DEF: pass   # already detect for returns in main so passing here is chill
            elif res: IB.error(self.interpreter,'ErrorType.TYPE_ERROR') 
            elif self.null: IB.error(self.interpreter,'ErrorType.TYPE_ERROR')
        elif return_type in ['int', 'bool', 'string'] and self.null: IB.error(self.interpreter,'ErrorType.TYPE_ERROR') 
        elif res == None:
            if return_type in list(self.class_dict.keys()): return_type = IB.VOID_DEF
            elif return_type not in list(self.default_returns.keys()): IB.error(self.interpreter,'ErrorType.TYPE_ERROR')            #print('HEHEHE',return_type, self.default_returns[return_type])
            res = self.default_returns[return_type]
        else:    
            if type(res) is ObjectDefinition:
                if return_type in (self.default_returns.keys()): IB.error(self.interpreter,'ErrorType.TYPE_ERROR') 
                if return_type not in list(self.class_dict.keys()): IB.error(self.interpreter,'ErrorType.TYPE_ERROR')
                base_name = res.what_class 
                while return_type != base_name:
                    if base_name == self.class_dict[base_name]: IB.error(self.interpreter,'ErrorType.TYPE_ERROR')
                    else: base_name = self.class_dict[base_name] 
            elif return_type in list(self.class_dict.keys()): IB.error(self.interpreter,'ErrorType.TYPE_ERROR')
            # else:
            if return_type in list(self.default_returns.keys()):
                if return_type == IB.STRING_DEF: return_type = 'str'
                if type(res) != eval(return_type): IB.error(self.interpreter,'ErrorType.TYPE_ERROR') 
        return res
    
    def __find_method(self,method_name):
        try: return self.method_defs[method_name]
        except: IB.error(self.interpreter, 'ErrorType.NAME_ERROR') 

    def add_method(self, method):
        if method[2] in list(self.method_defs.keys()): IB.error(self.interpreter, 'ErrorType.NAME_ERROR')
        if method[1] not in list(self.class_dict.keys()) and method[1] not in list(self.default_returns.keys()): IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')
        self.method_defs[method[2]] = (method[1], method[3], method[4:])    #name -> return type, params, statement
    
    def add_field(self, given_type, name, initial_value, what_scope):
        if what_scope == 'field_defs': scoped_map = self.field_defs
        elif what_scope == IB.LET_DEF: 
            scoped_map = self.method_params[self.what_method][IB.LET_DEF][-1]
        if name in list(scoped_map.keys()): IB.error(self.interpreter, 'ErrorType.NAME_ERROR')
        res = self.__eval_exp([initial_value])
        if given_type not in list(self.class_dict.keys()):
            if given_type not in list(self.default_returns): IB.error(self.interpreter, 'ErrorType.TYPE_ERROR') #type DNE
            if given_type == IB.STRING_DEF: given_type = 'str'
            if type(res) != eval(given_type): IB.error(self.interpreter, 'ErrorType.TYPE_ERROR') #primitive mismatch
        if given_type in list(self.class_dict.keys()) and res != None: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR') # obj / prim mis match
        scoped_map[name] = [res , type(res), given_type]
    
    def __execute_print_statement(self, statement):
        res = ""
        for word in statement:
            word = self.__eval_exp([word])
            if type(word) is bool: word = str(word).lower()
            res += str(word)
        IB.output(self.interpreter, val=res)
    
    def __execute_input_statement(self, statement):
        res = IB.get_input(self.interpreter)
        if str(res).replace("-","").isnumeric(): res = int(res) 
        else: res = str(res)
        self.__execute_set_statement([statement[0], res])
    
    def execute_call_statement(self,statement):
        object_reference, method_name, *args = statement
        params = []
        for arg in list(args): 
            try: 
                for vars in self.method_params[self.what_method][IB.LET_DEF][::-1]:
                    try: 
                        params.append(vars[arg][0])
                        break 
                    except: pass  
            except:
                try: params.append(self.method_params[self.what_method][arg][0])
                except:
                    try: params.append(self.field_defs[arg][0]) 
                    except: params.append(self.__eval_exp([arg]))
        if object_reference == IB.ME_DEF: self = self.derived
        if object_reference != IB.ME_DEF or (object_reference == IB.ME_DEF and self.base):
            try:
                for vars in self.method_params[self.what_method][IB.LET_DEF][::-1]:
                    try: 
                        obj = vars[object_reference][0]
                        break 
                    except: pass   
            except:
                try: obj = self.method_params[self.what_method][object_reference][0]    #Find object
                except:
                    try: obj = self.field_defs[object_reference][0]
                    except:
                        if object_reference == IB.SUPER_DEF: obj = self.base
                        elif object_reference == IB.ME_DEF: obj = self.derived # case of referencing me in a derived class
                        else: obj = self.__eval_exp([object_reference])
            if not obj or type(obj) is not ObjectDefinition: IB.error(self.interpreter, 'ErrorType.FAULT_ERROR')
            name, num_params, right_type = False, False, False
            obj_base = obj
            while not (name & num_params & right_type) and obj_base:
                if method_name in list(obj_base.method_defs.keys()): name = True
                if name and len(params) == len(obj_base.method_defs[method_name][1]): num_params = True
                if num_params:
                    j = 0
                    for i in range(len(params)):
                        given_type = obj_base.method_defs[method_name][1][i][0]
                        if given_type not in list(self.default_returns.keys()):
                            if type(params[i]) not in [type(None), ObjectDefinition]: IB.error(self.interpreter, 'ErrorType.NAME_ERROR')  
                        if type(params[i]) in [ObjectDefinition, type(None)]:
                            if given_type in list(self.default_returns.keys()): IB.error(self.interpreter, 'ErrorType.NAME_ERROR')  
                            if not params[i]: continue # None -> obj
                            while given_type != params[i].what_class:
                                if self.class_dict[params[i].what_class] == params[i].what_class: IB.error(self.interpreter, 'ErrorType.NAME_ERROR') 
                                else: params[i].what_class = self.class_dict[params[i].what_class]
                        else:
                            if given_type == 'string': given_type = 'str'
                            if type(params[i]) != eval(given_type): break
                        j=i
                    if not len(params) or j == len(params)-1:  right_type = True
                if not right_type: obj_base = obj_base.base
            if not obj_base: IB.error(self.interpreter, 'ErrorType.NAME_ERROR')
            if not (obj_base is obj): return obj_base.call_method(method_name, params)
            return obj.call_method(method_name, params) # run the method
        
        temp = self.method_params.pop(self.what_method) 
        prev_method = self.what_method  # recursion
        res = self.call_method(method_name, params)
        self.method_params.pop(method_name) 
        self.end = False
        self.what_method = prev_method
        self.method_params[self.what_method] = temp 
        return res
    
    def __execute_while_statement(self,statement):
        condition, body =  statement
        while True:
            if type(self.__eval_exp([condition])) is not bool: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')
            if not self.__eval_exp([condition]): break
            res = self.__run_statement(body)
            if self.end: return res
    
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
        if self.what_method == IB.MAIN_FUNC_DEF: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR') # cant return in main
        if statement[0] == IB.NULL_DEF: self.null = True
        if statement[0] == IB.ME_DEF: return self.derived
        try: 
            for vars in self.method_params[self.what_method][IB.LET_DEF][::-1]:
                try: return vars[statement[0]][0]
                except: pass  
        except:
            try: return self.method_params[self.what_method][statement[0]][0]
            except:
                try: return self.field_defs[statement[0]][0]
                except: return self.__eval_exp([statement[0]])
        
    def __execute_all_sub_statements_of_begin_statement(self,statement):
        let = False
        # print('hi',statement[0])
        if statement[0] == [] or type(statement[0][0]) is list:
            variables, *statement = statement
            try: self.method_params[self.what_method][IB.LET_DEF].append({})
            except: self.method_params[self.what_method][IB.LET_DEF] = [{}]
            for variable in variables:
                self.add_field(variable[0],variable[1],variable[2], 'let')
            let = True
            # print('hii', self.method_params)

        for line in statement:
            res = self.__run_statement(line)
            if self.end: return res
        if let: 
            let = False
            self.method_params[self.what_method][IB.LET_DEF].pop() 
            if len(self.method_params[self.what_method][IB.LET_DEF]) == 0: self.method_params[self.what_method].pop(IB.LET_DEF) 
    
    def __execute_new_statement(self,expression):
        if expression[0] in list(self.interpreter.classes.keys()):
            obj = self.interpreter.find_definition_for_class(expression[0])
        else: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')
        return obj
            
    def __execute_set_statement(self, statement):
        name,value = statement
        res, value_pair = self.__eval_exp([value]), type(Interpreter)
        try: 
            for vars in self.method_params[self.what_method][IB.LET_DEF][::-1]:
                try: 
                    value_pair = vars[name]
                    break
                except: pass  
        except: pass
        if value_pair == type(Interpreter):
            try: value_pair = self.method_params[self.what_method][name]
            except:
                try: value_pair = self.field_defs[name]
                except: IB.error(self.interpreter, 'ErrorType.NAME_ERROR') 
        if value_pair[1] in [ObjectDefinition, type(None)]:
            if type(res) in [int, bool, str]: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR') 
            if type(res) == type(None): pass
            if res: 
                base_name = res.what_class
                while value_pair[2] != base_name:
                    if self.class_dict[base_name] == base_name: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')  
                    else: base_name = self.class_dict[base_name]
                value_pair[1] = type(res)
        elif type(res) is not value_pair[1]: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR') 
        
        if type(res) is bool: res = str(res).lower()    # True/False -> true/false 
        value_pair[0] = res
        return
        
#   # runs/interprets the passed-in statement until completion and
    def __run_statement(self, statement):
        keyword = statement[0]
        statement = statement[1:]
        if keyword == IB.PRINT_DEF:
            result = self.__execute_print_statement(statement)
        elif keyword in [IB.INPUT_INT_DEF,IB.INPUT_STRING_DEF]:
            result = self.__execute_input_statement(statement)
        elif keyword == IB.CALL_DEF:
            result = self.execute_call_statement(statement)
        elif keyword == IB.WHILE_DEF:
            result = self.__execute_while_statement(statement)
        elif keyword == IB.IF_DEF:
            result = self.__execute_if_statement(statement)
        elif keyword == IB.RETURN_DEF:
            result = self.__execute_return_statement(statement)
        elif keyword in [IB.BEGIN_DEF,IB.LET_DEF]:
            result = self.__execute_all_sub_statements_of_begin_statement(statement)
        elif keyword == IB.SET_DEF:
            result = self.__execute_set_statement(statement)
        return result

    def __eval_exp(self,expression):
        if type(expression[0]) is list: expression = expression[0]
        if type(expression[0]) is not StringWithLineNumber: return expression[0]
        filled_in_exp = []
        for term in expression:
            expr_val = term
            if type(term) is list:     
                res = self.__eval_exp(term)              
                expr_val = [res, type(res)]
            elif term == IB.NEW_DEF: return self.__execute_new_statement(expression[1:])    # new class
            elif term == IB.CALL_DEF: return self.execute_call_statement(expression[1:])    # method call
            elif '"' in term: expr_val = [str(term).replace('"',""), str]                   # string
            elif term.replace("-","").isnumeric(): expr_val = [int(term), int]              # integer
            elif term in list(self.operators.keys()): expr_val = self.operators[term]       # operator                               
            elif self.what_method != '' and IB.LET_DEF in list(self.method_params[self.what_method].keys()):       # let scoped variable
                for vars in self.method_params[self.what_method][IB.LET_DEF][::-1]:
                    try: 
                        expr_val = vars[term]
                        break
                    except: pass
            if expr_val == term: 
                if self.what_method != '' and term in list(self.method_params[self.what_method].keys()): 
                    expr_val = self.method_params[self.what_method][term]                       # method params scoped variable
                elif term in list(self.field_defs.keys()): expr_val = self.field_defs[term]     # field def scoped variable
                elif term == IB.ME_DEF: return self.derived
                elif expr_val is term: IB.error(self.interpreter, 'ErrorType.NAME_ERROR')       # out of scope
            filled_in_exp.append(expr_val)
        
        res = filled_in_exp[0][0]
        if len(filled_in_exp) == 1: return res      # singular expression
        if expression[0] not in list(self.operators.keys()): IB.error(self.interpreter, 'ErrorType.TYPE_ERROR') #invalid expression
        op, is_boolean_operator = self.operators[expression[0]]
        if is_boolean_operator == 'unary':                          # int is code for unary operator !
            if len(filled_in_exp[1:]) != 1: raise Exception
            if filled_in_exp[1][1] is not bool: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')
            res = op(filled_in_exp[1][0])
        elif is_boolean_operator:
            if len(filled_in_exp[1:]) != 2: raise Exception
            if set([filled_in_exp[1][1], filled_in_exp[2][1]]) & set([type(None), ObjectDefinition]):   #operands contain an object/None
                if set([filled_in_exp[1][1], filled_in_exp[2][1]]) & set([int, bool, str]): IB.error(self.interpreter, 'ErrorType.TYPE_ERROR') # operands have incompatible type
                if filled_in_exp[1][1] == ObjectDefinition and filled_in_exp[2][2] == 'main': filled_in_exp[2][2] =  filled_in_exp[1][2]        # obj against default null
                if filled_in_exp[2][1] == ObjectDefinition and filled_in_exp[1][2] == 'main': filled_in_exp[1][2] =  filled_in_exp[2][2]        # same ^
                op1 = filled_in_exp[1][2]       # determining proper polymorphism
                if filled_in_exp[1][0]: op1 = filled_in_exp[1][0].what_class
                op2 = filled_in_exp[2][2]
                if filled_in_exp[2][0]: op2 = filled_in_exp[2][0].what_class
                x,operands = 0,[op1, op2]
                if set(operands) ^ set([operands[0]]): 
                    for term in operands:
                        gtype = [x for x in operands if x != term][0]
                        while gtype != term:
                            if self.class_dict[term] == term: break
                            else: term = self.class_dict[term]
                        if gtype == term: x +=1
                        else: x-=1 
                if x: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')    # bad inheritance between objects
            elif filled_in_exp[1][1] != filled_in_exp[2][1]: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR')  
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
                    if c[0] is not operator.add and o1[1] is str: IB.error(self.interpreter, 'ErrorType.TYPE_ERROR') 
                    res = c[0](o1[0],o2[0])
                    if o1[1] is int: res = int(res)
                    stack.append(res)
            res = stack.pop()
        return res

def main():

    lines = []
    with open('input.txt', 'r') as file:
        for line in file:
            lines.append(line.strip())
                    
    ex = Interpreter()
    ex.run(lines)

if __name__ == '__main__':
    main()
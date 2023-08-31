from classv3 import ClassDef, TemplateClassDef
from intbase import InterpreterBase, ErrorType
from bparser import BParser
from objectv3 import ObjectDef
from type_valuev3 import TypeManager

# need to document that each class has at least one method guaranteed

# Main interpreter class
class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output

    # run a program, provided in an array of strings, one string per line of source code
    # usese the provided BParser class found in parser.py to parse the program into lists
    def run(self, program):
        status, parsed_program = BParser.parse(program)
        if not status:
            super().error(
                ErrorType.SYNTAX_ERROR, f"Parse error on program: {parsed_program}"
            )
        self.__add_all_class_types_to_type_manager(parsed_program)
        self.__map_class_names_to_class_defs(parsed_program)

        # instantiate main class
        invalid_line_num_of_caller = None
        self.main_object = self.instantiate(
            InterpreterBase.MAIN_CLASS_DEF, invalid_line_num_of_caller
        )

        # call main function in main class; return value is ignored from main
        self.main_object.call_method(
            InterpreterBase.MAIN_FUNC_DEF, [], False, invalid_line_num_of_caller
        )

        # program terminates!

    # user passes in the line number of the statement that performed the new command so we can generate an error
    # if the user tries to new an class name that does not exist. This will report the line number of the statement
    # with the new command
    def instantiate(self, class_name, line_num_of_statement):
        save_class = class_name
        template_class_def = None
        if '@' in class_name:
            template_class_def = class_name.split('@')
            for type_def in template_class_def[1:]:
                if not self.is_valid_type(type_def): super().error(
                        ErrorType.TYPE_ERROR,
                        'invalid type ' + type_def + 'passed into template type' + class_name,
                        line_num_of_statement
                )
            class_name = template_class_def[0]
        if class_name not in self.class_index:
            super().error(
                ErrorType.TYPE_ERROR,
                f"No class named {class_name} found",
                line_num_of_statement,
            )
        class_def = self.class_index[class_name]
        # try: print(class_def.var_list, template_class_def[1:])
        # except: pass
        # print(save_class)
        if template_class_def:
            self.type_manager.add_class_type(save_class, class_name)
            class_def = class_def.createObjDef(template_class_def[1:])

        # print(class_def.getV_name())
        obj = ObjectDef(
            self, class_def, None, self.trace_output
        )  # Create an object based on this class definition
        # if class_name != 'main':
        #     raise Exception
        # print(obj.class_def.class_source)
        # if class_name == 'node':
        #     raise Exception
        return obj

    # returns a ClassDef object
    def get_class_def(self, class_name, line_number_of_statement):
        if class_name not in self.class_index:
            super().error(
                ErrorType.TYPE_ERROR,
                f"No class named {class_name} found",
                line_number_of_statement,
            )
        return self.class_index[class_name]

    # returns a bool
    def is_valid_type(self, typename):
        return self.type_manager.is_valid_type(typename)

    # returns a bool
    def is_a_subtype(self, suspected_supertype, suspected_subtype):
        return self.type_manager.is_a_subtype(suspected_supertype, suspected_subtype)

    # typea and typeb are Type objects; returns true if the two type are compatible
    # for assignments typea is the type of the left-hand-side variable, and typeb is the type of the
    # right-hand-side variable, e.g., (set person_obj_ref (new teacher))
    def check_type_compatibility(self, typea, typeb, for_assignment=False):
        return self.type_manager.check_type_compatibility(typea, typeb, for_assignment)

    def __map_class_names_to_class_defs(self, program):
        self.class_index = {}
        for item in program:
            if item[0] == InterpreterBase.CLASS_DEF or InterpreterBase.TEMPLATE_CLASS_DEF:
                if item[1] in self.class_index:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Duplicate class name {item[1]}",
                        item[0].line_num,
                    )
                if item[0] == InterpreterBase.CLASS_DEF: self.class_index[item[1]] = ClassDef(item, self)
                else: self.class_index[item[1]] = TemplateClassDef(item, self)

    # [class classname inherits superclassname [items]]
    def __add_all_class_types_to_type_manager(self, parsed_program):
        self.type_manager = TypeManager()
        for item in parsed_program:
            if item[0] == InterpreterBase.CLASS_DEF or item[0] == InterpreterBase.TEMPLATE_CLASS_DEF:
                class_name = item[1]
                superclass_name = None
                if item[2] == InterpreterBase.INHERITS_DEF:
                    superclass_name = item[3]
                self.type_manager.add_class_type(class_name, superclass_name)

def main():

    lines = []
    with open('input.txt', 'r') as file:
        for line in file:
            lines.append(line.strip())
                    
    ex = Interpreter()
    ex.run(lines)

if __name__ == '__main__':
    main()

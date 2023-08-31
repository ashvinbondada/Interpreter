# CS 131 Spring 2023: Interpreter

I'm building an interpreter for my CS 131 Programming Languages class to understand a language's function, purpose, strengths, and weaknesses. When should we use a specific programming langauge? What is the best programming language for a scenario, and how should we determine that?

There are 3 progressive versions to the Interpreter which continually expand on the previous.\\
The first version of the interpreter supports:

# Classes

1. Fields
2. Methods

# Expressions

1. Booleans
2. Integer/String operations
3. Call (method)
4. New (class)

# Statements

1. If
2. While
3. Print
4. Return
5. Set
6. Begin

The second version of the interpreter supports:

1. Static Typing, meaning all fields and parameters have types, and methods have explicit return types. My program must now check that all types are compatible.
2. Local variables, which must be defined as part of a "let" statement
3. Inheritance - A derived class may have its own methods/fields, and may override the methods of the base class just as with other languages.
4. Polymorphism. As with languages like C++, you can substitute an object of the derived class anywhere your code expects an object of the base class

The third version of the interpreter supports:

1. Default Field and Local Variable Values. Variables throughout the program can be initialied with a default value rather than have to `let` a variable and then `set` it.
2. Class Templates - Once defined a templated class, you may use the class to define parameterized types anywhere normal types would be used in your program, e.g.: with return types, fields, parameters, local variables, and object instantiations.
3. Exception Handling - Like other languages, a thrown exception will immediately transfer control to the nearest/most nested exception handler in the call stack, e.g. If and when the catch statement is executed, a new variable called exception must be added into the catch statement's scope, and its value will be set to the exception string that was thrown by the throw statement.


# Interpreter V1 Examples

```lisp
# Our first Brewin program!
(class main
  # private member fields
  (field num 0)
  (field result 1)

# public methods
(method main ()
  (begin
    (print "Enter a number: ")
    (inputi num)
    (print num " factorial is " (call me factorial num))
  )
)
(method factorial (n)
  (begin
    (set result 1)
      (while (> n 0)
        (begin
          (set result (* n result))
          (set n (- n 1))
        )
      )
      (return result)
    )
  )
)
```

# Interpreter V2 Example:

```lisp
(class organism 
  (method void say_something () (print "blurb"))
)

(class person inherits organism
  (field string name "jane")
  (method void say_something () (print name " says hi"))
)

(class student inherits person
  (method void say_something ()
    (begin
     (print "first")
     (call super say_something)
     (print "second")
    )
  )
)

(class main
  (field organism o null)
  (method void foo ((organism o))
    (call o say_something))
  (method void main () 
    (begin 
      (set o (new student))
      (call me foo o)
      (set o (new person))
      (call me foo o)
      (set o (new organism))
      (call me foo o)
    )
  )
)
```

# Interpreter V3 Example:

```lisp
(class person
 (method void talk () (print "hello world"))
)

(tclass struct (field_type)
  (field field_type value)
  (method void set_val ((field_type v)) (set value v))
  (method field_type get_val () (return value))
)

(class main
  (method void main () 
    (let ((struct@person sp null) (person p null))
      (set sp (new struct@person))
      (set p (new person))
      (call sp set_val p)
      (call (call sp get_val) talk)
    )
  )
)
```

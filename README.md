# cntxt - the missing Python namespace

`cntxt` adds a dynamic namespace that is managed with a context manager and extends down
through the call stack, to be accessible where needed.

### Other options for managing namespaces

Scopes:
1. Local scope - variables in the current function or class definition
2. Enclosing scope - variables available through lexical closure
3. Global scope - module namespace created when module is loaded, usually never deleted
4. Built-in scope - created when interpreter starts, never deleted

Namespaces:
5. Object namespace - attributes, inherited or not
6. Class namespace - same, but for classes
7. Thread-local - data specific to a thread
8. Environment variables - values defined outside the Python program
9. File, database or similar - containing key-value pairs or more complex data

What's wrong with these namespaces?

1. Local scope is too local, not available elsewhere.
2. Enclosing scope is a little bit less local, but still very local in terms of a codebase.
3. Global scope is too global - we try to avoid "polluting the global namespace" as the values can
   be overwritten anywhere and conflicts can be hard to debug.
4. Built-in scope is too static.
5. Instances are ok, but accessing them requires a reference, which you have to manually pass down
   the stack to any users.
6. Classes are often used as importable singletons for configuration type information, but as such
   they can be "too global" and modified in surprising places.
7. Thread-local data is "too global" within the thread stack.
8. Environment variables are essentially global values, and where they are defined is not visible
   in the Python code.
9. Files or more powerful require configuration information to be accessible. They are also not
   in memory, which may be relevant in some cases.
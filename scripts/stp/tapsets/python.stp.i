/* Systemtap tapset to make it easier to trace Python */
/*
   Define python.function.entry/return:
*/

probe python.function.entry = process("__VIRTUALENV_PATH__/bin/python").library("__VIRTUALENV_PATH__/inst/lib/libpython2.7.so.1.0").mark("function__entry")
{
    filename = user_string($arg1);
    funcname = user_string($arg2);
    lineno = $arg3;
    file_mem = $arg1;
}
probe python.function.return = process("__VIRTUALENV_PATH__/bin/python").library("__VIRTUALENV_PATH__/inst/lib/libpython2.7.so.1.0").mark("function__return")
{
    filename = user_string($arg1);
    funcname = user_string($arg2);
    lineno = $arg3;
}

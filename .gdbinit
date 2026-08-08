# History
set history save on
set history size 10000
set history filename ~/.gdb_history

# Disassembly
set disassembly-flavor intel
set print asm-demangle on
set disassemble-next-line on

# Pretty-printing & readability
set print pretty on
set print object on
set pagination off
set print array-indexes on

# C++
set print vtbl on
set print demangle on
set unwindonsignal on

# Quality-of-life
set confirm off
set print frame-arguments all

# Backtraces
set backtrace past-main on

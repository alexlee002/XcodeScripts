#!/bin/sh

# filename: trim_comments.sh
# usage: trim_comments.sh xxx.c

cat "$1" |
awk '
BEGIN { FS="" }
!(ignore_line && $NF == "\\") && !ignore_line-- {
    ignore_line = 0;
    for(i = 1; i <= NF; i++) {
        if (ignore_block) {
            if ($i $(i+1) == "*/") {
                ignore_block = 0
                i++ # remove '*'
            }
            continue
        }
        if (!instr && $i $(i+1) == "/*") {
            ignore_block = 1
            i++ # remove '/'
            continue
        }
        if (!instr && $i $(i+1) == "//") {
            ignore_line = ($NF == "\\")? 1: 0
            break
        }
        if ($i == "\"") {
            instr = 1 - instr
        }
        printf("%s", $i)
    }
    printf("\n")
}'  | sed '/^$/d' 
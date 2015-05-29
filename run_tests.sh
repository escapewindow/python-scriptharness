#!/bin/bash

coverage erase
tox && coverage html && {
    files=$(find tests scriptharness -type f -name \*.py)
    echo "Running pylint..."
    for file in $files ; do
        echo -n "."
        output=$(pylint $file 2>&1 | grep 'Your code has been rated at ')
        echo $output | grep -q 'rated at 10.00/10'
        if [ $? != 0 ] ; then
            echo
            echo $file: $output
        fi
    done
    echo
}

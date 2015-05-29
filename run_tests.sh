#!/bin/bash

coverage erase
python tests/http/cgi_server.py >/dev/null 2>&1 &
trap "{ kill %; }" SIGINT SIGTERM SIGKILL EXIT
SCRIPTHARNESS_WEBSERVER="http://localhost:8001" tox && coverage html && {
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

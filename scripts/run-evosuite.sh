#!/bin/bash
SCOPE="$1"
TESTS="$2"
DIR="$3"
for FILE in $(find ./src/main/java -type f -name *.java); do
	TESTCLASS="$(echo ${FILE#./src/main/java/} | sed 's/\//./g' | sed 's/\.java$//')"
	ant evosuite-analyze-class -Dtestclass="$TESTCLASS" -Dscope="$SCOPE" -Dtests="$TESTS" -Ddir="$DIR"
done

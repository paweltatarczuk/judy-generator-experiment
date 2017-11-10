#!/bin/bash
for DIR in $(find ./src/main/java -type d); do
	FILES=$(find $DIR -maxdepth 1 -type f | wc -l)
	if [ $FILES -gt 0 ]; then
		PACKAGE=$(echo ${DIR#./src/main/java/} | sed 's/\//./g')
		LIMIT="$(($FILES * 200))"
		ant randoop-generate-tests-for-package -Dpackage="$PACKAGE" -Dlimit="$LIMIT"
	fi
done

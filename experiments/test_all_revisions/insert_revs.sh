#!/bin/bash

for REV in $(git log --quiet HEAD~3000..HEAD --topo-order --reverse | grep ^"commit " | cut -f2 -d" "); do
	echo "\t\tqueries.append(\"insert into git_log (revision) values ('$REV');\")" >> gitlog.sql
done


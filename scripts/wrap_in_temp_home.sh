#!/bin/bash -ex

# Looks like $TMPDIR doesn't exist in the DAS4
if [ ! -z "$TMPDIR" ]; then
    mkdir -p "$TMPDIR"
fi

export HOME=$(mktemp -d)

if [ ! -e $HOME ]; then
    echo "Something went wrong while creating the temporary execution dir, aborting."
    exit 3
fi

echo "Using temporary home directory: $HOME"

if [ ! -z "$HOME_SEED_FILE" ]; then
    export HOME_SEED_FILE

    if [ -e "$HOME_SEED_FILE" ]; then
        echo "Unpacking HOME seed file: $HOME_SEED_FILE"
        cd $HOME
        tar xaf $HOME_SEED_FILE
        cd -
        echo "Done"
    else
        echo "HOME_SEED_FILE ($HOME_SEED_FILE) does not exist. Bailing out"
        exit 4
    fi
else
    echo "HOME_SEED_FILE not set, using a clean fake home"
fi

$* || FAILURE=$?

rm -fR $HOME

exit $FAILURE
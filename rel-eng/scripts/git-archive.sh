#!/usr/bin/env bash
#
# Creates a tarball for a git repository using using the project name as
# the prefix within the tarball.
set -e

WORKING_DIR=$1
DEST=$2
PROJECT_NAME=$3
ARCHIVE_PREFIX=$4
GIT_URL=$5
TREEISH=$6

pushd "${WORKING_DIR}"
git clone "${GIT_URL}" "${PROJECT_NAME}"
pushd "${PROJECT_NAME}"
git checkout "${TREEISH}"
echo "HEAD SHA1: $(git rev-parse HEAD)"
mkdir -p "$(dirname "${DEST}")"
rm -f "${OUTPUT}"
git archive --format=tar.gz --prefix="${ARCHIVE_PREFIX}/" --output="${DEST}" HEAD

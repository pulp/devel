
psmash() {
    # We start and end with {push,pop}d because workon changes CWD and we don't want to user's CWD
    # to be altered when they type pulp-smash. We also want to maintain their active venv.
    if [ ! -z $VIRTUAL_ENV ]; then
        _original_venv=`basename $VIRTUAL_ENV`
    fi
    pushd {{ unprivileged_homedir}};
    workon pulp-smash;
    prestart;
    _return_code=1
    if make lint test
    then
        py.test {{ pulp_devel_dir }}/pulp-smash/pulp_smash;
        _return_code=$?
    fi
    if [ -z $_original_venv ]; then
        deactivate;
    else
        workon $_original_venv
    fi
    popd;
    return $_return_code
}
_psmash_help="Run pulp smash against the currently running pulp installation"



setup_crane_links() {
    # If Crane is present, let's set up the publishing symlinks so that the app files can be used
    if [ -d $HOME/devel/crane ]; then
        pushd $HOME/devel/crane
        mkdir -p metadata/v1 metadata/v2
        setfacl -m u:apache:rwx metadata/*
        sudo -u apache mkdir -p /var/lib/pulp/published/docker/v1 /var/lib/pulp/published/docker/v2
        sudo -u apache ln -s $HOME/devel/crane/metadata/v1 /var/lib/pulp/published/docker/v1/app
        sudo -u apache ln -s $HOME/devel/crane/metadata/v2 /var/lib/pulp/published/docker/v2/app
        popd
    fi
}


export CRANE_CONFIG_PATH=$HOME/devel/crane/crane.conf

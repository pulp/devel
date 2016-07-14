.PHONY: all help specs archive srpm rpm clean


SRPM_DIR=${PWD}/SRPMS/
RPM_DIR=${PWD}/RPMS/
SPECS_DIR=${PWD}/packaging/rpms/
CONFIG=config/master.yaml


all: help


help:
	@echo "Usage: make <target>"
	@echo "Available targets are:"
	@echo " srpm                    build srpms in the ${DEFAULT_CHROOT} mock root"
	@echo " rpm			build rpms in mock"
	@echo " copr-build              build rpms in COPR"
	@echo " clean                   remove all build files"

specs:
	if [ ! -d packaging ]; then \
		git clone https://github.com/pulp/packaging; \
	fi


archive: specs
	pulp-devel archives ${CONFIG} --spec-dir ${PWD}/packaging/


srpm: archive
	pulp-devel srpm ${CONFIG} --spec-dir ${PWD}/packaging/


rpm: srpm
	pulp-devel rpm ${CONFIG} --srpm-dir ${PWD}/SRPMS/


clean:
	rm -rf ${SRPM_DIR} ${RPM_DIR}
	find . -name "*.tar.gz" -delete
	mock --clean

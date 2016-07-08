.PHONY: all help archive srpm rpm clean


SRPM_DIR=${PWD}/SRPMS/
RPM_DIR=${PWD}/RPMS/
SPECS_DIR=${PWD}/packaging/rpms/
CONFIG=config/master.yaml


all: help


help:
	@echo "Usage: make <target>"
	@echo "Available targets are:"
	@echo " srpm                    build srpms in the ${DEFAULT_CHROOT} mock root"
	@echo " copr-build              build rpms in COPR; defaults to building in the ${CHROOTS}"
	@echo "                         chroots (define CHROOTS to override)"
	@echo " mock-build              build rpms in the ${DEFAULT_CHROOT} mock root"
	@echo " clean                   remove all build files"

archive:
	scripts/fetch-archives ${CONFIG}


srpm: archive
	scripts/build-srpms ${CONFIG}


rpm: srpm
	scripts/build-rpms ${CONFIG} mock


clean:
	rm -rf ${SRPM_DIR} ${RPM_DIR}
	find . -name "*.tar.gz" -delete
	mock --clean

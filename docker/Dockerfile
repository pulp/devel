FROM rohanpm/fedora-vagrant:latest

ARG USER_EUID=1001
ARG USER_EGID=1001

RUN /sbin/usermod -u ${USER_EUID} vagrant
RUN /sbin/groupmod -g ${USER_EGID} vagrant
RUN /bin/chown -R vagrant:vagrant /home/vagrant

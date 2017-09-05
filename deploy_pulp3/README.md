1. install ansible2.2+, python3, virtualenv, libselinux-python
2. download roles from galaxy
   ansible-galaxy install -r requirements.yml -p ./roles
3. run the playbook by specifying which broker you want rabbitmq|qpidd
   ansible-playbook deploy-pulp3.yml --extra-vars "pulp3_broker=rabbitmq"


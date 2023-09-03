FROM ubuntu:22.04
RUN apt-get update && apt-get install -y python3 python3-pip
RUN pip3 install dnspython, scp
WORKDIR /home
ADD qname_list /home/qname_list
ADD main.py /home/main.py
CMD ["python3", "/home/main.py"]
Required python version: Python 3.7.x/3.8.x

My environment:
Python 3.7.6/3.8.2
MySQL Ver 14.14 Distrib 5.7.28, for macos10.14 (x86_64)

Execute the command:
python3 pipe.py

Add dependencies:
python3 -m pip install -r require.txt --user

MySQL setup:
SET GLOBAL local_infile = 'ON';
SHOW GLOBAL VARIABLES LIKE 'local_infile';

+---------------+-------+
| Variable_name | Value |
+---------------+-------+
| local_infile  | ON    |
+---------------+-------+
(The status of the variable "local_infile" needs to be ON.)
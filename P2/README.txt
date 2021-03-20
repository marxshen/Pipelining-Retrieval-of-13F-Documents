Required python version: Python 3.7.x/3.8.x

My environment:
Python 3.7.6/3.8.2
MySQL Ver 14.14 Distrib 5.7.28, for macos10.14 (x86_64)
Google Chrome Version 81.0.4044.138 (Official Build) (64-bit)

Execute the command:
python3 P1/pipe.py (Need to run this version of pipe.py in P1 first to produce the correct results)
python3 pipe.py
python3 app.py

Type URL with this format in the google chrome browser.
127.0.0.1:5000?cik={company's cik}&start={start quarter}&end={end quarter}
(e.g. http://127.0.0.1:5000/?cik=0000895421&start=2015Q1&end=2020Q1)

List of CIKs:
[
	0000895421 (Morgan Stanely, quarters ranging from 1999Q2 to 2020Q1),
	0000019617 (JPMORGAN CHASE & CO, quarters ranging from 2015Q4 to 2020Q1),
	0001067983 (BERKSHIRE HATHAWAY INC, quarters ranging from 2015Q3 to 2020Q1), 
	0000070858 (BANK OF AMERICA CORP, quarters ranging from 2015Q4 to 2020Q1),
	0000072971 (WELLS FARGO & COMPANY/MN, quarters ranging from 2015Q3 to 2020Q1),
	0001450144 (TWO SIGMA SECURITIES, LLC, quarters ranging from 2015Q2 to 2020Q1)
]

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
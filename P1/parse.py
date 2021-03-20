import asyncio, re, os
from aiofile import AIOFile

# Parse a 13F document from an ordinary text file
def parseText(text, head, docs):
    report_re = re.compile('REPORT SUMMARY')
    table_re = re.compile('<TABLE>')
    skip_re = re.compile('VOTING AUTHORITY|<C>|<S>|<PAGE>')
    name_re = re.compile('NAME OF ISSUER')
    title_re = re.compile('-TITLE OF CLASS-')
    ttl_re = re.compile('T OF CLASS')
    shares_re = re.compile('\(X\$1000\)')
    sh_re = re.compile('\(x\$1000\)')
    managers_re = re.compile('-MANAGERS-')
    mgr_re = re.compile('--MGRS--')

    name_idx = title_idx = cusip_idx = -1
    name_last_idx = title_last_idx = cusip_last_idx = -1
    value_idx = shares_idx = shprn_idx = -1
    value_last_idx = shares_last_idx = shprn_last_idx = -1
    putcall_idx = invstmt_idx = managers_idx = -1
    putcall_last_idx = invstmt_last_idx = managers_last_idx = -1
    sole_idx = shared_idx = none_idx = -1
    sole_last_idx = shared_last_idx = none_last_idx = -1

    parse = False
    text = text.split('\n')
    for line in text:
        if report_re.search(line):
            break

        if parse == False and table_re.search(line):
            parse = True
            continue

        if parse == False:
            continue
        else:
            if line.strip() == '' or skip_re.search(line):
                continue
            
            # Calculate indexes of columns
            if name_re.search(line):
                name_idx = 0
                if title_re.search(line):
                    title_idx = line.find('-TITLE OF CLASS-')
                elif ttl_re.search(line):
                    title_idx = line.find('T OF CLASS')
                cusip_idx = line.find('--CUSIP--')

                name_last_idx = title_idx
                if title_re.search(line):
                    title_last_idx = title_idx + len('-TITLE OF CLASS-')
                elif ttl_re.search(line):
                    title_last_idx = title_idx + len('T OF CLASS')
                cusip_last_idx = cusip_idx + len('--CUSIP--')

                value_idx = cusip_last_idx
                if shares_re.search(line):
                    shares_idx = value_idx + (line.find('(X$1000)') - value_idx) + len('(X$1000)')
                elif sh_re.search(line):
                    shares_idx = value_idx + (line.find('(x$1000)') - value_idx) + len('(x$1000)')
                shprn_idx = line.find('PRN CALL')

                value_last_idx = shares_idx
                shares_last_idx = shares_idx + (line.find('PRN AMT') - shares_idx) + len('PRN AMT')
                shprn_last_idx = shprn_idx + len('PRN')

                putcall_idx = line.rfind('CALL')
                invstmt_idx = line.rfind('DSCRETN')
                if managers_re.search(line):
                    managers_idx = line.rfind('-MANAGERS-')
                elif mgr_re.search(line):
                    managers_idx = line.rfind('--MGRS--')

                putcall_last_idx = putcall_idx + len('CALL')
                invstmt_last_idx = invstmt_idx + len('DSCRETN')
                if managers_re.search(line):
                    managers_last_idx = managers_idx + len('-MANAGERS-')
                elif mgr_re.search(line):
                    managers_last_idx = managers_idx + len('--MGRS--')

                sole_idx = managers_last_idx
                shared_idx = sole_idx + (line.rfind('SOLE') - sole_idx) + len('SOLE')
                none_idx = shared_idx + (line.rfind('SHARED') - shared_idx) + len('SHARED')

                sole_last_idx = shared_idx
                shared_last_idx = none_idx
                none_last_idx = none_idx + (line.rfind('NONE') - none_idx) + len('NONE')
            else:
                # Retrieve values according to the indexes of the columns
                try:
                    name = line[name_idx:name_last_idx].strip()
                    title = line[title_idx:title_last_idx].strip()
                    cusip = line[cusip_idx:cusip_last_idx].strip()

                    value = shares = 0
                    if line[value_idx:value_last_idx].strip() != '':
                        value = int(line[value_idx:value_last_idx].strip())
                    if line[shares_idx:shares_last_idx].strip() != '':
                        shares = int(line[shares_idx:shares_last_idx].strip())

                    shprn = line[shprn_idx:shprn_last_idx].strip()
                    putcall = line[putcall_idx:putcall_last_idx].strip()
                    invstmt = line[invstmt_idx:invstmt_last_idx].strip()
                    managers = line[managers_idx:managers_last_idx].strip()
                    
                    sole = shared = none = 0
                    if line[sole_idx:sole_last_idx].strip() != '':
                        sole = int(line[sole_idx:sole_last_idx].strip())
                    if line[shared_idx:shared_last_idx].strip() != '':
                        shared = int(line[shared_idx:shared_last_idx].strip())
                    if line[none_idx:none_last_idx].strip() != '':
                        none = int(line[none_idx:none_last_idx].strip())

                    doc = [name, value, shares, sole, shared, none]
                    docs.append([*head, *doc])
                except:
                    continue

# Parse a 13F document from a XML text file
def parseXML(text, head, docs):
    head_re = re.compile('informationTable')
    tail_re = re.compile('</informationTable>')
    table_re = re.compile('</.*infoTable>')
    node_re = re.compile('<(?:ns1:)?(.*)>(.*)<')

    name = title = cusip = shprn = putcall = invstmt = managers = ''
    value = shares = sole = shared = none = ''

    parse = False
    text = text.split('\n')
    for line in text:
        if tail_re.search(line):
            break

        if parse == False and head_re.search(line):
            parse = True
            continue

        if parse == False:
            continue
        else:
            if table_re.search(line):
                doc = [name, value, shares, sole, shared, none]
                docs.append([*head, *doc])
                continue

            node_match = node_re.search(line)
            if node_match is None:
                continue
            else:
                # Retrieve values according to XML tags
                if node_match.group(1) == 'nameOfIssuer':
                    name = node_match.group(2)
                elif node_match.group(1) == 'titleOfClass':
                    title = node_match.group(2)
                elif node_match.group(1) == 'cusip':
                    cusip = node_match.group(2)
                elif node_match.group(1) == 'value':
                    value = int(node_match.group(2))
                elif node_match.group(1) == 'sshPrnamt':
                    shares = int(node_match.group(2))
                elif node_match.group(1) == 'sshPrnamtType':
                    shprn = node_match.group(2)
                elif node_match.group(1) == 'investmentDiscretion':
                    invstmt = node_match.group(2)
                elif node_match.group(1) == 'otherManager':
                    managers = node_match.group(2)
                elif node_match.group(1) == 'Sole':
                    sole = int(node_match.group(2))
                elif node_match.group(1) == 'Shared':
                    shared = int(node_match.group(2))
                elif node_match.group(1) == 'None':
                    none = int(node_match.group(2))

# Parse a 13F document according to the input filename
async def main(file):
    info_re = re.compile('informationTable')
    cik_re = re.compile('CENTRAL INDEX KEY:\s*(.*)')
    ria_re = re.compile('COMPANY CONFORMED NAME:\s*(.*)')
    type_re = re.compile('CONFORMED SUBMISSION TYPE:\s*(.*)')
    date_re = re.compile('FILED AS OF DATE:\s*(\w+)')
    ext_re = re.compile('txt')

    path = 'LOAD/'
    csv_file = ext_re.sub('csv', file)

    # If the 13F document is parsed before, the program simply skips this stage
    if os.path.exists(path + csv_file):
        print(f'parse.py: document exists: {csv_file}')
    else:
        # Create the directory 'LOAD'
        mask = os.umask(0)
        os.makedirs(path, exist_ok=True)
        os.umask(mask)

        holdings = []

        # Read the fetched document from the directory 'CIK'
        async with AIOFile('CIK/' + file, 'r') as afp:
            text = await afp.read()
            cik = ria = type = date = quarter = ''

            cik_match = cik_re.search(text)
            ria_match = ria_re.search(text)
            type_match = type_re.search(text)
            date_match = date_re.search(text)
            
            if cik_match:
                cik = cik_match.group(1)
            if ria_match:
                ria = ria_match.group(1)
            if type_match:
                type = type_match.group(1)
            if date_match:
                date = date_match.group(1)
                month = date[-4:-2]
                if int(month) < 4:
                    quarter = date[:-4] + 'Q1'
                elif int(month) < 7:
                    quarter = date[:-4] + 'Q2'
                elif int(month) < 10:
                    quarter = date[:-4] + 'Q3'
                else:
                    quarter = date[:-4] + 'Q4'

            header = [cik, ria, type, date, quarter]
            if info_re.search(text):
                parseXML(text, header, holdings)
            else:
                parseText(text, header, holdings)

        records = ''

        # Write the parsed document into the directory 'LOAD'
        async with AIOFile(path + csv_file, 'w+') as afp:
            for holding in holdings:
                holding = map(str, holding)

                record = '|'.join(holding)
                records += record + '\n'
                
            await afp.write(records)
            await afp.fsync()

        print(f'parse.py: document parsed: {file}')

    # Return the filename associated with the parsed file
    return file
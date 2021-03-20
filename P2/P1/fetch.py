import asyncio, aiohttp, os, re
from aiofile import AIOFile

# Fetch a 13 document according to an input URL
async def main(href):
    file_re = re.compile('\d+-.*.txt')

    path = 'CIK/'
    file = file_re.search(href).group()
    
    # If the 13F document is fetched before, the program simply skips this stage
    if os.path.exists(path + file):
        print('fetch.py: document exists:', file)
    else:
        async with aiohttp.request('GET', href) as resp:
            doc = await resp.text()

            # Create the directory 'CIK'
            mask = os.umask(0)
            os.makedirs(path, exist_ok=True)
            os.umask(mask)

            # Write the 13F document into the directory 'CIK'
            async with AIOFile(path + file, 'w+') as afp:
                await afp.write(doc)
                await afp.fsync()
        
            print('fetch.py: document fetched:', file)

    # Return the filename associated with the input URL
    return file
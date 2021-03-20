import pyppeteer, asyncio, re, os
from aiofile import AIOFile

# Acquire a headless chromium(browser) for navigating a website
async def get_http_session():
    return await pyppeteer.launcher.launch(args=['--no-sandbox'])

# This function will be called when a worker is instantiated
async def on_start():
    return dict(
        browser = await get_http_session()
    )

# This function will be called when a worker is finished its works
async def on_done(browser):
    # Close all the pages instantiated in a browser
    for pg in await browser.pages():
        await pg.close()

    await browser.close()

# Crawl the URLs associated with an input CIK in the website depositing 13F documents
async def main(cik, browser):
    page = await browser.newPage()

    cnt = 0
    if cik == '0000895421':
        cnt = 100
    else:
        cnt = 20
    
    url = f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany \
        &CIK={cik}&type=13F-HR%25&dateb=&owner=exclude&start=0&count={cnt}'
    await page.goto(url, waitUntil='domcontentloaded')

    hrefs = []

    cond = True
    while cond:
        docs = await page.JJeval(
            '#documentsbutton',
            'es => es.map(e => e.href.replace("https://www.sec.gov",""))'
        )

        # Retrieve the URLs corresponding to 13F documents
        for doc in docs:
            await page.waitFor(50)
            await asyncio.gather(
                page.waitForNavigation(waitUntil='domcontentloaded'),
                page.click(f'a[href="{doc}"]')
            )
            
            link = '.tableFile tr:last-of-type a'
            href = await page.Jeval(link, 'e => e.href')
            hrefs.append(href)
            print('crawl.py: link crawled:', href)

            await page.waitFor(50)
            await page.goBack()

        await page.waitFor(50)
        if cik == '0000895421':
            if await page.querySelector('input[value="Next 100"]') is not None:
                await asyncio.gather(
                    page.waitForNavigation(waitUntil='domcontentloaded'),
                    page.click('input[value="Next 100"]')
                )
            else:
                cond = False
        else:
            cond = False

    # Return the URLs corresponding to 13F documents
    return hrefs
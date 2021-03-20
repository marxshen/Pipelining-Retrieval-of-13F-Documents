import pypeln as pl, asyncio, timeit, crawl, fetch, parse, store

async def main():
    # CIKs for Morgan Stanely, JPMORGAN CHASE & CO, BERKSHIRE HATHAWAY INC,
    # BANK OF AMERICA CORP, WELLS FARGO & COMPANY/MN, TWO SIGMA SECURITIES, LLC
    data = ['0000895421', '0000019617', '0001067983', '0000070858', '0000072971', '0001450144']
    num_ciks = len(data)

    # 1st stage of the pipeline for crawling 13F documents
    stage = await pl.task.map(
        crawl.main, data, workers=num_ciks, maxsize=num_ciks,
        on_start = crawl.on_start, on_done = crawl.on_done
    )

    # Flatten the list of the lists of URLs into a list of URLs
    stage = [item for sublist in stage for item in sublist]
    
    # 2nd stage of the pipeline for fetching 13F documents
    stage = await pl.task.map(fetch.main, stage, workers=10, maxsize=10)

    # 3rd stage of the pipeline for parsing 13F documents
    stage = await pl.task.map(parse.main, stage, workers=10, maxsize=10)

    # Initialize the table 'holdings' for storing 13F documents
    await store.init_db()

    # 4th stage of the pipeline for storing 13F documents
    await pl.task.each(
        store.main, stage, workers=10, maxsize=10,
        on_start = store.on_start, on_done = store.on_done
    )

    # Query the result from the table 'holdings'
    return await store.query_db("select count(*) from holdings;")

if __name__ == '__main__':
    start = timeit.default_timer()

    # Place the main program(an asynchronous task) in the asyncio event loop
    print('Processing', asyncio.run(main()), 'records...')
    
    print(timeit.default_timer() - start, 'sec(s)')
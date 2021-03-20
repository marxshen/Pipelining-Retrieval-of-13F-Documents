import pypeln as pl, asyncio, timeit, stats

async def main():
    # CIKs for Morgan Stanely, JPMORGAN CHASE & CO, BERKSHIRE HATHAWAY INC,
    # BANK OF AMERICA CORP, WELLS FARGO & COMPANY/MN, TWO SIGMA SECURITIES, LLC
    ciks = ['0000895421', '0000019617', '0001067983', '0000070858', '0000072971', '0001450144'] 
    num_ciks = len(ciks)

    # Initialize the table 'sec_stats' and 'ria_stats' for analyzing 13F documents
    await stats.init_db()

    # 1st stage of the pipeline for preparing the indexes (cik, quarter) to query
    stage = await pl.task.map(
        stats.get_indexes, ciks, workers=num_ciks, maxsize=num_ciks,
        on_start=stats.on_start, on_done=stats.on_done
    )

    # Flatten the list of the lists of data into a list of data
    stage = [item for sublist in stage for item in sublist]
    
    # Create the procedure to calculate statistics concerning securities from 13F documents
    await stats.create_proc('sec')

    # 2nd stage of the pipeline for analyzing statistics concerning securities from 13F documents
    stage = await pl.task.map(
        stats.analyze_sec, stage, workers=5, maxsize=5,
        on_start=stats.on_start, on_done=stats.on_done
    )

    # Create the procedure to calculate statistics concerning RIAs from 13F documents
    await stats.create_proc('ria')

    # 3rd stage of the pipeline for analyzing statistics concerning RIAs from 13F documents
    await pl.task.each(
        stats.analyze_ria, stage, workers=5, maxsize=5,
        on_start=stats.on_start, on_done=stats.on_done
    )

if __name__ == '__main__':
    start = timeit.default_timer()

    # Place the main program(an asynchronous task) in the asyncio event loop
    asyncio.run(main())
    
    print(timeit.default_timer() - start, 'sec(s)')
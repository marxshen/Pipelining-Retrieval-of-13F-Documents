import asyncio, aiomysql, os
from aiofile import AIOFile

# Create and Connect to a pool of connections to MySQL database
async def get_db_session():
    return await aiomysql.create_pool(
        host='127.0.0.1', port=3306, maxsize=100,
        user='root', password='mysql123', db='mysql',
        loop=None, autocommit=True, local_infile=True
    )

# This function will be called when a worker is instantiated
async def on_start():
    return dict(
        pool = await get_db_session()
    )

# This function will be called when a worker is finished its works
async def on_done(pool):
    pool.close()
    await pool.wait_closed()

# Initialize the table 'sec_stats' and 'ria_stats' for analyzing 13F documents
async def init_db():
    pool = await get_db_session()

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('drop table if exists sec_stats')
            await cur.execute(
                """
                create table sec_stats (
                    serial int not null auto_increment,
                    cik varchar(20) not null,
                    quarter varchar(10) not null,
                    security varchar(100) not null,
                    value int not null,
                    shares int not null,
                    weighting double not null,
                    primary key (serial)
                );
                """
            )

            await cur.execute('drop table if exists ria_stats')
            await cur.execute(
                """
                create table ria_stats (
                    serial int not null auto_increment,
                    cik varchar(20) not null,
                    quarter varchar(10) not null,
                    num_sec int not null,
                    value bigint not null,
                    shares bigint not null,
                    change_value double not null,
                    change_shares double not null,
                    primary key (serial)
                );
                """
            )
    
    pool.close()
    await pool.wait_closed()

# Preparing the indexes (cik, quarter) to query
async def get_indexes(cik, pool):
    rows = []
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f'select distinct quarter from holdings where cik = {cik};')
            rows = await cur.fetchall()
    
    data = []
    for row in rows:
        data.append((cik, row[0]))

    return data

# Create procedure for analyzing statistics regarding securities and RIAs
async def create_proc(cmd):
    pool = await get_db_session()

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if cmd == 'sec':
                await cur.execute('drop procedure if exists `sec`;')
                await cur.execute(
                    """
                    create procedure `sec`(IN in_cik varchar(20), IN in_quarter varchar(10))
                    BEGIN
                        declare sum_val double;

                        select sum(value) into sum_val
                        from holdings
                        where cik = in_cik and quarter = in_quarter and type = '13F-HR';

                        select cik, quarter, security, val, shr, val/sum_val*100
                        from
                        (
                            select cik, quarter, security, 
                                cast(sum(value) as signed) as val,
                                cast(sum(shares) as signed) as shr
                            from holdings
                            where cik = in_cik and quarter = in_quarter and type = '13F-HR'
                            group by security
                        ) as t;
                    END
                    """
                )
            elif cmd == 'ria':
                await cur.execute('drop procedure if exists `ria`;')
                await cur.execute(
                    """
                    create procedure `ria`(IN in_cik varchar(20), IN curr_quarter varchar(10), IN prev_quarter varchar(10))
                    BEGIN
                        declare prev_val double;
                        declare prev_shrs double;

                        select sum(value), sum(shares) into prev_val, prev_shrs
                        from sec_stats
                        where cik = in_cik and quarter = prev_quarter;

                        insert into ria_stats(cik, quarter, num_sec, value, shares, change_value, change_shares)
                        select cik, quarter, num_sec, sum_val, sum_shrs,
                            if (prev_val is null, 0.0, (sum_val-prev_val)/prev_val*100),
                            if (prev_val is null, 0.0, (sum_shrs-prev_shrs)/prev_shrs*100)
                        from
                        (
                            select cik, quarter, count(distinct security) as num_sec,
                                cast(sum(value) as signed) as sum_val,
                                cast(sum(shares) as signed) as sum_shrs
                            from sec_stats
                            where cik = in_cik and quarter = curr_quarter
                        ) as t;
                    END
                    """
                )
                    
    pool.close()
    await pool.wait_closed()

# Analyzing statistics regarding securities
async def analyze_sec(data, pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            path = 'SEC_STATS/'
            csv_file = f'{data[0]}_{data[1]}.csv'

            await cur.callproc('sec', data)
            rows = await cur.fetchall()

            # Create the directory 'SEC_STATS'
            mask = os.umask(0)
            os.makedirs(path, exist_ok=True)
            os.umask(mask)

            # Write the analyzed document into the directory 'SEC_STATS'
            records = ''
            async with AIOFile(path + csv_file, 'w+') as afp:
                for row in rows:
                    row = map(str, row)
                    record = '|'.join(row)
                    records += record + '\n'
                    
                await afp.write(records)
                await afp.fsync()

            await cur.execute(
                f"""
                load data local infile 'SEC_STATS/{csv_file}'
                into table sec_stats
                fields terminated by '|'
                lines terminated by '\n'
                ignore 1 lines
                (
                    cik, quarter, security, value, shares, weighting
                );
                """
            )

            print(f'stats.py: sec with cik "{data[0]}" on quarter "{data[1]}" analyzed')
            return data

# Analyzing statistics regarding RIAs
async def analyze_ria(data, pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            prev_quarter = ''
            if data[1][-1] == '1':
                prev_quarter = str(int(data[1][:4])-1) + 'Q4'
            else:
                prev_quarter = data[1][:5] + str(int(data[1][-1]) - 1)
            await cur.callproc('ria', [data[0], data[1], prev_quarter])
            print(f'stats.py: ria with cik "{data[0]}" on quarter "{data[1]}" analyzed')
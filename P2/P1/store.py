import asyncio, aiomysql, re

# Create and Connect to a pool of connections to MySQL database
async def get_db_session():
    return await aiomysql.create_pool(
        host='127.0.0.1', port=3306,
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

# Initialize the table 'holdings' for storing 13F documents
async def init_db():
    pool = await get_db_session()

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('drop table if exists holdings;')
            await cur.execute(
                """
                create table holdings (
                    serial int not null auto_increment,
                    cik varchar(20) not null,
                    ria varchar(50) not null,
                    type varchar(20) not null,
                    dt_reported varchar(20) not null,
                    quarter varchar(10) not null,
                    security varchar(100) not null, 
                    value int not null,
                    shares int not null,
                    sole int not null,
                    shared int not null,
                    none int not null,
                    primary key (serial)
                );
                """
            )
    
    pool.close()
    await pool.wait_closed()

# Query the result from the table 'holdings'
async def query_db(stmt):
    pool = await get_db_session()

    rows = 0
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(stmt)
            rows = await cur.fetchall()
    
    pool.close()
    await pool.wait_closed()
    return rows[0][0]

# Store a 13F document according to the input filename
async def main(file, pool):
    file_re = re.compile('txt')
    csv_file = file_re.sub('csv', file)

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            stmt = f""" load data local infile 'LOAD/{csv_file}'
                        into table holdings
                        fields terminated by '|'
                        lines terminated by '\n'
                        ignore 1 lines
                        (
                            cik, ria, type, dt_reported, quarter, security,
                            value, shares, sole, shared, none
                        );
                    """
            await cur.execute(stmt)

    print(f'store.py: document stored: {file}')